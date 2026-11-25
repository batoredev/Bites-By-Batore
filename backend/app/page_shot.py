"""Render one public web page to a JPEG for the review desk: python -m app.page_shot <url> <out.jpg>.

Runs in its own short-lived process so the API's event loop never hosts a browser.

Network safety is enforced at the connection, not per request: Chromium sends every request
(redirect hops, subresources, WebSockets) through a small in-process CONNECT proxy that resolves
the host itself, refuses unless every address is public, and connects to the address it checked.
Redirects to private hosts and DNS rebinding therefore have nothing to slip past. Plain http,
non-443 ports, QUIC and non-proxied WebRTC are refused.
"""
from __future__ import annotations

import ipaddress
import select
import socket
import socketserver
import sys
import threading
from urllib.parse import urlparse

MAX_REQUESTS = 250


def public_ip(host: str) -> str | None:
    """The address to connect to, only when every address the host resolves to is public."""
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        ips = [a[4][0] for a in addresses]
    except (OSError, UnicodeError):
        return None
    if not ips or not all(ipaddress.ip_address(ip.split("%")[0]).is_global for ip in ips):
        return None
    return ips[0]


class _Tunnel(socketserver.StreamRequestHandler):
    timeout = 20

    def handle(self):
        request = self.rfile.readline(4096).decode("latin-1").split()
        while self.rfile.readline(4096) not in (b"\r\n", b"\n", b""):
            pass  # the browser's proxy headers carry nothing we need
        if len(request) < 2 or request[0].upper() != "CONNECT":
            return self._refuse()
        host, _, port = request[1].rpartition(":")
        ip = public_ip(host.strip("[]")) if port == "443" else None
        if ip is None:
            return self._refuse()
        try:
            upstream = socket.create_connection((ip, 443), timeout=10)
        except OSError:
            return self._refuse()
        self.wfile.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        self.wfile.flush()
        client = self.connection
        try:
            sockets = [client, upstream]
            while True:
                ready, _, _ = select.select(sockets, [], [], 20)
                if not ready:
                    break
                for s in ready:
                    data = s.recv(65536)
                    if not data:
                        return
                    (upstream if s is client else client).sendall(data)
        except OSError:
            pass
        finally:
            upstream.close()

    def _refuse(self):
        self.wfile.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")


class _Proxy(socketserver.ThreadingTCPServer):
    daemon_threads = True


def start_proxy() -> tuple[_Proxy, int]:
    proxy = _Proxy(("127.0.0.1", 0), _Tunnel)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    return proxy, proxy.server_address[1]


def main(url: str, out: str) -> int:
    from playwright.sync_api import sync_playwright

    count = 0

    def route(r):  # a cheap first filter; the proxy is what actually enforces public addresses
        nonlocal count
        count += 1
        scheme = urlparse(r.request.url).scheme
        if count <= MAX_REQUESTS and r.request.resource_type != "media" and scheme in {"https", "data", "blob"}:
            r.continue_()
        else:
            r.abort()

    proxy, port = start_proxy()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=[
                f"--proxy-server=http://127.0.0.1:{port}",
                "--proxy-bypass-list=<-loopback>",  # Chromium otherwise sends localhost around the proxy
                "--disable-quic",
                "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                "--webrtc-ip-handling-policy=disable_non_proxied_udp",
            ])
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
    finally:
        proxy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
