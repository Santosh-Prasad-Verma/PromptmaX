"""Celery tasks for async AI operations."""

import logging
import concurrent.futures

from celery import shared_task
from django.core.cache import cache

from .core.ai_client import generate_with_fallback
from .core.pipeline import PromptXPipeline
from .core.scraper import scrape_website_deep, web_search
from .core.ab_testing import generate_ab_variations, compare_variations
from .utils.prompts import MASTER_PROMPT, build_website_analysis_prompt

logger = logging.getLogger("enhancer")

# G4F and PollinationsAI are removed, exclusively using official Mistral AI API


def _store_task_result(task_id: str, result: dict, ttl: int = 3600):
    cache.set(f"task:{task_id}", result, timeout=ttl)


def _get_task_status(task_id: str):
    return cache.get(f"task:{task_id}")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_prompt_history_task(self, history_id: str, supabase_user_id=None):
    from .models import PromptHistory
    from .supabase_sync import sync_prompt_history

    try:
        history = PromptHistory.objects.get(id=history_id)
        return sync_prompt_history(history, supabase_user_id=supabase_user_id)
    except PromptHistory.DoesNotExist:
        logger.warning("Supabase history sync skipped; history %s not found", history_id)
        return None
    except Exception as exc:
        logger.warning("Supabase history sync task failed for %s: %s", history_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_prompt_asset_task(self, asset_id: str, supabase_user_id: str):
    from .models import PromptAsset
    from .supabase_sync import sync_prompt_asset

    try:
        asset = PromptAsset.objects.select_related('project', 'user').get(id=asset_id)
        return sync_prompt_asset(asset, supabase_user_id)
    except PromptAsset.DoesNotExist:
        logger.warning("Supabase asset sync skipped; asset %s not found", asset_id)
        return None
    except Exception as exc:
        logger.warning("Supabase asset sync task failed for %s: %s", asset_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_prompt_version_task(self, version_id: str):
    from .models import PromptVersion
    from .supabase_sync import sync_prompt_version

    try:
        version = PromptVersion.objects.select_related('asset', 'history_reference').get(id=version_id)
        return sync_prompt_version(version)
    except PromptVersion.DoesNotExist:
        logger.warning("Supabase version sync skipped; version %s not found", version_id)
        return None
    except Exception as exc:
        logger.warning("Supabase version sync task failed for %s: %s", version_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_enhance(self, prompt: str, level: str = "intermediate",
                mode: str = "enhance", preferred_model: str = "auto"):
    task_id = self.request.id
    _store_task_result(task_id, {"status": "started", "progress": 0})

    try:
        pipeline = PromptXPipeline()
        result = pipeline.execute(
            prompt=prompt, enhancement_level=level,
        )
        data = result.to_dict()
        _store_task_result(task_id, {"status": "completed", "data": data})
        return data
    except Exception as exc:
        logger.error(f"Enhance task {task_id} failed: {exc}")
        _store_task_result(task_id, {"status": "failed", "error": str(exc)})
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_generate(self, prompt: str, preferred_model: str = "auto"):
    task_id = self.request.id
    _store_task_result(task_id, {"status": "started", "progress": 0})

    try:
        system_prompt = (
            f"{MASTER_PROMPT}\n\n---\n"
            f"**CURRENT MODE: Auto-detected**\n\n"
            f"User prompt: {prompt}"
        )
        result = generate_with_fallback(
            system_prompt, max_tokens=2000,
            preferred_model=preferred_model,
        )
        data = {
            "success": True,
            "type": "enhance",
            "mode": "generate",
            "enhanced": result["text"],
            "text": result["text"],
            "model": result["model"],
        }
        _store_task_result(task_id, {"status": "completed", "data": data})
        return data
    except Exception as exc:
        logger.error(f"Generate task {task_id} failed: {exc}")
        _store_task_result(task_id, {"status": "failed", "error": str(exc)})
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_deep_research(self, prompt: str, preferred_model: str = "auto"):
    task_id = self.request.id
    _store_task_result(task_id, {"status": "started", "progress": 0})

    try:
        system_prompt = (
            f"{MASTER_PROMPT}\n\n---\n"
            f"**CURRENT MODE: MODE 4 — TECH KNOWLEDGE EXPLORER**\n\n"
            f"User request: {prompt}"
        )
        result = generate_with_fallback(
            system_prompt, max_tokens=4000,
            preferred_model=preferred_model,
        )
        data = {
            "success": True, "type": "deep_research",
            "enhanced": result["text"], "model": result["model"],
            "classification": {"category": "general", "domain": "general"},
        }
        _store_task_result(task_id, {"status": "completed", "data": data})
        return data
    except Exception as exc:
        logger.error(f"Deep research task {task_id} failed: {exc}")
        _store_task_result(task_id, {"status": "failed", "error": str(exc)})
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_greeting(self, prompt: str, preferred_model: str = "auto"):
    task_id = self.request.id
    _store_task_result(task_id, {"status": "started", "progress": 0})

    try:
        system_prompt = (
            f"{MASTER_PROMPT}\n\n---\n"
            f"**CURRENT MODE: MODE 5 — DEEP CONVERSATION**\n\n"
            f"User: {prompt}"
        )
        result = generate_with_fallback(
            system_prompt, max_tokens=300,
            preferred_model=preferred_model,
        )
        data = {
            "success": True, "type": "welcome",
            "enhanced": result["text"], "model": result["model"],
        }
        _store_task_result(task_id, {"status": "completed", "data": data})
        return data
    except Exception:
        data = {
            "success": True, "type": "welcome",
            "enhanced": "Hello! I'm Promptrix AI. How can I help you today?",
            "model": "fallback",
        }
        _store_task_result(task_id, {"status": "completed", "data": data})
        return data


@shared_task(bind=True, max_retries=1, default_retry_delay=10)
def run_url_analysis(
    self, prompt: str, url: str, preferred_model: str = "auto"
):
    task_id = self.request.id
    _store_task_result(task_id, {"status": "started", "progress": 0})

    try:
        scraped = scrape_website_deep(url)
        if not scraped["success"]:
            _store_task_result(task_id, {
                "status": "failed",
                "error": f"Failed to scrape: {scraped['error']}",
            })
            return None

        _store_task_result(task_id, {"status": "started", "progress": 30})

        search_context = web_search(prompt)
        pages_summary = "\n".join(
            f"- {p['title']}: {p['url']} ({len(p['text'])} chars)"
            for p in scraped["pages"]
        )
        analysis_prompt = build_website_analysis_prompt(
            prompt, scraped["site_title"], url,
            scraped["pages_scraped"], scraped["total_chars"],
            pages_summary, scraped["combined_text"],
            "\n".join(
                f"[{s['title']}] {s['snippet']}"
                for s in search_context
            ),
        )
        response_data = generate_with_fallback(
            analysis_prompt, max_tokens=4000,
            preferred_model=preferred_model,
        )
        data = {
            "success": True, "type": "url_analysis",
            "mode": "url_analysis",
            "enhanced": response_data["text"],
            "text": response_data["text"],
            "model": response_data["model"],
            "url": url,
            "site_title": scraped["site_title"],
            "pages_scraped": scraped["pages_scraped"],
            "total_chars": scraped["total_chars"],
            "pages": [
                {"url": p["url"], "title": p["title"]}
                for p in scraped["pages"]
            ],
        }
        _store_task_result(task_id, {"status": "completed", "data": data})
        return data
    except Exception as exc:
        logger.error(f"URL analysis task {task_id} failed: {exc}")
        _store_task_result(task_id, {"status": "failed", "error": str(exc)})
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=1, default_retry_delay=5)
def run_ab_test(self, prompt: str, preferred_model: str = "auto"):
    task_id = self.request.id
    _store_task_result(task_id, {"status": "started", "progress": 0})

    try:
        variations = generate_ab_variations(
            prompt, preferred_model=preferred_model,
        )
        comparison = compare_variations(prompt, variations)
        data = {
            "success": True,
            "original": prompt,
            "variations": comparison["variations"],
            "recommendation": comparison["recommendation"],
        }
        _store_task_result(task_id, {"status": "completed", "data": data})
        return data
    except Exception as exc:
        logger.error(f"AB test task {task_id} failed: {exc}")
        _store_task_result(task_id, {"status": "failed", "error": str(exc)})
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_execute(
    self, prompt_text: str, model: str = "auto", max_tokens: int = 1000,
):
    task_id = self.request.id
    _store_task_result(task_id, {"status": "started", "progress": 0})

    try:
        import time
        start = time.time()
        result = generate_with_fallback(
            prompt=prompt_text, max_tokens=max_tokens,
            preferred_model=model,
        )
        elapsed = time.time() - start
        data = {
            "success": True,
            "result_text": result["text"],
            "model_used": result["model"],
            "execution_time_seconds": round(elapsed, 2),
        }
        _store_task_result(task_id, {"status": "completed", "data": data})
        return data
    except Exception as exc:
        logger.error(f"Execute task {task_id} failed: {exc}")
        _store_task_result(task_id, {"status": "failed", "error": str(exc)})
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=1, default_retry_delay=10)
def run_multi_model(self, prompt: str):
    task_id = self.request.id
    _store_task_result(task_id, {"status": "started", "progress": 0})

    models = [
        {"name": "mistral_large", "label": "Mistral Large"},
        {"name": "mistral_small", "label": "Mistral Small"},
        {"name": "codestral", "label": "Codestral"},
    ]

    results = []

    def _call_one(model_info):
        import time
        start = time.time()
        try:
            res = generate_with_fallback(
                prompt=prompt,
                preferred_model=model_info["name"]
            )
            elapsed = time.time() - start
            text = res.get("text", "")
            return {
                "model": model_info["label"],
                "model_key": model_info["name"],
                "text": text,
                "time": round(elapsed, 2),
                "chars": len(text),
                "success": True,
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                "model": model_info["label"],
                "model_key": model_info["name"],
                "text": "",
                "time": round(elapsed, 2),
                "chars": 0,
                "success": False,
                "error": str(e),
            }

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_call_one, m): m for m in models}
            for future in concurrent.futures.as_completed(futures, timeout=120):
                result = future.result()
                results.append(result)
    except Exception as e:
        logger.error(f"Multi-model parallel call failed: {e}")

    results.sort(key=lambda r: models.index(
        next((m for m in models if m["name"] == r["model_key"]), models[0]),
    ))

    winner = None
    successful = [r for r in results if r["success"]]
    if successful:
        winner = max(successful, key=lambda r: r["chars"])

    data = {
        "success": True,
        "type": "multi_model",
        "prompt": prompt,
        "results": results,
        "winner": winner["model"] if winner else None,
        "total_time": round(
            max((r["time"] for r in results if r["time"]), default=0), 2,
        ),
    }
    _store_task_result(task_id, {"status": "completed", "data": data})
    return data
