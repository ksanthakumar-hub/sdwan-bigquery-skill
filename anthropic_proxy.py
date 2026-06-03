#!/usr/bin/env python3
"""
Lightweight Anthropic API proxy — forwards POST /v1/messages to api.anthropic.com.
Adds CORS headers so a browser-served dashboard can call it.
Runs on port 8081.
"""
import http.server, urllib.request, urllib.error, json, ssl

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress access logs

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, x-api-key, anthropic-version, anthropic-dangerous-direct-browser-calls')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_POST(self):
        if self.path != '/v1/messages':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        api_key = self.headers.get('x-api-key', '')
        version = self.headers.get('anthropic-version', '2023-06-01')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': version,
            },
            method='POST'
        )

        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                self.send_cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            resp_body = e.read()
            self.send_response(e.code)
            self.send_cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as e:
            self.send_response(502)
            self.send_cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', 8081), ProxyHandler)
    print('Proxy listening on :8081')
    server.serve_forever()
