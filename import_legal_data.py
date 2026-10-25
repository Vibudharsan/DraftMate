"""Run explicitly to import the user-selected public datasets, in resumable batches."""
import json,csv,io,zipfile,argparse,urllib.request,urllib.parse
from pathlib import Path
from legal_reference import connect,add_record,status
PARQUET_DIR=Path(__file__).resolve().parent/'data'/'datasets'/'indian-legal-documents'
ACT_TYPES="('Act','Legislation','Legislation (Act)','Bare Act','Legislation (Code)','Ordinance','Regulation','Regulations','Code')"
# Collections taken from the full KanoonGPT/indian-legal-documents dataset (35,845 documents).
GROUPS={'central':(f"document_jurisdiction='Central' AND document_type IN {ACT_TYPES}",'Central {type} incl. Constitution — dataset copy; verify on India Code'),
 'rules':("document_jurisdiction='Central' AND document_type='Rules'",'Central Rules — dataset copy; verify the official notification'),
 'state':(f"document_jurisdiction<>'Central' AND document_type IN {ACT_TYPES}",'{jurisdiction} {type} — dataset copy; verify the official state text')}

def get(url,limit=40_000_000):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'DraftMateDatasetImporter/1.0'}),timeout=60) as r:
  raw=r.read(limit+1)
  if len(raw)>limit:raise ValueError('Download exceeds importer size limit')
  return raw

def hf(source,limit,offset):
 dataset={'cases':'KanoonGPT/indian-case-laws','judgments':'opennyaiorg/InJudgements_dataset'}[source]
 with connect() as db:
  for start in range(offset,offset+limit,20):
   url='https://datasets-server.huggingface.co/rows?'+urllib.parse.urlencode(dict(dataset=dataset,config='default',split='train',offset=start,length=min(20,offset+limit-start)))
   data=json.loads(get(url));rows=data['rows'];added=0
   for entry in rows:
    # The viewer explicitly flags truncated cells; never index shortened text as full text.
    if entry.get('truncated_cells'):continue
    row=entry['row'];idx=entry['row_idx']
    if source=='cases': title=row.get('case_title') or row.get('party_caption') or 'Case metadata';body=row.get('indexable_text') or json.dumps(row,ensure_ascii=False);kind='Case metadata only — not full judgment';identity=row.get('id',idx)
    else: title=row.get('title') or row.get('case_title') or 'Judgment';body=row.get('text') or row.get('judgment') or '';kind='Judgment dataset text';identity=idx
    link='https://huggingface.co/datasets/'+dataset+'/viewer/default/train?row='+str(idx)
    added+=add_record(db,source,identity,title,body,link,kind)
   db.commit();print(source,start,'added',added,flush=True)
   if len(rows)<min(20,offset+limit-start):break

def mapping():
 raw=get('https://www.kaggle.com/api/v1/datasets/download/tanujsaxena/bns-ipc-mapping')
 with zipfile.ZipFile(io.BytesIO(raw)) as z,connect() as db:
  for f in z.infolist():
   if not f.filename.lower().endswith('.csv'):continue
   if f.file_size>10_000_000:raise ValueError('Mapping CSV too large')
   rows=csv.DictReader(io.StringIO(z.read(f).decode('utf-8-sig')))
   for i,row in enumerate(rows):
    text='\n'.join(str(k)+': '+str(v) for k,v in row.items())
    add_record(db,'mapping',i,'IPC–BNS mapping · row '+str(i+1),text,kind='Community comparison — verify official provisions')
  db.commit()
 print('mapping imported',flush=True)
def download_parquet():
 PARQUET_DIR.mkdir(parents=True,exist_ok=True)
 for i in range(8):
  target=PARQUET_DIR/f'train-{i:05d}.parquet'
  if target.exists() and target.stat().st_size>1_000_000:continue
  print('downloading',target.name,flush=True)
  target.write_bytes(get(f'https://huggingface.co/datasets/KanoonGPT/indian-legal-documents/resolve/main/data/{target.name}',limit=200_000_000))

def kanoon_full(groups):
 """Import whole collections from the dataset, one copy per law (the most English, then longest, version)."""
 import duckdb
 download_parquet()
 con=duckdb.connect()
 # Title key for spotting copies of the same law: drop brackets, "(Act) No. 22 of 2023", punctuation and a leading "the".
 con.execute(f"""CREATE VIEW d AS SELECT *,
  regexp_replace(trim(regexp_replace(regexp_replace(regexp_replace(lower(document_title),'\\(.*?\\)','','g'),'(act )?no\\.? ?\\d+ of \\d{{4}}','','g'),'[^a-z0-9]+',' ','g')),'^the ','') AS norm,
  length(regexp_replace(text,'[^\\x00-\\x7F]','','g'))::DOUBLE/greatest(length(text),1) AS ascii
  FROM read_parquet('{(PARQUET_DIR/'*.parquet').as_posix()}')""")
 with connect() as db:
  # The earlier 200-record sample used the 'laws' collection; these collections replace it.
  db.execute("DELETE FROM passages WHERE source='laws'");db.execute("DELETE FROM records WHERE source='laws'");db.commit()
  for name in groups:
   where,kind=GROUPS[name]
   # Re-running replaces the collection, so improved de-duplication takes effect.
   db.execute('DELETE FROM passages WHERE source=?',(name,));db.execute('DELETE FROM records WHERE source=?',(name,));db.commit()
   cursor=con.execute(f"""SELECT doc_id,document_title,document_type,document_jurisdiction,text FROM (
     SELECT *,row_number() OVER (PARTITION BY norm,document_jurisdiction ORDER BY ascii DESC,length(text) DESC) rn FROM d WHERE {where} AND length(text)>200) WHERE rn=1""")
   added=seen=0
   while True:
    rows=cursor.fetchmany(200)
    if not rows:break
    for doc_id,title,doc_type,jurisdiction,text in rows:
     seen+=1
     added+=add_record(db,name,doc_id,(title or 'Untitled').strip()[:300],text,'',kind.format(type=doc_type,jurisdiction=jurisdiction))
    db.commit();print(name,'processed',seen,'added',added,flush=True)
 print('kanoon import complete',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',choices=['kanoon-full','cases','judgments','mapping','all'],default='all');p.add_argument('--groups',default='central,rules,state',help='for kanoon-full: comma-separated '+','.join(GROUPS));p.add_argument('--limit',type=int,default=200);p.add_argument('--offset',type=int,default=0);a=p.parse_args()
 for s in (['kanoon-full','cases','mapping'] if a.source=='all' else [a.source]):
  try:
   if s=='mapping':mapping()
   elif s=='kanoon-full':kanoon_full([g for g in a.groups.split(',') if g in GROUPS])
   else:hf(s,max(1,min(a.limit,5000)),max(0,a.offset))
  except Exception as e:print(s,'IMPORT FAILED:',str(e),flush=True)
 print(json.dumps(status(),indent=2))
