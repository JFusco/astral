"""Allow authenticated Gmail receipt navigation without exposing raw references."""
import re
from urllib.parse import parse_qs, urlsplit


def receipt_url(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 2048 or re.search(r'\s', value):
        raise ValueError('Invalid receipt URL')
    parsed = urlsplit(value)
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    if (parsed.scheme != 'https' or parsed.netloc != 'mail.google.com'
            or not re.fullmatch(r'/mail/u/(?:\d+/)?', parsed.path)
            or not re.fullmatch(r'(?:all|inbox)/[A-Za-z0-9_-]{8,100}', parsed.fragment)
            or set(query) - {'authuser'}
            or ('authuser' in query and (len(query['authuser']) != 1
                or not re.fullmatch(r'(?:\d+|[\w.+-]+@[\w.-]+)', query['authuser'][0])))):
        raise ValueError('Receipt links must open a Gmail message over HTTPS')
    return value


def receipt_links(charges):
    links = []
    seen = set()
    for charge in charges:
        if charge.get('status') == 'confirmed' and charge.get('role', 'charge') == 'charge':
            url = receipt_url(charge.get('receipt_url'))
            if url and url not in seen:
                seen.add(url)
                links.append({'provider': charge['provider'], 'url': url})
    return links
