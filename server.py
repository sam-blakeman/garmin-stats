import http.server
import json
import os
import threading
import time
import tomllib

from garmin_data import fetch_stats

PORT = int(os.environ.get("GARMIN_STATS_PORT", 8765))
INTERVAL = int(os.environ.get("GARMIN_STATS_INTERVAL", 300))
RETRY = 60  # poll sooner after a failure
WEBROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")
THEME_COLORS = os.path.expanduser("~/.local/state/omarchy/current/theme/colors.toml")
THEME_NAME = os.path.expanduser("~/.local/state/omarchy/current/theme.name")

state = {"data": None, "error": None, "fetched_at": None, "interval": INTERVAL}

DEFAULT_THEME = {
    "name": None,
    "bg": "#040303",
    "fg": "#ffffff",
    "muted": "#7f6e6e",
    "accent": "#aaacac",
    "red": "#F82A2A",
    "magenta": "#f76e78",
    "yellow": "#fef348",
    "cyan": "#6bf7ff",
}


def load_theme():
    theme = dict(DEFAULT_THEME)
    try:
        with open(THEME_NAME) as f:
            theme["name"] = f.read().strip() or None
    except OSError:
        pass
    try:
        with open(THEME_COLORS, "rb") as f:
            raw = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return theme

    def pick(*keys):
        for key in keys:
            val = raw.get(key)
            if isinstance(val, str) and val.startswith("#"):
                return val
        return None

    theme["bg"] = pick("background", "color0") or theme["bg"]
    theme["fg"] = pick("foreground", "cursor", "color7") or theme["fg"]
    theme["muted"] = pick("muted", "dark_foreground", "color8") or theme["muted"]
    theme["accent"] = pick("accent", "color4") or theme["accent"]
    theme["red"] = pick("red", "color1") or theme["red"]
    theme["magenta"] = pick("magenta", "color5") or theme["magenta"]
    theme["yellow"] = pick("yellow", "color3") or theme["yellow"]
    theme["cyan"] = pick("cyan", "color6") or theme["cyan"]
    return theme


def poll():
    while True:
        try:
            state["data"] = fetch_stats()
            state["error"] = None
            delay = INTERVAL
        except Exception as e:
            # Keep the last good data; the UI flags it as stale.
            state["error"] = str(e) or type(e).__name__
            delay = min(RETRY, INTERVAL)
        state["fetched_at"] = time.time()
        time.sleep(delay)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBROOT, **kwargs)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/api/health", "/api/health/"):
            self._json(state)
        elif path in ("/api/theme", "/api/theme/"):
            self._json(load_theme())
        else:
            super().do_GET()

    def _json(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class Server(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    threading.Thread(target=poll, daemon=True).start()
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        httpd.serve_forever()
