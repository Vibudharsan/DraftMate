from pathlib import Path
p=Path('server.py');s=p.read_text(encoding='utf-8-sig')
s=s.replace("class Handler(SimpleHTTPRequestHandler):", "AI_REQUESTS=threading.BoundedSemaphore(2)\n\nclass Handler(SimpleHTTPRequestHandler):")
s=s.replace("    def do_GET(self):",'''    def log_message(self,format,*args):
        pass  # Do not log queries, filenames, prompts or credentials.
    def json_response(self,result,status=200):
        raw=json.dumps(result,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
    def do_HEAD(self):
        self.send_error(405)
    def do_POST(self):
        host=self.headers.get('Host','')
        if host not in ('127.0.0.1:4174','localhost:4174') or self.headers.get('Origin')!='http://'+host or self.headers.get('X-DraftMate-Request')!='1':
            self.json_response({'error':'Use the DraftMate page on this localhost origin.'},403);return
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            self.json_response({'error':'JSON required.'},415);return
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:length=0
        if length<=0 or length>29_000_000:
            self.json_response({'error':'Request too large or empty.'},413);return
        if not AI_REQUESTS.acquire(blocking=False):
            self.json_response({'error':'Two tasks are running. Wait for one to finish.'},429);return
        try:
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('Expected a JSON object.')
            from ai_service import generate,transcribe,configure
            from document_engine import parse_document
            handlers={'/api/ai/generate':generate,'/api/ai/configure':configure,'/api/ai/transcribe':transcribe,'/api/documents/parse':parse_document}
            fn=handlers.get(urlparse(self.path).path)
            if not fn:self.json_response({'error':'Unknown operation.'},404);return
            self.json_response(fn(data))
        except ValueError as exc:self.json_response({'error':str(exc)[:300]},400)
        except Exception:self.json_response({'error':'The task could not complete. Check file format, installed dependencies or provider availability.'},500)
        finally:AI_REQUESTS.release()
    def do_GET(self):''')
s=s.replace("        if path in ('/api/legal/search','/api/legal/status'):","""        if path=='/api/ai/status':
            from ai_service import provider_status
            from document_engine import vector_status
            self.json_response({**provider_status(),'vectors':vector_status()});return
        if path in ('/api/legal/search','/api/legal/status'):""")
s=s.replace("        if DATA.resolve() in target.parents or target.suffix in ('.py','.pyc','.cmd','.sqlite'):","        if target != ROOT and (target.parent != ROOT or target.suffix.lower() not in ('.html','.js','.css','.png','.jpg','.svg','.ico')):")
s=s.replace("    ThreadingHTTPServer(('127.0.0.1',4174),Handler).serve_forever()", "    class LocalServer(ThreadingHTTPServer):\n        allow_reuse_address=False\n    LocalServer(('127.0.0.1',4174),Handler).serve_forever()")
p.write_text(s,encoding='utf-8')
