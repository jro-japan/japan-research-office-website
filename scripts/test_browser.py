"""Render every allowlisted HTML page in Chromium at desktop and mobile widths."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright
from build_public import PAGES, build

dist = build()
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(dist)))
Thread(target=server.serve_forever, daemon=True).start()
origin = "http://127.0.0.1:" + str(server.server_port)
errors = []
count = 0
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height in [(320, 800), (390, 844), (768, 1024), (1024, 768), (1440, 900)]:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin + "/") else route.abort())
            for path in (*PAGES, "404.html"):
                url = origin + "/" + path
                response = page.goto(url, wait_until="load", timeout=15000)
                if not response or response.status != 200:
                    errors.append(f"{width} {path}: failed local load")
                    continue
                if page.locator("h1").count() != 1 or not page.locator("h1").is_visible():
                    errors.append(f"{width} {path}: H1 missing or hidden")
                size = page.evaluate("({width:document.documentElement.clientWidth, scroll:document.documentElement.scrollWidth})")
                if size["scroll"] > size["width"] + 2:
                    errors.append(f"{width} {path}: horizontal overflow {size}")
                if page.locator("nav a").count() == 0:
                    errors.append(f"{width} {path}: missing navigation")
                if path == "index.html":
                    for dest in ("/pricing.html", "/trust-center.html", "/ordering-payment.html"):
                        link = page.locator(f'a[href="{dest}"]').first
                        if not link.count() or not link.is_visible():
                            errors.append(f"{width}: missing buyer link {dest}")
                        else:
                            link.click(timeout=10000)
                            if not page.url.endswith(dest):
                                errors.append(f"{width}: navigation did not reach {dest}")
                            page.goto(url, wait_until="load")
                if path == "ordering-payment.html":
                    if not page.locator('a[href^="mailto:"]').first.is_visible():
                        errors.append(f"{width}: email route hidden")
                count += 1
            page.close()
        browser.close()
finally:
    server.shutdown()
if errors:
    print("\n".join("ERROR " + e for e in errors))
    raise SystemExit(1)
print(f"Chromium smoke: PASS ({count} page/viewport checks; local artifact only)")
