import re
import ipaddress
import logging
import requests
import socket
from urllib.parse import urljoin, urlparse, unquote
from django.conf import settings

logger = logging.getLogger('enhancer')

_SCRAPE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

_VALUABLE_PATHS = [
    '/', '/about', '/about-us', '/features', '/pricing', '/docs',
    '/documentation', '/api', '/api-docs', '/developers', '/tech',
    '/blog', '/careers', '/team', '/product', '/solutions',
    '/how-it-works', '/integrations', '/security', '/enterprise',
]


def _is_public_ip(address):
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'}:
        raise ValueError('Only http and https URLs are supported')
    if not parsed.hostname:
        raise ValueError('URL must include a hostname')

    hostname = parsed.hostname.rstrip('.').lower()
    if hostname in {'localhost', 'localhost.localdomain'}:
        raise ValueError('Localhost URLs are not allowed')

    try:
        addresses = {
            info[4][0]
            for info in socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == 'https' else 80))
        }
    except socket.gaierror as exc:
        raise ValueError('Could not resolve URL hostname') from exc

    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise ValueError('Private, local, or reserved network addresses are not allowed')


def _safe_get(url, timeout):
    scraper_config = settings.PROMPTX.get('SCRAPER', {})
    max_redirects = scraper_config.get('MAX_REDIRECTS', 5)
    max_bytes = scraper_config.get('MAX_RESPONSE_BYTES', 1_000_000)
    current_url = url

    for _ in range(max_redirects + 1):
        _validate_public_url(current_url)
        resp = requests.get(
            current_url,
            headers=_SCRAPE_HEADERS,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )

        if 300 <= resp.status_code < 400 and resp.headers.get('Location'):
            current_url = urljoin(current_url, resp.headers['Location'])
            resp.close()
            continue

        content_type = resp.headers.get('Content-Type', '').lower()
        if content_type and not any(kind in content_type for kind in ('text/html', 'application/xhtml+xml', 'text/plain')):
            resp.close()
            raise ValueError('URL did not return an HTML or text response')

        content_length = resp.headers.get('Content-Length')
        if content_length and int(content_length) > max_bytes:
            resp.close()
            raise ValueError(f'Response too large; limit is {max_bytes} bytes')

        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536, decode_unicode=False):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                resp.close()
                raise ValueError(f'Response too large; limit is {max_bytes} bytes')
            chunks.append(chunk)

        resp._content = b''.join(chunks)
        resp.encoding = resp.encoding or 'utf-8'
        return resp

    raise ValueError('Too many redirects')


