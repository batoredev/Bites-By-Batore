"""Render one public web page to a JPEG for the review desk: python -m app.page_shot <url> <out.jpg>.

Runs in its own short-lived process so the API's event loop never hosts a browser. Every request
the page makes is checked: https only, public addresses only, a bounded count, no downloads.
"""
from __future__ import annotations

import ipaddress
import socket
import sys
from urllib.parse import urlparse

MAX_REQUESTS = 250


def main(url: str, out: str) -> int:
    from playwright.sync_api import sync_playwright

    hosts: dict[str, bool] = {}
    count = 0

    def public(target: str) -> bool:
        p = urlparse(target)
        if p.scheme in {"data", "blob"}:
            return True
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None, 443):
            return False
        if p.hostname not in hosts:
            try:
                addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
                hosts[p.hostname] = bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
            except OSError:
                hosts[p.hostname] = False
        return hosts[p.hostname]

    def route(r):
        nonlocal count
        count += 1
        if count <= MAX_REQUESTS and r.request.resource_type != "media" and public(r.request.url):
            r.continue_()
        else:
            r.abort()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1100, "height": 1400}, service_workers="block",
                                          accept_downloads=False, locale="en-IN")
            context.route("**/*", route)
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except Exception:  # a slow page still gets whatever has rendered
                pass
            page.wait_for_timeout(2000)
            # Some sites serve automated browsers an empty shell; a white picture helps nobody.
            text = 0
            for _ in range(3):  # pages that redirect themselves destroy the context mid-check
                try:
                    text = page.evaluate("document.body ? document.body.innerText.trim().length : 0")
                    break
                except Exception:
                    page.wait_for_timeout(1500)
            if text < 40:
                return 2
            page.screenshot(path=out, type="jpeg", quality=70)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
