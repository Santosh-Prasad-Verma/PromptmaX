from django.urls import path, include, re_path
from django.conf import settings
from django.shortcuts import render
from django.utils.cache import add_never_cache_headers
from pathlib import Path


def render_frontend(request, template_name):
    response = render(request, template_name)
    if settings.DEBUG:
        add_never_cache_headers(response)
    return response


def serve_frontend(request, path=''):
    frontend_root = Path(settings.BASE_DIR.parent, 'frontend').resolve()
    pages_root = (frontend_root / 'pages').resolve()
    frontend_dir = str(frontend_root)
    clean_path = path.strip('/')

    if not clean_path:
        return render_frontend(request, 'index.html')

    file_path = (frontend_root / clean_path).resolve()
    if (
        frontend_root in file_path.parents
        and file_path.is_file()
        and not clean_path.endswith('.html')
    ):
        from django.views.static import serve
        response = serve(request, clean_path, document_root=frontend_dir)
        if settings.DEBUG:
            add_never_cache_headers(response)
        return response

    page_name = clean_path.rstrip('/')
    if not page_name.endswith('.html'):
        page_name = f'{page_name}.html'
    template_path = (pages_root / page_name).resolve()
    if pages_root in template_path.parents and template_path.is_file():
        return render_frontend(request, f'pages/{page_name}')
    return render_frontend(request, 'index.html')


urlpatterns = [
    path('', serve_frontend),
    path('api/v1/', include('enhancer.urls')),
    re_path(r'^(?P<path>.+)/?$', serve_frontend),
]
