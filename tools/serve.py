#!/usr/bin/env python3
"""Serve the repository on 127.0.0.1 so the site in docs/ can read data/ and report/.

Usage: python3 tools/serve.py [PORT]   (default: an ephemeral port; the URL is printed)
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Server(http.server.ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer.server_bind calls socket.getfqdn(), which can stall for half a minute on
        # some machines; the name is not needed.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass


def main(argv: list[str]) -> None:
    port = int(argv[0]) if argv else 0
    handler = functools.partial(Handler, directory=str(ROOT))
    with Server(("127.0.0.1", port), handler) as httpd:
        print(f"http://127.0.0.1:{httpd.server_address[1]}/docs/", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main(sys.argv[1:])
