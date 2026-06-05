#!/usr/bin/env python3
"""
BigQuery proxy for the SD-WAN Fleet Dashboard.
POST /bq  {query, token?}  → BigQuery REST API → response JSON
GET  /token                → {token: "..."}  (uses file, ADC, or gcloud)
GET  /health               → {"status":"ok"}
Runs on port 8082.

Token priority:
  1. token field in POST body
  2. /home/ubuntu/.bq_token file  (push via: push_gcp_token.sh)
  3. gcloud application-default
  4. gcloud auth print-access-token
"""
import http.server, urllib.request, urllib.error, json, subprocess, os, time

TOKEN_FILE = os.path.expanduser('~/.bq_token')
GCLOUD_PATHS = [
    os.path.expanduser('~/google-cloud-sdk/bin/gcloud'),
    '/usr/bin/gcloud',
    '/usr/local/bin/gcloud',
]
BQ_PROJECT = 'pa-sase-insights-prod-01'
BQ_URL = f'https://bigquery.googleapis.com/bigquery/v2/projects/{BQ_PROJECT}/queries'

_cache = {'token': None, 'exp': 0}

def find_gcloud():
    for p in GCLOUD_PATHS:
        if os.path.isfile(p):
            return p
    return 'gcloud'

def read_token_file():
    """Read token from ~/.bq_token if it exists and looks valid."""
    try:
        mtime = os.path.getmtime(TOKEN_FILE)
        # Token files pushed from local machine are valid ~1h; reject if older than 55 min
        if time.time() - mtime > 3300:
            return None
        tok = open(TOKEN_FILE).read().strip()
        if tok and len(tok) > 20:
            return tok
    except Exception:
        pass
    return None

def get_token():
    now = time.time()
    if _cache['token'] and now < _cache['exp']:
        return _cache['token']

    # Try token file first (fastest, doesn't need gcloud)
    tok = read_token_file()
    if tok:
        _cache['token'] = tok
        _cache['exp'] = now + 300  # re-check file every 5 min
        return tok

    # Fall back to gcloud
    gcloud = find_gcloud()
    for flag in ['auth application-default print-access-token',
                 'auth print-access-token']:
        try:
            tok = subprocess.check_output(
                [gcloud] + flag.split(),
                stderr=subprocess.DEVNULL,
                timeout=15
            ).decode().strip()
            if tok and len(tok) > 20:
                _cache['token'] = tok
                _cache['exp'] = now + 1700
                return tok
        except Exception:
            pass
    return None

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def reply(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            self.reply(200, {'status': 'ok'})
        elif self.path == '/token':
            tok = get_token()
            self.reply(200, {'token': tok, 'ok': bool(tok),
                             'source': 'file' if read_token_file() else 'gcloud'})
        else:
            self.reply(404, {'error': 'not found'})

    def do_POST(self):
        if self.path == '/push_token':
            # Accepts a plain-text token body and writes it to TOKEN_FILE
            length = int(self.headers.get('Content-Length', 0))
            tok = self.rfile.read(length).decode().strip()
            if not tok or len(tok) < 20:
                self.reply(400, {'error': 'invalid token'})
                return
            try:
                with open(TOKEN_FILE, 'w') as f:
                    f.write(tok)
                _cache['token'] = tok
                _cache['exp'] = time.time() + 3300
                self.reply(200, {'ok': True, 'message': 'token saved'})
            except Exception as e:
                self.reply(500, {'error': str(e)})
            return

        if self.path != '/bq':
            self.reply(404, {'error': 'not found'})
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length))
        except Exception:
            self.reply(400, {'error': 'invalid JSON'})
            return

        query = body.get('query', '').strip()
        token = body.get('token', '').strip() or get_token()

        if not query:
            self.reply(400, {'error': 'missing query'})
            return
        if not token:
            self.reply(401, {'error': 'no GCP token available — run: gcloud auth application-default print-access-token | curl -s -X POST http://10.9.224.231:8082/push_token --data-binary @-'})
            return

        bq_req = urllib.request.Request(
            BQ_URL,
            data=json.dumps({'query': query, 'useLegacySql': False, 'timeoutMs': 120000}).encode(),
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(bq_req, timeout=130) as r:
                self.reply(200, json.loads(r.read()))
        except urllib.error.HTTPError as e:
            err = e.read()
            # If BQ returns 401, clear cached token so next call re-reads the file
            if e.code == 401:
                _cache['token'] = None
                _cache['exp'] = 0
            self.send_response(e.code)
            self.cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(err)
        except Exception as e:
            self.reply(502, {'error': str(e)})

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', 8082), Handler)
    print(f'BQ proxy on :8082  (token file: {TOKEN_FILE})')
    server.serve_forever()
