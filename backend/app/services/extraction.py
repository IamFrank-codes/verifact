import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
try:
    import trafilatura
except ImportError:
    trafilatura = None

class ExtractionError(Exception):
    pass

def validate_public_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ExtractionError('Enter a valid public HTTP(S) URL.')
    hostname = parsed.hostname
    if hostname in {'localhost', '0.0.0.0'} or hostname.endswith('.local'):
        raise ExtractionError('Local and internal URLs cannot be retrieved.')
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ExtractionError('The URL host could not be resolved.') from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ExtractionError('Private, reserved, and internal network addresses are not allowed.')
    return value

def extract_article(url: str) -> dict:
    validate_public_url(url)
    try:
        with httpx.Client(follow_redirects=True, timeout=10, headers={'User-Agent': 'VeriFact/1.0 (evidence verification)'}) as client:
            response = client.get(url)
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise ExtractionError('The article response is too large to process safely.')
            if 'html' not in response.headers.get('content-type', '').lower():
                raise ExtractionError('The URL did not return an HTML article.')
    except httpx.HTTPError as exc:
        raise ExtractionError('VeriFact could not retrieve this article. Paste its text instead.') from exc
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    title = (soup.find('meta', property='og:title') or {}).get('content') or (soup.title.string.strip() if soup.title and soup.title.string else None)
    author = (soup.find('meta', attrs={'name': 'author'}) or {}).get('content')
    publisher = (soup.find('meta', property='og:site_name') or {}).get('content')
    published = (soup.find('meta', property='article:published_time') or {}).get('content')
    body = trafilatura.extract(html, include_comments=False, include_tables=False) if trafilatura else None
    if not body:
        body = ' '.join(p.get_text(' ', strip=True) for p in soup.find_all('p'))
    if len(body.strip()) < 100:
        raise ExtractionError('VeriFact could not extract enough article text. Paste the article text instead.')
    return {'url': str(response.url), 'title': title, 'author': author, 'publisher': publisher, 'published_at': published, 'text': body.strip()}
