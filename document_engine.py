"""On-device Chroma vectors and MarkItDown document extraction."""
from pathlib import Path
import os,threading,hashlib,json,base64,re,zipfile,io,tempfile,subprocess,sys
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
os.environ.setdefault('ANONYMIZED_TELEMETRY','False')
os.environ.setdefault('HF_HOME',str(DATA/'models'/'huggingface'))
os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
_lock=threading.RLock();_client=None;_embedding=None

def vector_client():
 global _client,_embedding
 with _lock:
  if _client is None:
   import chromadb
   from chromadb.config import Settings
   from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
   ONNXMiniLM_L6_V2.DOWNLOAD_PATH=DATA/'models'/'all-MiniLM-L6-v2'
   _embedding=ONNXMiniLM_L6_V2(preferred_providers=['CPUExecutionProvider'])
   _client=chromadb.PersistentClient(path=str(DATA/'chroma'),settings=Settings(anonymized_telemetry=False))
  return _client

def collection(name):return vector_client().get_or_create_collection(name,embedding_function=_embedding,metadata={'hnsw:space':'cosine'})

def vector_status():
 try:
  with _lock:return {'publicPassages':collection('legal_public_v1').count(),'privatePassages':collection('case_documents_v1').count(),'embedding':'Local MiniLM (English-oriented)'}
 except Exception:return {'error':'Vector store not ready. Check dependencies and the local embedding model.'}

# Collections given semantic (vector) search. Rules and state Acts stay keyword-only to keep indexing time reasonable.
VECTOR_SOURCES=('central','cases','mapping')

def index_public(sources=VECTOR_SOURCES):
 from legal_reference import connect
 with _lock:
  c=collection('legal_public_v1')
  c.delete(where={'source':'laws'})  # vectors from the replaced 200-record sample
 with connect() as db:
  marks=','.join('?'*len(sources))
  total=db.execute(f'SELECT count(*) FROM passages WHERE source IN ({marks})',sources).fetchone()[0]
  cursor=db.execute(f'SELECT title,body,source,record_id,url,part,kind FROM passages WHERE source IN ({marks})',sources);done=0
  while True:
   batch=cursor.fetchmany(64)
   if not batch:break
   ids=[hashlib.sha256((r[3]+':'+str(r[5])).encode()).hexdigest() for r in batch]
   with _lock:
    existing=set(c.get(ids=ids,include=[])['ids']);todo=[(r,i) for r,i in zip(batch,ids) if i not in existing]
    if todo:c.upsert(ids=[i for r,i in todo],documents=[r[1] for r,i in todo],metadatas=[{'title':r[0],'source':r[2],'recordId':r[3],'url':r[4],'part':int(r[5]),'kind':r[6]} for r,i in todo])
   done+=len(batch)
   if done%1280<64 or done==total:print('Indexed',done,'/',total,flush=True)
 return vector_status()

def private_ids(values):return [str(x) for x in values if re.fullmatch(r'[a-fA-F0-9-]{36}',str(x))][:30]

def retrieve(query,document_ids=None,source='all'):
 from legal_reference import search
 results=search(query,source)['items'][:4];warning=''
 try:
  with _lock:
   pc=collection('case_documents_v1');ids=private_ids(document_ids or [])
   if ids and pc.count():
    out=pc.query(query_texts=[query],where={'documentId':{'$in':ids}},n_results=4,include=['documents','metadatas','distances'])
    private=[dict(m,passage=t,distance=d) for m,t,d in zip(out['metadatas'][0],out['documents'][0],out['distances'][0]) if d<1.2]
    results=private+results
   c=collection('legal_public_v1')
   if c.count():
    kw={'where':{'source':source}} if source!='all' else {}
    out=c.query(query_texts=[query],n_results=4,include=['documents','metadatas','distances'],**kw)
    results += [dict(m,passage=t,distance=d) for m,t,d in zip(out['metadatas'][0],out['documents'][0],out['distances'][0]) if d<1.0]
 except Exception:warning='Vector retrieval unavailable; keyword matches only.'
 unique=[];seen=set()
 for r in results:
  key=(r['recordId'],str(r['part']))
  if key in seen:continue
  seen.add(key);r['citation']='R'+str(len(unique)+1);unique.append(r)
  if len(unique)==8:break
 return unique,warning

def parse_document(payload):
 name=Path(str(payload.get('name','document'))).name[:200];ext=Path(name).suffix.lower()
 if ext not in ('.pdf','.docx','.txt','.md'):raise ValueError('Use PDF, DOCX, TXT or Markdown.')
 ids=private_ids([payload.get('id','')])
 if not ids:raise ValueError('Document ID is invalid.')
 identity=ids[0]
 try:raw=base64.b64decode(payload.get('content',''),validate=True)
 except Exception:raise ValueError('Invalid document encoding.')
 if not raw or len(raw)>20*1024*1024:raise ValueError('Use a non-empty file up to 20 MB.')
 if ext=='.docx':
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   if len(z.infolist())>3000 or sum(i.file_size for i in z.infolist())>80*1024*1024:raise ValueError('Expanded document is too large.')
 (DATA/'tmp').mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(dir=DATA/'tmp') as tmp:
  path=Path(tmp)/('input'+ext);path.write_bytes(raw)
  if ext in ('.txt','.md'):text=raw.decode('utf-8-sig',errors='replace')
  else:
   try:completed=subprocess.run([sys.executable,str(ROOT/'parse_worker.py'),str(path)],timeout=60,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   except subprocess.TimeoutExpired:raise ValueError('Document parsing exceeded 60 seconds. Split or simplify the file.')
   if completed.returncode:raise ValueError('Cannot parse this file. Check for encryption, damage, or excessive size.')
   text=path.with_suffix('.parsed.txt').read_text(encoding='utf-8')
 if not text.strip():raise ValueError('No text extracted. Scanned PDFs need OCR; OCR is not configured.')
 if len(text)>1_000_000:raise ValueError('Extracted text exceeds one million characters. Split this document first.')
 chunks=[text[i:i+1800] for i in range(0,len(text),1500)]
 with _lock:
  c=collection('case_documents_v1');prefix='private:'+identity
  # Parse and embed the replacement before removing the previous index.
  vector_client();embeddings=_embedding(chunks)
  c.delete(where={'documentId':identity})
  for start in range(0,len(chunks),64):
   parts=chunks[start:start+64]
   c.upsert(ids=[prefix+':'+str(start+i+1) for i in range(len(parts))],documents=parts,embeddings=embeddings[start:start+64],metadatas=[{'documentId':identity,'title':name,'recordId':prefix,'source':'private','url':'','part':start+i+1,'kind':'User document — extracted text, not verified legal authority'} for i in range(len(parts))])
 return {'text':text,'passages':len(chunks),'parser':'MarkItDown' if ext in ('.pdf','.docx') else 'UTF-8 text','documentId':identity}
if __name__=='__main__':print(json.dumps(index_public(tuple(sys.argv[1].split(',')) if len(sys.argv)>1 else VECTOR_SOURCES)))

