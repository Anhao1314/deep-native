"""Loopback Anthropic relay: upstream credentials stay in parent memory.

No request bodies/auth headers are recorded. Provider SSE usage is preserved.
Both experimental arms use exactly this transport without model translation.
"""
import http.server
import json
import threading
import time
import urllib.error
import urllib.request

class Relay:
    def __init__(self, endpoint, credential):
        self.endpoint = endpoint.rstrip('/')
        self.credential = credential
        self.calls = []
        relay = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                started = time.monotonic()
                payload = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                data = json.loads(payload)
                call = {'path': self.path, 'requested_model': data.get('model'),
                        'max_tokens': data.get('max_tokens'), 'thinking': data.get('thinking'),
                        'temperature': data.get('temperature'), 'usage': {}, 'response_model': None,
                        'http_status': None, 'complete': False}
                relay.calls.append(call)
                headers = {k:v for k,v in self.headers.items()
                           if k.lower() not in {'host','authorization','x-api-key','content-length','connection','accept-encoding'}}
                headers['Authorization'] = 'Bearer ' + relay.credential
                headers['Accept-Encoding'] = 'identity'
                req = urllib.request.Request(relay.endpoint+self.path,data=payload,headers=headers,method='POST')
                buffer = b''
                try:
                    try:
                        response = urllib.request.urlopen(req,timeout=90)
                    except urllib.error.HTTPError as exc:
                        response = exc
                    with response:
                        call['http_status'] = response.status
                        self.send_response(response.status)
                        self.send_header('Content-Type',response.headers.get('Content-Type','application/json'))
                        self.end_headers()
                        while True:
                            chunk = response.read1(8192)
                            if not chunk:
                                break
                            buffer += chunk
                            while b'\n' in buffer:
                                line,buffer=buffer.split(b'\n',1)
                                if line.startswith(b'data: '):
                                    try:
                                        event=json.loads(line[6:])
                                        if event.get('type') == 'message_start':
                                            message=event.get('message',{})
                                            call['response_model']=message.get('model')
                                            call['usage'].update(message.get('usage',{}))
                                        elif event.get('type') == 'message_delta':
                                            call['usage'].update(event.get('usage',{}))
                                        elif event.get('type') == 'message_stop':
                                            call['complete']=True
                                    except (ValueError,TypeError):
                                        pass
                            self.wfile.write(chunk)
                            self.wfile.flush()
                        if not data.get('stream') and response.status == 200:
                            # Count-token requests are diagnostic, not generated completions.
                            call['complete']=True
                except (BrokenPipeError,ConnectionResetError):
                    call['transport_error']='client_disconnected'
                except Exception as exc:
                    # Exception strings can contain request details: persist class only.
                    call['transport_error']=type(exc).__name__
                finally:
                    call['duration_seconds']=round(time.monotonic()-started,4)
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    @property
    def url(self):
        return 'http://127.0.0.1:'+str(self.server.server_port)

    def close(self):
        self.server.shutdown()
        self.server.server_close()

def provider_tokens(calls):
    requests=[c for c in calls if '/messages' in c['path'] and 'count_tokens' not in c['path']]
    if not requests or any(not c['complete'] or not c['usage'] for c in requests):
        return None
    keys=['input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens']
    totals={k:sum(c['usage'].get(k,0) for c in requests) for k in keys}
    totals['total_tokens']=sum(totals.values())
    return totals
