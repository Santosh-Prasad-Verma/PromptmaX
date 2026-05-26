import time
import logging
import uuid

logger = logging.getLogger('enhancer')


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id
        start_time = time.perf_counter()

        response = self.get_response(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        user_id = request.user.id if request.user.is_authenticated else None

        logger.info(
            "request",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2),
                'user_id': user_id,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            },
        )

        response['X-Request-ID'] = request_id
        return response
