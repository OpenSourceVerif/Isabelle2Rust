#!/usr/bin/env python3
"""Serve only the generated dashboard on localhost; refresh reads new results."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlsplit
from build_dashboard import build
from build_report_preview import build as build_preview

lock = Lock()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path not in ['/', '/index.html', '/report-preview.html']:
            self.send_error(404)
            return
        with lock:
            body = (build_preview() if path == '/report-preview.html' else build()).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    args = parser.parse_args()
    build()
    server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'实验看板：http://127.0.0.1:{server.server_port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
