"""Views for PromptX API — unified DRF layer."""
# Supabase dual-write sync (fire-and-forget, never blocks responses)
from enhancer.supabase_sync import (
    get_supabase_user_id,
)

import time
import re
import json
import hashlib
import logging
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from enhancer.auth import SupabaseJWTAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .serializers import (
    EnhanceRequestSerializer,
    AnalyzeRequestSerializer,
    CompareRequestSerializer,
    FeedbackSerializer,
    BatchEnhanceRequestSerializer,
    ABTestRequestSerializer,
    AnalyzeURLRequestSerializer,
    WebSearchRequestSerializer,
    IdeasRequestSerializer,
    PromptProjectSerializer,
    PromptAssetSerializer,
    PromptVersionSerializer,
    ExecutePromptSerializer,
    MultiModelRequestSerializer,
)
from .core.pipeline import PromptXPipeline
from .core.analyzer import PromptAnalyzer
from .core.quality_scorer import QualityScorer
from .core.ai_client import generate_with_fallback
from .core.scraper import scrape_website_deep, web_search
from .core.ab_testing import generate_ab_variations, compare_variations
from .core.idea_generator import IdeaGenerator
from .models import PromptHistory, PromptProject, PromptAsset, PromptVersion
from .utils.text_processing import sanitize_input
from .utils.prompts import MASTER_PROMPT, build_website_analysis_prompt
from .tasks import (
    run_enhance, run_generate, run_deep_research, run_greeting,
    run_url_analysis, run_ab_test, run_execute, run_multi_model,
    sync_prompt_history_task, sync_prompt_asset_task, sync_prompt_version_task,
)

logger = logging.getLogger('enhancer')

_GREETING_PATTERNS = {
    'hi', 'hello', 'hey', 'hii', 'helo', 'heya', 'howdy',
    'hi there', 'hello there', 'hey there',
    'what can you do', 'what do you do', 'who are you',
    'help', 'help me', 'what is this', 'how does this work',
    'good morning', 'good afternoon', 'good evening', 'good night',
    'sup', 'yo', 'wassup', 'whats up', "what's up",
}

_DEEP_RESEARCH_SIGNALS = [
    'build a', 'build an', 'create a', 'create an', 'make a', 'make an',
    'develop a', 'develop an', 'design a', 'design an',
    'bulid', 'i want to bulid', 'i want to build', 'how to build', 'how do i build',
    'like flipkart', 'like amazon', 'like uber', 'like airbnb', 'like netflix',
    'like instagram', 'like twitter', 'like facebook', 'like youtube',
    'like whatsapp', 'like linkedin', 'like shopify', 'like stripe',
    'same features', 'same as', 'similar to', 'clone of',
    'full website', 'full app', 'full stack', 'full-stack',
    'complete website', 'complete app', 'complete system',
    'e-commerce', 'ecommerce', 'marketplace', 'social media platform',
    'ai agent', 'how to create', 'how to develop',
    'architecture for', 'system design', 'tech stack for',
    'explain in detail', 'explain deeply', 'deep dive', 'in depth',
    'comprehensive guide', 'step by step guide', 'complete guide',
    'everything about', 'tell me everything', 'details', 'give details',
    'how it works', 'how does', 'how do', 'explain', 'what is the architecture',
    'step by step', 'explain step by step',
    'diagram', 'diagam', 'diagrram', 'architecture', 'visualize', 'draw a', 'show me a',
    'flowchart', 'structure of', 'breakdown of', 'hoe it work', 'hoe does',
]

_IDEA_SIGNALS = [
    'suggest me', 'give me ideas', 'business idea', 'project idea',
    'startup idea', 'side hustle', 'make money', 'how to make money',
    'money making', 'income idea', 'passive income', 'high grossing',
    'best idea', 'new idea', 'innovation', 'entrepreneur',
    'i want to start', 'i want to build', 'what business',
    'profitable business', 'lucrative', 'most profitable',
]

