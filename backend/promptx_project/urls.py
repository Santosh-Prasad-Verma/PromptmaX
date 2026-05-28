from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import RedirectView
from django.shortcuts import render
from django.utils.cache import add_never_cache_headers
import os


def render_frontend(request, template_name):
    response = render(request, template_name)
    if settings.DEBUG:
        add_never_cache_headers(response)
    return response


def serve_frontend(request, path=''):
    frontend_dir = os.path.join(settings.BASE_DIR.parent, 'frontend')
    pages_dir = os.path.join(frontend_dir, 'pages')
    clean_path = path.strip('/')

    if not clean_path:
        return render_frontend(request, 'index.html')

    file_path = os.path.join(frontend_dir, clean_path)
    if os.path.isfile(file_path) and not clean_path.endswith('.html'):
        from django.views.static import serve
        response = serve(request, clean_path, document_root=frontend_dir)
        if settings.DEBUG:
            add_never_cache_headers(response)
        return response

    page_name = clean_path.rstrip('/')
    if not page_name.endswith('.html'):
        page_name = f'{page_name}.html'
    template_path = os.path.join(pages_dir, page_name)
    if os.path.isfile(template_path):
        return render_frontend(request, f'pages/{page_name}')
    return render_frontend(request, 'index.html')


urlpatterns = [
    path('', serve_frontend),
    path('api/v1/', include('enhancer.urls')),
    path('', include('social_django.urls')),
    re_path(r'^(?P<path>.+)/?$', serve_frontend),
]
