import http.server
import json
import os
import socketserver
import threading
import time

from garmin_data import fetch_stats

PORT = 8765
INTERVAL = 300
WEBROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")

state = {"data": None, "error": None, "fetched_at": None}


def poll():
    while True:
        try:
            state["data"] = fetch_stats()
            state["error"] = None
        except Exception as e:
            state["error"] = str(e)
        state["fetched_at"] = time.time()
        time.sleep(INTERVAL)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBROOT, **kwargs)

    def do_GET(self):
        if self.path in ("/api/health", "/api/health/"):
            body = json.dumps(state).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, *args):
        pass


threading.Thread(target=poll, daemon=True).start()

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    httpd.serve_forever()