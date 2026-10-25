"""Local DraftMate server: static UI plus allowlisted public source readers."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse, urljoin, parse_qs
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json, re, threading, time, sys, ssl, xml.etree.ElementTree as ET

from legal_reference import search as legal_search, status as legal_status
ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
SCI = 'https://www.sci.gov.in/argument-transcripts-2/'
FEEDS = [('Times of India', 'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms'),
         ('The Indian Express', 'https://indianexpress.com/section/india/feed/')]
LOCK = threading.Lock()
def now(): return datetime.now(timezone.utc).isoformat()
def fetch(url):
    req = Request(url, headers={'User-Agent': 'DraftMateLocalPrototype/1.0 (public-source reader)'})
    with urlopen(req, timeout=18) as response:
        raw = response.read(3_000_001)
        if len(raw) > 3_000_000: raise ValueError('Source exceeds size limit')
        return raw
def load(name, default):
    try: return json.loads((DATA / name).read_text(encoding='utf-8'))
    except (OSError, ValueError): return default
def write(name, data):
    DATA.mkdir(exist_ok=True)
    temp = DATA / (name + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temp.replace(DATA / name)
def safe_url(value):
    return value if urlparse(value).scheme in ('https', 'http') else ''
def category(title):
    groups = [('Courts & law', r'court|judge|judicial|bail|verdict|petition|lawyer|justice|legal'),
              ('Crime & investigation', r'police|arrest|murder|crime|fraud|probe|investigation'),
              ('Policy & governance', r'government|minister|parliament|policy|election|bill\b'),
              ('Business & economy', r'bank|econom|tax|market|company|business'),
              ('Environment', r'climate|pollution|environment|forest')]
    return next((label for label, pattern in groups if re.search(pattern,title,re.I)), 'General')
def parse_feed(source, raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('Unsupported XML declaration')
    root = ET.fromstring(raw)
    items=[]
    for item in root.findall('.//item')[:100]:
        title=' '.join((item.findtext('title') or '').split())
        url=safe_url((item.findtext('link') or '').strip())
        if not title or not url: continue
        try: date=parsedate_to_datetime(item.findtext('pubDate') or '').astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError): date=None
        items.append({'title':title,'url':url,'source':source,'publishedAt':date,'category':category(title),'fetchedAt':now()})
    return items
def feed_job(pair):
    source,url=pair
    try: return {'source':source,'status':'ok'},parse_feed(source,fetch(url))
    except Exception as exc: return {'source':source,'status':'unavailable','message':str(exc)[:160]},[]
def news(refresh=False):
    with LOCK:
        cached=load('news.json', {'items':[], 'sources':[]})
        if not refresh: return cached
        entries={i['url']:i for i in cached['items']}
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(feed_job,FEEDS))
        for _,items in results:
            for item in items: entries[item['url']]=item
        result={'items':sorted(entries.values(),key=lambda i:i['publishedAt'] or '',reverse=True)[:2000],
                'sources':[s for s,_ in results], 'lastAttempt':now(), 'lastSuccess':now() if any(items for _,items in results) else cached.get('lastSuccess')}
        write('news.json',result)
        return result

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None; self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='tr': self.row=[]; self.links=[]
        if tag in ('td','th') and self.row is not None: self.cell=[]
        if tag=='a' and self.cell is not None and attrs.get('href'): self.links.append(urljoin(SCI,attrs['href']))
    def handle_data(self,text):
        if self.cell is not None: self.cell.append(text)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(' '.join(self.cell).split())); self.cell=None
        if tag=='tr' and self.row is not None:
            self.rows.append((self.row,self.links)); self.row=None
def parse_cases(raw):
    parser=TableParser(); parser.feed(raw.decode('utf-8',errors='replace')); records={}
    for cells,links in parser.rows:
        dates=[(i,re.search(r'\d{2}-[A-Za-z]{3}-\d{4}',c)) for i,c in enumerate(cells)]
        match=next(((i,m) for i,m in dates if m),None)
        urls=[u for u in links if 'view-pdf' in u or 'transcrib' in u or '.pdf' in u]
        if not match or not urls: continue
        index,m=match
        if index<1: continue
        name=cells[index-1]; number=' '.join(cells[:index-1])
        if not name: continue
        key=re.sub(r'[^a-zA-Z0-9]','',number or name)
        item=records.setdefault('PUBLIC-'+key,{'id':'PUBLIC-'+key,'name':name,'number':number,'type':'Public case','origin':'public','source':SCI,'hearings':[]})
        item['hearings'].append({'date':datetime.strptime(m.group(),'%d-%b-%Y').date().isoformat(),'url':safe_url(urls[0])})
    for item in records.values(): item['hearings'].sort(key=lambda h:h['date'],reverse=True)
    return list(records.values())
def cases(refresh=False):
    with LOCK:
        cached=load('public-cases.json',{'items':[],'status':'not_loaded'})
        if not refresh: return cached
        try:
            items=parse_cases(fetch(SCI))
            if not items: raise ValueError('No transcript rows found; source layout may have changed')
            result={'items':items,'status':'ok','fetchedAt':now(),'source':SCI}
            write('public-cases.json',result); return result
        except Exception as exc:
            return {**cached,'status':'unavailable','message':str(exc)[:180],'lastAttempt':now()}

AI_REQUESTS=threading.BoundedSemaphore(2)
LOCAL_HOSTS=('127.0.0.1:4174','localhost:4174')

class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.webmanifest':'application/manifest+json'}
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,format,*args):
        pass  # Do not log queries, filenames, prompts or credentials.
    # Each listening server declares its accepted Host values and scheme (Wi-Fi sharing uses HTTPS on another port).
    def allowed_hosts(self): return getattr(self.server,'allowed_hosts',LOCAL_HOSTS)
    def scheme(self): return getattr(self.server,'scheme','http')
    def from_this_computer(self): return self.client_address[0] in ('127.0.0.1','::1')
    def json_response(self,result,status=200):
        raw=json.dumps(result,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
    def do_HEAD(self):
        self.send_error(405)
    def do_POST(self):
        host=self.headers.get('Host','')
        if host not in self.allowed_hosts() or self.headers.get('Origin')!=self.scheme()+'://'+host or self.headers.get('X-DraftMate-Request')!='1':
            self.json_response({'error':'Use the DraftMate page on this origin.'},403);return
        if urlparse(self.path).path=='/api/ai/configure' and not self.from_this_computer():
            self.json_response({'error':'API keys can only be changed on the computer running DraftMate.'},403);return
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
            from ai_service import generate,transcribe,configure,command,courtroom
            from document_engine import parse_document
            handlers={'/api/ai/generate':generate,'/api/ai/configure':configure,'/api/ai/transcribe':transcribe,'/api/ai/command':command,'/api/ai/courtroom':courtroom,'/api/documents/parse':parse_document}
            fn=handlers.get(urlparse(self.path).path)
            if not fn:self.json_response({'error':'Unknown operation.'},404);return
            self.json_response(fn(data))
        except ValueError as exc:self.json_response({'error':str(exc)[:300]},400)
        except Exception:self.json_response({'error':'The task could not complete. Check file format, installed dependencies or provider availability.'},500)
        finally:AI_REQUESTS.release()
    def do_GET(self):
        path=urlparse(self.path).path
        # Local-only service, with fixed public sources and no arbitrary URL proxy.
        if self.headers.get('Host') not in self.allowed_hosts():
            self.send_error(403); return
        if path=='/api/ai/status':
            from ai_service import provider_status
            from document_engine import vector_status
            self.json_response({**provider_status(),'vectors':vector_status()});return
        if path in ('/api/legal/search','/api/legal/status'):
            args=parse_qs(urlparse(self.path).query)
            try:
                result=legal_status() if path.endswith('status') else legal_search(args.get('q',[''])[0][:1000],args.get('source',['all'])[0])
                data=json.dumps(result,ensure_ascii=False).encode()
                self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
            except Exception:
                self.send_error(503,'Legal index unavailable')
            return
        if path=='/draftmate-ca.crt':
            # Public half of the local CA (see lan.py), for installing on phones. Never the private key.
            try:
                from lan import ca_der
                raw=ca_der()
            except Exception:
                self.send_error(404,'Start DraftMate with Start-DraftMate-WiFi.cmd first'); return
            self.send_response(200); self.send_header('Content-Type','application/x-x509-ca-cert'); self.send_header('Content-Disposition','attachment; filename="DraftMate-local-CA.crt"'); self.end_headers(); self.wfile.write(raw); return
        if path=='/DraftMate.apk':
            apk=ROOT/'android'/'build'/'DraftMate.apk'
            if not apk.exists(): self.send_error(404,'Build the app first: android\\build.ps1'); return
            raw=apk.read_bytes()
            self.send_response(200); self.send_header('Content-Type','application/vnd.android.package-archive'); self.send_header('Content-Disposition','attachment; filename="DraftMate.apk"'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if path in ('/api/news','/api/public-cases'):
            refresh='refresh=1' in urlparse(self.path).query
            result=(news if path.endswith('news') else cases)(refresh)
            data=json.dumps(result,ensure_ascii=False).encode()
            self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data); return
        target=Path(self.translate_path(self.path)).resolve()
        if target != ROOT and (target.parent != ROOT or target.suffix.lower() not in ('.html','.js','.css','.png','.jpg','.svg','.ico','.webmanifest')):
            self.send_error(404); return
        super().do_GET()
if __name__=='__main__':
    class LocalServer(ThreadingHTTPServer):
        allow_reuse_address=False
    local=LocalServer(('127.0.0.1',4174),Handler)
    print('DraftMate AI: http://127.0.0.1:4174',flush=True)
    if '--lan' in sys.argv:
        # Wi-Fi sharing: HTTPS on 4175 so other devices get a secure context for microphone and storage APIs.
        from lan import lan_ips,ensure_cert
        ips=lan_ips()
        if not ips: print('No Wi-Fi/LAN address found; sharing not started.',flush=True)
        else:
            cert,key=ensure_cert(ips)
            shared=LocalServer(('0.0.0.0',4175),Handler)
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(cert,key)
            shared.socket=context.wrap_socket(shared.socket,server_side=True,do_handshake_on_connect=False)
            shared.allowed_hosts=tuple(f'{h}:4175' for h in [*ips,'localhost','127.0.0.1']);shared.scheme='https'
            threading.Thread(target=shared.serve_forever,daemon=True).start()
            for ip in ips: print(f'Same Wi-Fi devices: https://{ip}:4175',flush=True)
            print(f'Install as a phone app: open https://{ips[0]}:4175/install.html on the phone (accept the one-time warning first).',flush=True)
    local.serve_forever()


