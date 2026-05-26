import os
import time
import logging
from dotenv import load_dotenv
from django.conf import settings

from ..utils.cache import DeepCopyLRUCache

load_dotenv()
logger = logging.getLogger("enhancer")

G4F_AVAILABLE = False
try:
    import g4f
    from g4f.Provider import PollinationsAI
    G4F_AVAILABLE = True
except ImportError:
    logger.warning("g4f package not installed — GPT4Free models unavailable")


class AIModelFallback:
    def __init__(self):
        self.models = [
            {"name": "g4f_gpt4o", "priority": 1},
            {"name": "g4f_gemini_flash", "priority": 2},
            {"name": "g4f_llama3_70b", "priority": 3},
            {"name": "g4f_gpt4o_mini", "priority": 4},
            {"name": "g4f_gpt5_nano", "priority": 5},
        ]

    def generate(self, prompt, max_tokens=2000, preferred_model=None, api_key=None):
        if preferred_model and preferred_model != "auto":
            if preferred_model in [m["name"] for m in self.models]:
                try:
                    result = self._call_model(preferred_model, prompt, max_tokens)
                    if result:
                        return {"text": result, "model": preferred_model, "success": True}
                except Exception as e:
                    raise Exception(
                        f"Selected model '{preferred_model}' failed: {str(e)}"
                    )
            else:
                raise Exception(f"Unknown model: '{preferred_model}'")

        errors = []
        for model in self.models:
            try:
                result = self._call_model(model["name"], prompt, max_tokens)
                if result:
                    return {"text": result, "model": model["name"], "success": True}
            except Exception as e:
                errors.append(f"{model['name']}: {str(e)}")
                continue

        raise Exception(f"All models failed: {'; '.join(errors[:3])}")

    def _call_model(self, model_name, prompt, max_tokens):
        routing = {
            "g4f_gpt4o": ("gpt-4.1-nano", PollinationsAI),
            "g4f_gpt4o_mini": ("mistral-small-3.1-24b", PollinationsAI),
            "g4f_llama3_70b": ("gpt-4.1-nano", PollinationsAI),
            "g4f_gemini_flash": ("deepseek-r1", PollinationsAI),
            "g4f_gpt5_nano": ("gpt-5-nano", PollinationsAI),
        }
        if model_name not in routing:
            raise ValueError(f"Unknown model: {model_name}")
        g4f_model, provider = routing[model_name]
        return self._call_g4f(g4f_model, prompt, max_tokens, provider=provider)

    def _call_g4f(self, model_name, prompt, max_tokens, provider=None):
        if not G4F_AVAILABLE:
            raise RuntimeError("g4f package is not installed")
        messages = self._split_prompt(prompt)
        try:
            kwargs = {"model": model_name, "messages": messages, "stream": False}
            if provider is not None:
                kwargs["provider"] = provider
            response = g4f.ChatCompletion.create(**kwargs)
            if not response:
                raise Exception(f"g4f returned empty response for {model_name}")
            return str(response).strip()
        except Exception as e:
            raise Exception(f"g4f {model_name} error: {str(e)}")

    def _split_prompt(self, prompt):
        delimiter = "\n\nUser prompt to enhance:\n"
        if delimiter in prompt:
            parts = prompt.split(delimiter, 1)
            return [
                {"role": "system", "content": parts[0].strip()},
                {"role": "user", "content": parts[1].strip()},
            ]
        return [{"role": "user", "content": prompt}]


_fallback = AIModelFallback()


@DeepCopyLRUCache(capacity=settings.PROMPTX.get("AI_CLIENT", {}).get("CACHE_SIZE", 500))
def generate_with_fallback(prompt, max_tokens=2000, preferred_model=None, api_key=None):
    for attempt in range(settings.PROMPTX.get("AI_CLIENT", {}).get("RETRY_COUNT", 1) + 1):
        try:
            return _fallback.generate(
                prompt, max_tokens, preferred_model=preferred_model, api_key=api_key
            )
        except Exception as e:
            if attempt == settings.PROMPTX.get("AI_CLIENT", {}).get("RETRY_COUNT", 1):
                raise
            logger.warning(f"AI generation attempt {attempt + 1} failed, retrying: {e}")
            time.sleep(2**attempt)
    raise Exception("AI generation failed after all retries")
