# server-v8.py
import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import re
import glob
import hashlib
import time
import webbrowser
import threading
import socket

from config import (
    PORT, CACHE_DIR, ALLOWED_HOSTS, MAX_RESPONSE_BYTES,
    UPSTREAM_TIMEOUT, CACHE_TTL_SECONDS, HEADERS,
    DEFAULT_CHARACTERS, DEFAULT_SOURCE, DEFAULT_DOCK_POS
)

# ---------- утилиты ----------

def get_latest_html():
    files = glob.glob("armory6-v*.html") or glob.glob("armory6*.html")
    if not files:
        return None
    def ver(f):
        m = re.search(r'-v(\d+)', f)
        return int(m.group(1)) if m else 0
    files.sort(key=ver, reverse=True)
    return files[0]

def cache_path(key: str) -> str:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")

def is_host_allowed(url: str) -> bool:
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return False
    host = host.lower()
    if host in ALLOWED_HOSTS:
        return True
    return host.endswith(".wowhead.com") or host.endswith(".armorywowforever.com")

def is_private_host(url: str) -> bool:
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return True
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        ip = socket.gethostbyname(host)
        parts = ip.split(".")
        if parts[0] == "10": return True
        if parts[0] == "192" and parts[1] == "168": return True
        if parts[0] == "172" and 16 <= int(parts[1]) <= 31: return True
        if ip.startswith("169.254."): return True
    except Exception:
        pass
    return False

def read_capped(resp, limit: int) -> bytes:
    chunks, total = [], 0
    while True:
        chunk = resp.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ValueError(f"Ответ превышает лимит {limit} байт")
        chunks.append(chunk)
    return b"".join(chunks)

# ---------- хендлер ----------

class ArmoryProxyHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, parsed.query

        if path in ("/", ""):
            latest = get_latest_html()
            if latest:
                self.path = "/" + latest
            return super().do_GET()

        if path == "/api/config":
            return self._send_json({
                "characters": DEFAULT_CHARACTERS,
                "defaultSource": DEFAULT_SOURCE,
                "dockPos": DEFAULT_DOCK_POS
            })

        if path == "/clear-cache":
            count = 0
            for f in glob.glob(os.path.join(CACHE_DIR, "*.json")):
                try:
                    os.remove(f)
                    count += 1
                except Exception:
                    pass
            return self._send_json({"cleared": count})

        if path.startswith("/api/"):
            target = f"https://armorywowforever.com{path}"
            if query:
                target += f"?{query}"
            return self._proxy(target, bypass_cache=("refresh=1" in query))

        if path.startswith("/wh-proxy/"):
            raw = path[len("/wh-proxy/"):]
            if query:
                raw += f"?{query}"
            target = urllib.parse.unquote(raw)
            if not target.startswith("http"):
                target = "https://" + target.lstrip("/")
            return self._proxy(target, bypass_cache=("refresh=1" in query))

        return super().do_GET()

    def _send_json(self, obj, status: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, target_url: str, bypass_cache: bool = False):
        if not is_host_allowed(target_url) or is_private_host(target_url):
            return self._send_json({"error": "host not allowed"}, status=403)

        c_file = cache_path(target_url)

        if not bypass_cache and os.path.exists(c_file):
            fresh = True
            if CACHE_TTL_SECONDS > 0:
                try:
                    age = time.time() - os.path.getmtime(c_file)
                    fresh = age < CACHE_TTL_SECONDS
                except Exception:
                    fresh = False
            if fresh:
                try:
                    with open(c_file, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    body = cached["body"].encode("utf-8")
                    self.send_response(cached.get("status", 200))
                    self.send_header("Content-Type", cached.get("content_type", "application/json; charset=utf-8"))
                    self.send_header("X-Cache", "HIT")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                except Exception:
                    pass

        req = urllib.request.Request(target_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as resp:
                status = resp.getcode()
                ctype = resp.headers.get("Content-Type", "application/json; charset=utf-8")
                raw = read_capped(resp, MAX_RESPONSE_BYTES)
                body = raw.decode("utf-8", errors="replace")

                if status == 200 and body and not body.lstrip().startswith('{"error"'):
                    try:
                        with open(c_file, "w", encoding="utf-8") as f:
                            json.dump({"status": status, "content_type": ctype, "body": body}, f, ensure_ascii=False)
                    except Exception:
                        pass

                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("X-Cache", "MISS")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        except urllib.error.HTTPError as e:
            try:
                raw = read_capped(e, MAX_RESPONSE_BYTES)
            except Exception:
                raw = b'{"error":"upstream error"}'
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except ValueError as e:
            self._send_json({"error": "response too large", "detail": str(e)}, status=502)
        except Exception:
            self._send_json({"error": "upstream request failed"}, status=502)

class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    latest = get_latest_html()
    print(f"Starting server on http://127.0.0.1:{PORT}/")
    print(f"Serving HTML: {latest or 'Directory listing'}")
    threading.Timer(0.8, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/")).start()
    with ReusableTCPServer(("127.0.0.1", PORT), ArmoryProxyHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")