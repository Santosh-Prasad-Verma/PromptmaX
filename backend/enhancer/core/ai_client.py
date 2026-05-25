import os
import time
import logging
from dotenv import load_dotenv
from django.conf import settings

from ..utils.cache import DeepCopyLRUCache

load_dotenv()
logger = logging.getLogger('enhancer')


class AIModelFallback:
    def __init__(self):
        self.models = [
            {'name': 'nvidia_nemotron', 'priority': 1},
            {'name': 'nvidia_minimax', 'priority': 2},
            {'name': 'nvidia_gpt_oss', 'priority': 3},
        ]

    def generate(self, prompt, max_tokens=2000, preferred_model=None, api_key=None):
        errors = []
        if preferred_model and preferred_model != 'auto' and preferred_model in [m['name'] for m in self.models]:
            try:
                result = self._call_model(preferred_model, prompt, max_tokens, api_key=api_key)
                if result:
                    return {'text': result, 'model': preferred_model, 'success': True}
            except Exception as e:
                raise Exception(f"Selected model '{preferred_model}' failed: {str(e)}")

        for err in errors:
            logger.warning(f"Model fallback error: {err[:200]}")

        for model in self.models:
            try:
                result = self._call_model(model['name'], prompt, max_tokens, api_key=api_key)
                if result:
                    return {'text': result, 'model': model['name'], 'success': True}
            except Exception as e:
                errors.append(f"{model['name']}: {str(e)}")
                continue

        if all('429' in str(e) or 'quota' in str(e).lower() or 'resource_exhausted' in str(e).lower() for e in errors):
            raise Exception(f"All NVIDIA model quotas exceeded. Errors: {'; '.join(errors[:2])}")
        raise Exception(f"All models failed: {'; '.join(errors)}")

    def _call_model(self, model_name, prompt, max_tokens, api_key=None):
        if model_name == 'nvidia_nemotron':
            return self._call_nvidia_nemotron(prompt, max_tokens, api_key=api_key)
        elif model_name == 'nvidia_minimax':
            return self._call_nvidia_minimax(prompt, max_tokens, api_key=api_key)
        elif model_name == 'nvidia_gpt_oss':
            return self._call_nvidia_gpt_oss(prompt, max_tokens, api_key=api_key)

    def _call_nvidia_minimax_stream(self, prompt, max_tokens, api_key=None):
        key = api_key or os.getenv('NVIDIA_API_KEY')
        if not key:
            raise ValueError("NVIDIA_API_KEY not found")
        from openai import OpenAI
        import httpx
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=key,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        max_input_chars = 6000
        if len(prompt) > max_input_chars:
            prompt = prompt[:max_input_chars] + "\n\n[Truncated for speed]"
        messages = self._split_prompt(prompt)
        try:
            stream = client.chat.completions.create(
                model="minimaxai/minimax-m2.7",
                messages=messages,
                temperature=0.7,
                top_p=0.95,
                max_tokens=min(max_tokens, 8192),
                stream=True,
            )
            for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                if delta.content is not None:
                    yield delta.content
        except Exception as e:
            raise Exception(f"NVIDIA streaming error: {str(e)}")

    def _call_nvidia_minimax(self, prompt, max_tokens, api_key=None):
        parts = []
        try:
            for chunk in self._call_nvidia_minimax_stream(prompt, max_tokens, api_key=api_key):
                parts.append(chunk)
            return ''.join(parts).strip()
        except Exception as e:
            raise Exception(f"NVIDIA API error: {str(e)}")

    def _call_nvidia_nemotron_stream(self, prompt, max_tokens, api_key=None):
        key = api_key or os.getenv('NVIDIA_API_KEY')
        if not key:
            raise ValueError("NVIDIA_API_KEY not found")
        from openai import OpenAI
        import httpx
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=key,
            timeout=httpx.Timeout(180.0, connect=10.0),
        )
        max_input_chars = 12000
        if len(prompt) > max_input_chars:
            prompt = prompt[:max_input_chars] + "\n\n[Truncated for speed]"
        messages = self._split_prompt(prompt)
        try:
            stream = client.chat.completions.create(
                model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                messages=messages,
                temperature=0.6,
                top_p=0.95,
                max_tokens=min(max_tokens, 65536),
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": True},
                    "reasoning_budget": 16384,
                },
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    yield f"[reasoning]{reasoning}[/reasoning]"
                if delta.content is not None:
                    yield delta.content
        except Exception as e:
            raise Exception(f"NVIDIA Nemotron streaming error: {str(e)}")

    def _call_nvidia_nemotron(self, prompt, max_tokens, api_key=None):
        parts = []
        try:
            for chunk in self._call_nvidia_nemotron_stream(prompt, max_tokens, api_key=api_key):
                parts.append(chunk)
            return ''.join(parts).strip()
        except Exception as e:
            raise Exception(f"NVIDIA Nemotron error: {str(e)}")

    def _call_nvidia_gpt_oss_stream(self, prompt, max_tokens, api_key=None):
        key = api_key or os.getenv('NVIDIA_API_KEY')
        if not key:
            raise ValueError("NVIDIA_API_KEY not found")
        from openai import OpenAI
        import httpx
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=key,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        max_input_chars = 12000
        if len(prompt) > max_input_chars:
            prompt = prompt[:max_input_chars] + "\n\n[Truncated for speed]"
        messages = self._split_prompt(prompt)
        try:
            stream = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=1,
                top_p=1,
                max_tokens=min(max_tokens, 4096),
                stream=True,
            )
            for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    yield f"[reasoning]{reasoning}[/reasoning]"
                if delta.content is not None:
                    yield delta.content
        except Exception as e:
            raise Exception(f"NVIDIA GPT-OSS streaming error: {str(e)}")

    def _call_nvidia_gpt_oss(self, prompt, max_tokens, api_key=None):
        parts = []
        try:
            for chunk in self._call_nvidia_gpt_oss_stream(prompt, max_tokens, api_key=api_key):
                parts.append(chunk)
            return ''.join(parts).strip()
        except Exception as e:
            raise Exception(f"NVIDIA GPT-OSS error: {str(e)}")

    def _split_prompt(self, prompt):
        delimiter = "\n\nUser prompt to enhance:\n"
        if delimiter in prompt:
            parts = prompt.split(delimiter, 1)
            return [
                {'role': 'system', 'content': parts[0].strip()},
                {'role': 'user', 'content': parts[1].strip()},
            ]
        return [{'role': 'user', 'content': prompt}]


_fallback = AIModelFallback()


@DeepCopyLRUCache(capacity=settings.PROMPTX.get('AI_CLIENT', {}).get('CACHE_SIZE', 500))
def generate_with_fallback(prompt, max_tokens=2000, preferred_model=None, api_key=None):
    for attempt in range(settings.PROMPTX.get('AI_CLIENT', {}).get('RETRY_COUNT', 1) + 1):
        try:
            return _fallback.generate(prompt, max_tokens, preferred_model=preferred_model, api_key=api_key)
        except Exception as e:
            if attempt == settings.PROMPTX.get('AI_CLIENT', {}).get('RETRY_COUNT', 1):
                raise
            logger.warning(f"AI generation attempt {attempt + 1} failed, retrying: {e}")
            time.sleep(2 ** attempt)
    raise Exception("AI generation failed after all retries")
