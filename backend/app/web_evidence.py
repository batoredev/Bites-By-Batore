"""Read text from explicitly configured official-source hosts, with bounded IO."""

import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urlparse
import httpx
from .config import settings
from .providers import Unavailable, quota
from .collection_control import backoff, success


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


from .performance import measured


@measured("first_party_http")
def read_official_html(db, url, allow_unverified_host=False):
    p = urlparse(url)
    if (
        p.scheme != "https"
        or p.username
        or p.password
        or p.port not in (None, 443)
        or (not allow_unverified_host and p.hostname not in settings().web_evidence_hosts)
    ):
        raise Unavailable("This evidence host is not enabled; an administrator can review and configure it")
    try:
        addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
            raise Unavailable("Evidence host must resolve to public addresses")
        quota(db, host=p.hostname)
        with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
            with client.stream("GET", url, headers={"User-Agent": "BatoreEvidence/0.2"}) as response:
                if response.status_code in {429, 503, 504}:
                    backoff(db, p.hostname, headers=response.headers)
                if response.status_code != 200 or "text/html" not in response.headers.get("content-type", ""):
                    raise Unavailable("Official page unavailable, redirected or not readable HTML")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 3 * 1024 * 1024:
                        raise Unavailable("Official page exceeds the text collection limit")
                success(db, p.hostname)
                return raw.decode("utf-8", errors="replace")
    except (OSError, httpx.HTTPError) as exc:
        raise Unavailable("Official page could not be retrieved") from exc


def read_official_page(db, url):
    parser = VisibleText()
    parser.feed(read_official_html(db, url))
    text = "\n".join(parser.parts)[:20000]
    if len(text) < 40:
        raise Unavailable("Page needs rendered-browser or manual review; no readable text obtained")
    return text
