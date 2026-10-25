from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request,urlopen
import json
from server import Handler
srv=ThreadingHTTPServer(('127.0.0.1',0),Handler)
Thread(target=srv.serve_forever,daemon=True).start()
try:
 for path in ['/api/legal/status','/api/legal/search?q=murder%20302&source=mapping']:
  req=Request('http://127.0.0.1:'+str(srv.server_port)+path,headers={'Host':'127.0.0.1:4174'})
  with urlopen(req,timeout=5) as r:data=json.load(r)
  assert data.get('sources') or data.get('items')
 print('HTTP smoke test passed: coverage and source-filtered retrieval.')
finally:srv.shutdown();srv.server_close()