def _clean_html(html, max_chars=8000):
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ''
    html = re.sub(
        r'<(script|style|noscript|nav|footer|header|aside|iframe|svg|form|button|input|select|textarea|meta|link)[^>]*>.*?</\1>',
        '', html, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(r'<[^>]+>', ' ', html)
    for ent, ch in [
        ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'),
        ('&#39;', "'"), ('&nbsp;', ' '), ('&mdash;', '—'), ('&ndash;', '–'),
        ('&hellip;', '...'), ('&copy;', '©'), ('&reg;', '®'),
    ]:
        text = text.replace(ent, ch)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(l.strip() for l in text.splitlines() if l.strip())
    if len(text) > max_chars:
        text = text[:max_chars] + f'\n[truncated at {max_chars} chars]'
    return title, text


def _extract_internal_links(html, base_url):
    base = urlparse(base_url)
    base_root = f"{base.scheme}://{base.netloc}"
    hrefs = re.findall(r'<a[^>]+href=["\']([^"\'#?]+)["\']', html, re.IGNORECASE)
    seen = set()
    links = []
    for href in hrefs:
        full = urljoin(base_root, href)
        parsed = urlparse(full)
        if (parsed.netloc == base.netloc
                and not re.search(r'\.(pdf|jpg|png|gif|svg|zip|css|js|ico|woff)$', parsed.path, re.I)
                and full not in seen):
            seen.add(full)
            links.append(full)
    return links


def scrape_url(url, max_chars=8000):
    scraper_config = settings.PROMPTX.get('SCRAPER', {})
    timeout = scraper_config.get('REQUEST_TIMEOUT', 12)
    try:
        resp = _safe_get(url, timeout)
        resp.raise_for_status()
        html = resp.text
        title, text = _clean_html(html, max_chars)
        links = _extract_internal_links(html, url)
        return {'success': True, 'url': url, 'title': title or url,
                'text': text, 'char_count': len(text), 'links': links, 'error': None}
    except requests.exceptions.Timeout:
        return {'success': False, 'url': url, 'title': '', 'text': '', 'char_count': 0, 'links': [], 'error': f'Timed out after {timeout}s'}
    except requests.exceptions.HTTPError as e:
        return {'success': False, 'url': url, 'title': '', 'text': '', 'char_count': 0, 'links': [], 'error': f'HTTP {e.response.status_code}'}
    except ValueError as e:
        return {'success': False, 'url': url, 'title': '', 'text': '', 'char_count': 0, 'links': [], 'error': str(e)}
    except Exception as e:
        return {'success': False, 'url': url, 'title': '', 'text': '', 'char_count': 0, 'links': [], 'error': str(e)}


def scrape_website_deep(base_url, max_pages=None, chars_per_page=None):
    scraper_config = settings.PROMPTX.get('SCRAPER', {})
    max_pages = max_pages or scraper_config.get('MAX_PAGES', 8)
    chars_per_page = chars_per_page or scraper_config.get('CHARS_PER_PAGE', 6000)
    parsed = urlparse(base_url)
    base_root = f"{parsed.scheme}://{parsed.netloc}"

    home = scrape_url(base_url, chars_per_page)
    if not home['success']:
        return {'success': False, 'base_url': base_url, 'pages_scraped': 0,
                'pages': [], 'combined_text': '', 'total_chars': 0, 'error': home['error']}

    pages = [{'url': base_url, 'title': home['title'], 'text': home['text']}]
    candidates = [urljoin(base_root, path) for path in _VALUABLE_PATHS]
    for link in home.get('links', [])[:30]:
        if link not in candidates:
            candidates.append(link)

    scraped_urls = {base_url}
    for candidate in candidates:
        if len(pages) >= max_pages:
            break
        if candidate in scraped_urls:
            continue
        scraped_urls.add(candidate)
        result = scrape_url(candidate, chars_per_page)
        if result['success'] and result['char_count'] > 200:
            pages.append({'url': candidate, 'title': result['title'], 'text': result['text']})

    combined_parts = [f"=== PAGE: {p['title']} ===\nURL: {p['url']}\n\n{p['text']}" for p in pages]
    combined_text = '\n\n' + ('\n\n' + '─' * 60 + '\n\n').join(combined_parts)

    return {
        'success': True, 'base_url': base_url, 'site_title': home['title'],
        'pages_scraped': len(pages), 'pages': pages, 'combined_text': combined_text,
        'total_chars': sum(len(p['text']) for p in pages), 'error': None,
    }


def web_search(query, max_results=6):
    try:
        params = {'q': query, 'kl': 'us-en', 'kp': '-1'}
        resp = requests.get('https://html.duckduckgo.com/html/', params=params, headers=_SCRAPE_HEADERS, timeout=10)
        resp.raise_for_status()
        html = resp.text
        results = []
        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        for url, title_html, snippet_html in blocks[:max_results]:
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet_html).strip()
            real_url_match = re.search(r'uddg=([^&]+)', url)
            if real_url_match:
                url = unquote(real_url_match.group(1))
            if title and url.startswith('http'):
                results.append({'title': title, 'url': url, 'snippet': snippet})
        return results
    except Exception as e:
        logger.warning(f"Web search error: {e}")
        return []
