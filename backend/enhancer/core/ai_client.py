import os
import time
import logging
from dotenv import load_dotenv
from django.conf import settings

from ..utils.cache import DeepCopyLRUCache

load_dotenv()
logger = logging.getLogger("enhancer")


class AIModelFallback:
    def __init__(self):
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        if not self.mistral_api_key:
            try:
                self.mistral_api_key = getattr(settings, "MISTRAL_API_KEY", None)
            except Exception:
                pass

        self.models = [
            {"name": "mistral_large", "priority": 1},
            {"name": "mistral_small", "priority": 2},
            {"name": "codestral", "priority": 3},
        ]
        self.valid_choices = ["mistral_large", "mistral_small", "codestral"]

    def generate(self, prompt, max_tokens=2000, preferred_model=None, api_key=None):
        if preferred_model and preferred_model != "auto":
            if preferred_model in self.valid_choices:
                try:
                    result = self._call_model(preferred_model, prompt, max_tokens, api_key=api_key)
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
                result = self._call_model(model["name"], prompt, max_tokens, api_key=api_key)
                if result:
                    return {"text": result, "model": model["name"], "success": True}
            except Exception as e:
                errors.append(f"{model['name']}: {str(e)}")
                continue

        raise Exception(f"All models failed: {'; '.join(errors[:3])}")

    def _call_model(self, model_name, prompt, max_tokens, api_key=None):
        if model_name in self.valid_choices:
            return self._call_mistral(model_name, prompt, max_tokens, api_key=api_key)
        raise ValueError(f"Unknown model: {model_name}")

    def _call_mistral(self, model_alias, prompt, max_tokens, api_key=None):
        import requests
        key = api_key or self.mistral_api_key or os.getenv("MISTRAL_API_KEY")
        if not key:
            raise ValueError(f"Mistral API key is not configured for {model_alias}")

        model_mapping = {
            "mistral_large": "mistral-large-latest",
            "mistral_small": "mistral-small-latest",
            "codestral": "codestral-latest",
        }
        mistral_model = model_mapping.get(model_alias, "mistral-large-latest")
        messages = self._split_prompt(prompt)

        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {key}"
        }

        timeout = 30
        try:
            timeout = settings.PROMPTX.get("AI_CLIENT", {}).get("REQUEST_TIMEOUT", 30)
        except Exception:
            pass

        payload = {
            "model": mistral_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code != 200:
                raise Exception(f"Mistral API error (status {response.status_code}): {response.text}")

            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return content.strip()
            else:
                raise Exception("Mistral API returned empty choices list")
        except Exception as e:
            raise Exception(f"Mistral {mistral_model} call failed: {str(e)}")

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