_URL_PATTERN = re.compile(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+', re.IGNORECASE)


def _classify_prompt(text: str) -> dict:
    lower = text.lower()
    return {"category": "general", "domain": "general"}


def _is_greeting(text):
    cleaned = text.strip().lower().rstrip('!?.')
    return cleaned in _GREETING_PATTERNS or (
        len(cleaned.split()) <= 2
        and any(cleaned.startswith(g) for g in ('hi', 'hey', 'hello', 'helo'))
    )


def _needs_deep_research(text):
    lower = text.lower()
    signal_count = sum(1 for s in _DEEP_RESEARCH_SIGNALS if s in lower)
    trigger_words = ['build', 'bulid', 'create', 'make', 'agent', 'app', 'website', 'clone', 'system', 'explain', 'details', 'how']
    return signal_count >= 1 or any(f" {w} " in f" {lower} " for w in trigger_words)


def _needs_ideas(text):
    return any(signal in text.lower() for signal in _IDEA_SIGNALS)


def _extract_urls(text):
    urls = _URL_PATTERN.findall(text)
    return [u if u.startswith('http') else f'https://{u}' for u in urls]


def _use_async(request):
    return request.query_params.get("async", "").lower() in ("true", "1")


def _cache_key(namespace, payload):
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"promptx:{namespace}:{digest}"


def _request_task_owner(request, create_session=False):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    if create_session and not request.session.session_key:
        request.session.save()
    if request.session.session_key:
        return f"session:{request.session.session_key}"
    return None


def _can_use_celery():
    return bool(getattr(settings, "REDIS_URL", "") or settings.CELERY_BROKER_URL != "redis://localhost:6379/0")


def _enqueue_background(task, *args, **kwargs):
    if not _can_use_celery():
        return False
    try:
        task.delay(*args, **kwargs)
        return True
    except Exception as exc:
        logger.warning("Background task enqueue failed for %s: %s", getattr(task, "name", task), exc)
        return False


def _dispatch_task(task, *args, **kwargs):
    request = kwargs.pop("_request", None)
    if not _can_use_celery():
        return Response(
            {"success": False, "error": "ASYNC_WORKER_NOT_CONFIGURED"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        result = task.delay(*args, **kwargs)
    except Exception as exc:
        logger.warning("Task dispatch failed for %s: %s", getattr(task, "name", task), exc)
        return Response(
            {"success": False, "error": "ASYNC_DISPATCH_FAILED"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if request is not None:
        owner = _request_task_owner(request, create_session=True)
        cache.set(f"task-owner:{result.id}", owner, timeout=3600)
    return Response({
        "success": True,
        "async": True,
        "task_id": result.id,
        "status_url": f"/api/v1/task/{result.id}/status/",
    }, status=status.HTTP_202_ACCEPTED)


class TaskStatusView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "task_status"

    def get(self, request, task_id):
        owner = cache.get(f"task-owner:{task_id}")
        if owner and owner != _request_task_owner(request):
            return Response({"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        cached = cache.get(f"task:{task_id}")
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        return Response({"status": "unknown", "error": "Task not found or expired"}, status=status.HTTP_404_NOT_FOUND)


class EnhancePromptView(APIView):
    authentication_classes = [TokenAuthentication, SupabaseJWTAuthentication]
    permission_classes = [AllowAny]
    throttle_scope = "ai_enhance"

    def post(self, request):
        serializer = EnhanceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "INVALID_REQUEST", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prompt = sanitize_input(serializer.validated_data["prompt"])
        if not prompt:
            return Response(
                {"success": False, "error": "Prompt contains prohibited content"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        level = serializer.validated_data["enhancement_level"]
        mode = serializer.validated_data.get("mode", "enhance")
        preferences = serializer.validated_data.get("preferences", {})
        preferred_model = serializer.validated_data.get("model", "auto")
        async_mode = _use_async(request)

        cache_key = _cache_key("enhance", {
            "prompt": prompt,
            "level": level,
            "mode": mode,
            "preferences": preferences,
            "model": preferred_model,
            "version": 2,
        })
        cached = cache.get(cache_key)
        if cached:
            cached = dict(cached)
            cached["from_cache"] = True
            return Response(cached, status=status.HTTP_200_OK)

        urls = _extract_urls(prompt)

        if _is_greeting(prompt):
            if async_mode:
                return _dispatch_task(run_greeting, prompt, preferred_model, _request=request)
            try:
                result = generate_with_fallback(
                    f"{MASTER_PROMPT}\n\n---\n**CURRENT MODE: MODE 5 — DEEP CONVERSATION**\n\nUser: {prompt}",
                    max_tokens=300, preferred_model=preferred_model,
                )
                return Response(
                    {
                        "success": True,
                        "type": "welcome",
                        "enhanced": result["text"],
                        "text": result["text"],
                        "model": result["model"],
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                logger.warning(f"Greeting failed: {e}")
                fallback = "Hello! I'm Promptrix AI. How can I help you today?"
                return Response(
                    {
                        "success": True,
                        "type": "welcome",
                        "enhanced": fallback,
                        "text": fallback,
                        "model": "fallback",
                    },
                    status=status.HTTP_200_OK,
                )

        if urls and mode == "generate":
            if async_mode:
                return _dispatch_task(run_url_analysis, prompt, urls[0], preferred_model, _request=request)
            try:
                url = urls[0]
                scraped = scrape_website_deep(url)
                if not scraped["success"]:
                    return Response(
                        {"success": False, "error": f"Failed to scrape: {scraped['error']}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                search_context = web_search(prompt)
                pages_summary = "\n".join(
                    f"- {p['title']}: {p['url']} ({len(p['text'])} chars)" for p in scraped["pages"]
                )
                analysis_prompt = build_website_analysis_prompt(
                    prompt, scraped["site_title"], url,
                    scraped["pages_scraped"], scraped["total_chars"],
                    pages_summary, scraped["combined_text"],
                    "\n".join(f"[{s['title']}] {s['snippet']}" for s in search_context),
                )
                response_data = generate_with_fallback(analysis_prompt, max_tokens=4000, preferred_model=preferred_model)
                result_dict = {
                    "success": True, "type": "url_analysis", "mode": "url_analysis",
                    "enhanced": response_data["text"], "text": response_data["text"],
                    "model": response_data["model"], "url": url,
                    "site_title": scraped["site_title"], "pages_scraped": scraped["pages_scraped"],
                    "total_chars": scraped["total_chars"],
                    "pages": [{"url": p["url"], "title": p["title"]} for p in scraped["pages"]],
                }
                cache.set(cache_key, result_dict, timeout=3600)
                return Response(result_dict, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"URL analysis failed: {e}")
                return Response({"success": False, "error": f"Analysis failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if _needs_deep_research(prompt):
            if async_mode:
                return _dispatch_task(run_deep_research, prompt, preferred_model, _request=request)
            try:
                response_data = generate_with_fallback(
                    f"{MASTER_PROMPT}\n\n---\n**CURRENT MODE: MODE 4 — TECH KNOWLEDGE EXPLORER**\n\nUser request: {prompt}",
                    max_tokens=4000, preferred_model=preferred_model,
                )
                return Response(
                    {
                        "success": True,
                        "type": "deep_research",
                        "enhanced": response_data["text"],
                        "text": response_data["text"],
                        "model": response_data["model"],
                        "classification": _classify_prompt(prompt),
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                logger.warning(f"Deep research failed, falling back to enhancement: {e}")

        if _needs_ideas(prompt) and mode == "generate":
            try:
                generator = IdeaGenerator()
                ideas = generator.generate()
                return Response({"success": True, "mode": "ideas", "ideas": ideas}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if mode == "generate":
            if async_mode:
                return _dispatch_task(run_generate, prompt, preferred_model, _request=request)
            try:
                response_data = generate_with_fallback(
                    f"{MASTER_PROMPT}\n\n---\n**CURRENT MODE: Auto-detected**\n\nUser prompt: {prompt}",
                    max_tokens=2000, preferred_model=preferred_model,
                )
                return Response(
                    {"success": True, "mode": "generate", "type": "enhance",
                     "enhanced": response_data["text"], "text": response_data["text"],
                     "model": response_data["model"]},
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if async_mode:
            return _dispatch_task(run_enhance, prompt, level, mode, preferred_model, _request=request)

        pipeline = PromptXPipeline()
        result = pipeline.execute(prompt=prompt, enhancement_level=level, user_preferences=preferences)
        response_data = result.to_dict()

        if result.success:
            self._save_history(request, result)
            cache.set(cache_key, response_data, timeout=3600)
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    def _save_history(self, request, result):
        try:
            history = PromptHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=request.session.session_key or '',
                original_prompt=result.original_prompt,
                enhanced_prompt=result.enhanced_prompt,
                enhancement_level=result.enhancement_level,
                detected_intent=result.intent,
                detected_domain=result.domain,
                detected_task_type=result.task_type,
                complexity_level=result.complexity,
                original_quality_score=result.original_quality,
                enhanced_quality_score=result.enhanced_quality,
                improvement_delta=result.improvement,
                original_scores_detail=result.original_scores,
                enhanced_scores_detail=result.enhanced_scores,
                validation_passed=result.validation_passed,
                validation_issues=result.validation_issues,
                validation_warnings=result.validation_warnings,
                processing_time_ms=result.processing_time_ms,
                enhancement_method=result.enhancement_method,
                pipeline_stages_completed=result.pipeline_stages,
            )
            # Dual-write to Supabase (fire-and-forget)
            try:
                sb_uid = get_supabase_user_id(request)
                if not _enqueue_background(sync_prompt_history_task, str(history.id), sb_uid):
                    logger.debug("Supabase history sync skipped: no background queue")
            except Exception as sync_err:
                logger.debug("Supabase history sync skipped: %s", sync_err)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")


class AnalyzePromptView(APIView):
    authentication_classes = [TokenAuthentication, SupabaseJWTAuthentication]
    permission_classes = [AllowAny]
    throttle_scope = "ai_light"

    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data['prompt']
        analyzer = PromptAnalyzer()
        analysis = analyzer.analyze(prompt)

        return Response({
            'success': True, 'prompt': prompt,
            'intent': {
                'primary': analysis.intent.primary_intent,
                'confidence': analysis.intent.confidence,
                'secondary': [{'intent': i, 'confidence': c} for i, c in analysis.intent.secondary_intents],
                'is_multi_intent': analysis.intent.is_multi_intent,
            },
            'domain': {'primary': analysis.intent.domain, 'confidence': analysis.intent.domain_confidence},
            'task_type': analysis.intent.task_type,
            'complexity': {
                'level': analysis.complexity.level, 'score': analysis.complexity.score,
                'factors': analysis.complexity.factors,
                'estimated_steps': analysis.complexity.estimated_steps,
                'requires_decomposition': analysis.complexity.requires_decomposition,
                'sub_tasks': analysis.complexity.sub_tasks,
            },
            'quality': {
                'overall': analysis.quality.overall, 'grade': analysis.quality.grade,
                'dimensions': analysis.quality.detail_scores,
                'bonuses': analysis.quality.bonuses, 'deductions': analysis.quality.deductions,
            },
            'elements': {
                'present': {k: v for k, v in analysis.quality.element_presence.items() if v},
                'missing': analysis.quality.missing_elements,
            },
            'nlp': {
                'entities': analysis.entities, 'keywords': analysis.keywords,
                'noun_phrases': analysis.noun_phrases, 'key_verbs': analysis.key_verbs,
                'programming_language': analysis.programming_language,
                'word_count': analysis.word_count, 'sentence_count': analysis.sentence_count,
            },
            'flags': {
                'has_question': analysis.has_question, 'has_negation': analysis.has_negation,
                'is_multi_part': analysis.is_multi_part,
                'requires_external_knowledge': analysis.requires_external_knowledge,
            },
            'resources': {'urls': analysis.urls, 'emails': analysis.emails,
                          'code_blocks_count': len(analysis.code_blocks)},
        }, status=status.HTTP_200_OK)


class ValidatePromptView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "ai_light"

    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        from .core.validator import PromptValidator
        from .core.fact_checker import FactChecker

        prompt = serializer.validated_data['prompt']
        validator = PromptValidator()
        validation = validator.validate(prompt)
        fact_checker = FactChecker()
        facts = fact_checker.check(prompt)

        return Response({
            'success': True, 'prompt': prompt,
            'validation': {
                'is_valid': validation.is_valid, 'score': validation.score,
                'checks_performed': validation.checks_performed,
                'issues': [{'severity': i.severity, 'category': i.category, 'message': i.message, 'suggestion': i.suggestion} for i in validation.issues],
                'warnings': [{'severity': w.severity, 'category': w.category, 'message': w.message, 'suggestion': w.suggestion} for w in validation.warnings],
                'info': [{'severity': i.severity, 'category': i.category, 'message': i.message, 'suggestion': i.suggestion} for i in validation.info],
                'resources_validated': validation.resources_validated,
            },
            'fact_check': {
                'status': facts.overall_status, 'items_checked': facts.items_checked,
                'items_verified': facts.items_verified, 'items_suspicious': facts.items_suspicious,
                'items': [{'claim': item.claim, 'status': item.status, 'confidence': item.confidence, 'details': item.details, 'source': item.source} for item in facts.items],
                'recommendations': facts.recommendations,
            },
        }, status=status.HTTP_200_OK)


class ComparePromptsView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "ai_light"

    def post(self, request):
        serializer = CompareRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        scorer = QualityScorer()
        analyzer = PromptAnalyzer()
        prompt_a = serializer.validated_data['prompt_a']
        prompt_b = serializer.validated_data['prompt_b']
        analysis_a = analyzer.analyze(prompt_a)
        analysis_b = analyzer.analyze(prompt_b)
        score_a = analysis_a.quality
        score_b = analysis_b.quality

        winner = 'prompt_a' if score_a.overall > score_b.overall else 'prompt_b'
        if abs(score_a.overall - score_b.overall) < 0.02:
            winner = 'tie'

        return Response({
            'success': True,
            'prompt_a': {'text': prompt_a, 'quality': score_a.overall, 'grade': score_a.grade,
                         'scores': score_a.detail_scores, 'intent': analysis_a.intent.primary_intent,
                         'domain': analysis_a.intent.domain, 'missing_elements': score_a.missing_elements},
            'prompt_b': {'text': prompt_b, 'quality': score_b.overall, 'grade': score_b.grade,
                         'scores': score_b.detail_scores, 'intent': analysis_b.intent.primary_intent,
                         'domain': analysis_b.intent.domain, 'missing_elements': score_b.missing_elements},
            'comparison': {
                'winner': winner,
                'quality_difference': round(abs(score_a.overall - score_b.overall), 3),
                'dimension_comparison': {
                    dim: {'prompt_a': score_a.detail_scores.get(dim, 0),
                          'prompt_b': score_b.detail_scores.get(dim, 0),
                          'better': 'prompt_a' if score_a.detail_scores.get(dim, 0) > score_b.detail_scores.get(dim, 0) else 'prompt_b'}
                    for dim in ['clarity', 'specificity', 'completeness', 'structure', 'actionability', 'grammar']
                },
            },
        }, status=status.HTTP_200_OK)


class ABTestView(APIView):
    authentication_classes = [TokenAuthentication, SupabaseJWTAuthentication]
    permission_classes = [AllowAny]
    throttle_scope = "ai_generate"

    def post(self, request):
        serializer = ABTestRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data['prompt']
        preferred_model = serializer.validated_data.get('model', 'auto')

        if _use_async(request):
            return _dispatch_task(run_ab_test, prompt, preferred_model, _request=request)

        variations = generate_ab_variations(prompt, preferred_model=preferred_model)
        comparison = compare_variations(prompt, variations)

        return Response({
            'success': True, 'original': prompt,
            'variations': comparison['variations'],
            'recommendation': comparison['recommendation'],
        }, status=status.HTTP_200_OK)


class AnalyzeURLView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "ai_scrape"

    def post(self, request):
        serializer = AnalyzeURLRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data['url']
        question = serializer.validated_data.get('question', '')

        return _dispatch_task(run_url_analysis, question or f"Analyze {url}", url, "auto", _request=request)


class WebSearchView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "ai_search"

    def post(self, request):
        serializer = WebSearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data['query']
        max_results = serializer.validated_data.get('max_results', 6)

        results = web_search(query, max_results)
        return Response({'success': True, 'query': query, 'results': results, 'count': len(results)}, status=status.HTTP_200_OK)


class IdeasView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "ai_light"

    def post(self, request):
        serializer = IdeasRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        count = serializer.validated_data.get('count', 5)
        generator = IdeaGenerator()
        ideas = generator.generate()
        if count < len(ideas):
            ideas = ideas[:count]

        return Response({'success': True, 'ideas': ideas, 'count': len(ideas)}, status=status.HTTP_200_OK)


class PromptHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get(self, request):
        queryset = PromptHistory.objects.filter(user=request.user).select_related('user').order_by('-created_at')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        data = [{
            'id': str(h.id),
            'original_prompt': h.original_prompt[:200],
            'enhanced_prompt': h.enhanced_prompt[:200],
            'intent': h.detected_intent,
            'domain': h.detected_domain,
            'enhancement_level': h.enhancement_level,
            'original_quality': h.original_quality_score,
            'enhanced_quality': h.enhanced_quality_score,
            'improvement': h.improvement_delta,
            'processing_time_ms': h.processing_time_ms,
            'created_at': h.created_at.isoformat(),
        } for h in page]

        return paginator.get_paginated_response(data)


class BatchEnhanceView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "ai_batch"

    def post(self, request):
        serializer = BatchEnhanceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        prompts = serializer.validated_data['prompts']
        level = serializer.validated_data['enhancement_level']
        pipeline = PromptXPipeline()
        results = []

        for i, prompt in enumerate(prompts):
            result = pipeline.execute(prompt=prompt, enhancement_level=level)
            results.append({
                'index': i, 'original': prompt,
                'enhanced': result.enhanced_prompt if result.success else None,
                'success': result.success,
                'quality_before': result.original_quality,
                'quality_after': result.enhanced_quality,
                'improvement': result.improvement,
                'grade_before': result.original_grade,
                'grade_after': result.enhanced_grade,
                'error': result.error,
            })

        return Response({
            'success': True, 'total': len(results),
            'successful': sum(1 for r in results if r['success']),
            'results': results,
        }, status=status.HTTP_200_OK)


class FeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            history = PromptHistory.objects.get(id=serializer.validated_data['prompt_id'], user=request.user)
            history.user_rating = serializer.validated_data['rating']
            history.user_feedback = serializer.validated_data.get('feedback', '')
            history.save()
            return Response({'success': True, 'message': 'Feedback recorded successfully'}, status=status.HTTP_200_OK)
        except PromptHistory.DoesNotExist:
            return Response({'success': False, 'error': 'Prompt not found'}, status=status.HTTP_404_NOT_FOUND)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        checks = {'app': 'ok', 'database': 'ok', 'cache': 'ok'}
        status_code = status.HTTP_200_OK

        from django.db import connections
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            checks['database'] = 'error'
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') != 'ok':
                checks['cache'] = 'error'
        except Exception:
            checks['cache'] = 'error'

        all_ok = all(v == 'ok' for v in checks.values())
        return Response({
            'status': 'healthy' if all_ok else 'degraded',
            'checks': checks,
            'version': '2.0.0',
        }, status=status_code)

class PromptProjectViewSet(viewsets.ModelViewSet):
    serializer_class = PromptProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PromptProject.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PromptAssetViewSet(viewsets.ModelViewSet):
    serializer_class = PromptAssetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        versions = PromptVersion.objects.order_by('-version_number')
        return (
            PromptAsset.objects
            .filter(user=self.request.user)
            .select_related('project', 'user')
            .prefetch_related(Prefetch('versions', queryset=versions, to_attr='prefetched_versions'))
            .annotate(versions_total=Count('versions'))
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def fork(self, request, pk=None):
        try:
            asset = (
                PromptAsset.objects
                .filter(Q(user=request.user) | Q(is_public=True), pk=pk)
                .prefetch_related('versions')
                .get()
            )
        except PromptAsset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        base_name = f"{asset.name} (Forked)"
        fork_name = base_name
        suffix = 2
        while PromptAsset.objects.filter(user=request.user, name=fork_name).exists():
            fork_name = f"{base_name} {suffix}"
            suffix += 1
        
        new_asset = PromptAsset.objects.create(
            user=request.user,
            name=fork_name,
            description=asset.description,
            is_public=False
        )
        for version in asset.versions.all():
            new_ver = PromptVersion.objects.create(
                asset=new_asset,
                version_number=version.version_number,
                content=version.content,
                commit_message=version.commit_message,
                quality_score=version.quality_score
            )
            # Dual-write version to Supabase
            try:
                _enqueue_background(sync_prompt_version_task, str(new_ver.id))
            except Exception:
                pass
        # Dual-write forked asset to Supabase
        try:
            sb_uid = get_supabase_user_id(request)
            if sb_uid:
                _enqueue_background(sync_prompt_asset_task, str(new_asset.id), sb_uid)
        except Exception:
            pass
        return Response(PromptAssetSerializer(new_asset).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        asset = self.get_object()
        asset.is_public = True
        asset.save()
        return Response({'status': 'Asset published successfully'})

    @action(detail=False, methods=['get'])
    def marketplace(self, request):
        versions = PromptVersion.objects.order_by('-version_number')
        public_assets = (
            PromptAsset.objects
            .filter(is_public=True)
            .exclude(user=request.user)
            .select_related('project', 'user')
            .prefetch_related(Prefetch('versions', queryset=versions, to_attr='prefetched_versions'))
            .annotate(versions_total=Count('versions'))
            .order_by('-created_at')
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(public_assets, request)
        data = PromptAssetSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @action(detail=True, methods=['post'])
    def commit(self, request, pk=None):
        content = request.data.get('content')
        commit_message = request.data.get('commit_message', 'Updated version')
        quality_score = request.data.get('quality_score', 0.0)
        history_id = request.data.get('history_reference')

        if not content:
            return Response({'error': 'content is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quality_score = float(quality_score)
        except (TypeError, ValueError):
            return Response({'error': 'quality_score must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            try:
                asset = PromptAsset.objects.select_for_update().get(pk=pk, user=request.user)
            except PromptAsset.DoesNotExist:
                return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)
            latest_version = asset.versions.order_by('-version_number').first()
            next_version_num = latest_version.version_number + 1 if latest_version else 1

            history_ref = None
            if history_id:
                try:
                    history_ref = PromptHistory.objects.get(id=history_id, user=request.user)
                except PromptHistory.DoesNotExist:
                    pass

            new_version = PromptVersion.objects.create(
                asset=asset,
                version_number=next_version_num,
                content=content,
                commit_message=commit_message,
                quality_score=quality_score,
                history_reference=history_ref
            )
        # Dual-write version to Supabase
        try:
            _enqueue_background(sync_prompt_version_task, str(new_version.id))
        except Exception:
            pass

        return Response(PromptVersionSerializer(new_version).data, status=status.HTTP_201_CREATED)

class PromptVersionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PromptVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PromptVersion.objects.filter(asset__user=self.request.user)

class ExecutePromptView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "ai_generate"

    def post(self, request):
        serializer = ExecutePromptSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt_text = serializer.validated_data['prompt_text']
        model = serializer.validated_data['model']
        max_tokens = serializer.validated_data['max_tokens']

        if _use_async(request):
            return _dispatch_task(run_execute, prompt_text, model, max_tokens, _request=request)

        try:
            start_time = time.time()
            result = generate_with_fallback(
                prompt=prompt_text,
                max_tokens=max_tokens,
                preferred_model=model,
            )
            execution_time = time.time() - start_time
            return Response({
                'success': True,
                'result_text': result['text'],
                'model_used': result['model'],
                'execution_time_seconds': round(execution_time, 2),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MultiModelView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "ai_multi_model"

    def post(self, request):
        serializer = MultiModelRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "INVALID_REQUEST", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prompt = serializer.validated_data["prompt"]
        return _dispatch_task(run_multi_model, prompt, _request=request)
