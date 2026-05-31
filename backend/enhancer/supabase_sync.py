"""
Supabase Sync Service — dual-write from Django to Supabase.

Uses the Supabase REST API (PostgREST) with the service_role key
to bypass RLS and write data from the Django backend.

Failures are logged but NEVER block the Django response.
"""

import logging
import json
from urllib.parse import urljoin

logger = logging.getLogger('enhancer')


def _get_config():
    """Lazy-load Supabase config from Django settings."""
    from django.conf import settings
    url = getattr(settings, 'SUPABASE_URL', '').strip()
    key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not url or not key:
        return None
    return {'url': url, 'key': key}


def _post(table, data, config):
    """POST a row to Supabase via PostgREST."""
    import urllib.request
    import urllib.error

    endpoint = urljoin(config['url'] + '/', f'rest/v1/{table}')
    headers = {
        'apikey': config['key'],
        'Authorization': f'Bearer {config["key"]}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }

    body = json.dumps(data, default=str).encode('utf-8')
    req = urllib.request.Request(endpoint, data=body, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        logger.warning(
            "Supabase sync failed for %s: HTTP %s — %s",
            table, e.code, error_body[:500]
        )
        return None
    except Exception as e:
        logger.warning("Supabase sync failed for %s: %s", table, str(e))
        return None


def _patch(table, match_column, match_value, data, config):
    """PATCH (update) a row in Supabase via PostgREST."""
    import urllib.request
    import urllib.error

    endpoint = urljoin(
        config['url'] + '/',
        f'rest/v1/{table}?{match_column}=eq.{match_value}'
    )
    headers = {
        'apikey': config['key'],
        'Authorization': f'Bearer {config["key"]}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }

    body = json.dumps(data, default=str).encode('utf-8')
    req = urllib.request.Request(endpoint, data=body, headers=headers, method='PATCH')

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        logger.warning(
            "Supabase patch failed for %s: HTTP %s — %s",
            table, e.code, error_body[:500]
        )
        return None
    except Exception as e:
        logger.warning("Supabase patch failed for %s: %s", table, str(e))
        return None


def sync_prompt_history(history_obj, supabase_user_id=None):
    """
    Sync a PromptHistory record to Supabase.

    Args:
        history_obj: Django PromptHistory model instance.
        supabase_user_id: UUID string of the Supabase auth user. If None,
                          attempts to resolve from the Django user's email.
    """
    config = _get_config()
    if not config:
        return  # Supabase not configured, skip silently

    data = {
        'id': str(history_obj.id),
        'user_id': supabase_user_id,
        'session_id': history_obj.session_id or '',
        'original_prompt': history_obj.original_prompt,
        'enhanced_prompt': history_obj.enhanced_prompt,
        'enhancement_level': history_obj.enhancement_level,
        'detected_intent': history_obj.detected_intent,
        'detected_domain': history_obj.detected_domain,
        'detected_task_type': history_obj.detected_task_type,
        'complexity_level': getattr(history_obj, 'complexity_level', 'medium'),
        'original_quality_score': history_obj.original_quality_score,
        'enhanced_quality_score': history_obj.enhanced_quality_score,
        'improvement_delta': history_obj.improvement_delta,
        'original_scores_detail': history_obj.original_scores_detail or {},
        'enhanced_scores_detail': history_obj.enhanced_scores_detail or {},
        'validation_passed': history_obj.validation_passed,
        'validation_issues': history_obj.validation_issues or [],
        'validation_warnings': history_obj.validation_warnings or [],
        'processing_time_ms': history_obj.processing_time_ms,
        'enhancement_method': history_obj.enhancement_method,
        'pipeline_stages_completed': history_obj.pipeline_stages_completed or [],
        'rules_applied': history_obj.rules_applied or [],
        'user_rating': history_obj.user_rating,
        'user_feedback': history_obj.user_feedback or '',
    }

    # Remove None user_id to avoid FK constraint violation
    if not data['user_id']:
        data.pop('user_id', None)

    status_code = _post('prompt_history', data, config)
    if status_code and 200 <= status_code < 300:
        logger.debug("Synced prompt_history %s to Supabase", history_obj.id)
    return status_code


def sync_prompt_project(project_obj, supabase_user_id):
    """Sync a PromptProject record to Supabase."""
    config = _get_config()
    if not config or not supabase_user_id:
        return

    data = {
        'id': str(project_obj.id),
        'user_id': supabase_user_id,
        'name': project_obj.name,
        'description': project_obj.description or '',
    }

    status_code = _post('prompt_projects', data, config)
    if status_code and 200 <= status_code < 300:
        logger.debug("Synced prompt_project %s to Supabase", project_obj.id)
    return status_code


def sync_prompt_asset(asset_obj, supabase_user_id):
    """Sync a PromptAsset record to Supabase."""
    config = _get_config()
    if not config or not supabase_user_id:
        return

    data = {
        'id': str(asset_obj.id),
        'project_id': str(asset_obj.project_id) if asset_obj.project_id else None,
        'user_id': supabase_user_id,
        'name': asset_obj.name,
        'description': asset_obj.description or '',
        'is_public': asset_obj.is_public,
    }

    status_code = _post('prompt_assets', data, config)
    if status_code and 200 <= status_code < 300:
        logger.debug("Synced prompt_asset %s to Supabase", asset_obj.id)
    return status_code


def sync_prompt_version(version_obj):
    """Sync a PromptVersion record to Supabase."""
    config = _get_config()
    if not config:
        return

    data = {
        'id': str(version_obj.id),
        'asset_id': str(version_obj.asset_id),
        'version_number': version_obj.version_number,
        'content': version_obj.content,
        'commit_message': version_obj.commit_message or 'Initial version',
        'quality_score': version_obj.quality_score,
        'history_ref': str(version_obj.history_reference_id) if version_obj.history_reference_id else None,
    }

    status_code = _post('prompt_versions', data, config)
    if status_code and 200 <= status_code < 300:
        logger.debug("Synced prompt_version %s to Supabase", version_obj.id)
    return status_code


def sync_user_plan(supabase_user_id, plan, price_rs=0):
    """Update a user's plan in the Supabase profiles table."""
    config = _get_config()
    if not config or not supabase_user_id:
        return

    data = {
        'plan': plan,
        'price_rs': price_rs,
    }

    status_code = _patch('profiles', 'id', supabase_user_id, data, config)
    if status_code and 200 <= status_code < 300:
        logger.debug("Synced user plan for %s to Supabase", supabase_user_id)
    return status_code


def get_supabase_user_id(request):
    """
    Extract the Supabase user ID (sub) from a request that was
    authenticated via SupabaseJWTAuthentication.

    Returns the UUID string or None.
    """
    payload = getattr(request, 'supabase_jwt_payload', None)
    if payload:
        return payload.get('sub')

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.lower().startswith('bearer '):
        return None

    token = auth_header.split()[1]
    try:
        import jwt as pyjwt
        from django.conf import settings
        secret = getattr(settings, 'SUPABASE_JWT_SECRET', '')
        if not secret:
            return None
        payload = pyjwt.decode(
            token, secret, algorithms=['HS256'],
            options={"verify_aud": False, "verify_exp": True}
        )
        return payload.get('sub')
    except Exception:
        return None
