"""Local lexical retrieval. No model training, provider calls or private query uploads."""
from pathlib import Path
import sqlite3, re, json, hashlib
from contextlib import contextmanager
DB=Path(__file__).resolve().parent/'data'/'legal-reference.sqlite'
KANOON='https://huggingface.co/datasets/KanoonGPT/indian-legal-documents'
SOURCES={'central':KANOON,'rules':KANOON,'state':KANOON,'cases':'https://huggingface.co/datasets/KanoonGPT/indian-case-laws','judgments':'https://huggingface.co/datasets/opennyaiorg/InJudgements_dataset','mapping':'https://www.kaggle.com/datasets/tanujsaxena/bns-ipc-mapping'}
@contextmanager
def connect():
 DB.parent.mkdir(exist_ok=True)
 db=sqlite3.connect(DB,timeout=30)
 db.execute('PRAGMA journal_mode=WAL')  # searches keep working while a long import writes
 db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(title,body,source UNINDEXED,record_id UNINDEXED,url UNINDEXED,part UNINDEXED,kind UNINDEXED)')
 db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY,source TEXT,title TEXT,parts INTEGER)')
 try:
  yield db
  db.commit()
 except Exception:
  db.rollback();raise
 finally:db.close()

def add_record(db,source,identity,title,body,url='',kind='text'):
 body=str(body or '').strip()
 if not body:return 0
 key=source+':'+str(identity)
 if db.execute('SELECT 1 FROM records WHERE id=?',(key,)).fetchone():return 0
 # Keep full supplied text and overlapping chunks; no silent truncation.
 chunks=[body[i:i+2400] for i in range(0,len(body),2100)]
 for i,chunk in enumerate(chunks):db.execute('INSERT INTO passages VALUES (?,?,?,?,?,?,?)',(title,chunk,source,key,url or SOURCES[source],i+1,kind))
 db.execute('INSERT INTO records VALUES (?,?,?,?)',(key,source,title,len(chunks)))
 return 1

def status():
 with connect() as db:
  counts={s:{'records':n,'passages':p} for s,n,p in db.execute('SELECT source,count(*),sum(parts) FROM records GROUP BY source')}
 return {'sources':[{'id':s,'url':u,**counts.get(s,{'records':0,'passages':0})} for s,u in SOURCES.items()], 'mode':'Local keyword retrieval over dataset copies; verify against official text'}

# Common abbreviations rarely appear in statute text, so expand them before searching.
ALIASES={'dpdp':'digital personal data protection','dpdpa':'digital personal data protection','bns':'bharatiya nyaya sanhita','bnss':'bharatiya nagarik suraksha sanhita',
 'bsa':'bharatiya sakshya adhiniyam','ipc':'indian penal code','crpc':'code criminal procedure','cpc':'code civil procedure','iea':'indian evidence','rti':'right information',
 'ibc':'insolvency bankruptcy code','pocso':'protection children sexual offences','posh':'sexual harassment women workplace','ndps':'narcotic drugs psychotropic substances',
 'gst':'goods services tax','cgst':'central goods services tax','rera':'real estate regulation development','pmla':'prevention money laundering','uapa':'unlawful activities prevention',
 'mact':'motor accidents claims tribunal','tpa':'transfer property','hma':'hindu marriage','sma':'special marriage',
 'fema':'foreign exchange management','sebi':'securities exchange board india','llp':'limited liability partnership','coi':'constitution india'}
STOPWORDS={'what','which','the','is','of','in','a','an','and','for','to','please','explain','about','summary','summarise','summarize','give','me','tell','under','does','do','how','can','i','my','act','law'}

def search(query,source='all'):
 words=re.findall(r'\w+',query.lower(),re.UNICODE)
 expanded=[]
 for w in words:expanded+= ALIASES[w].split() if w in ALIASES else [w]
 tokens=list(dict.fromkeys(expanded))[:24]
 tokens=[t for t in tokens if t not in STOPWORDS] or [t for t in tokens if t in ('act','law')]
 if not tokens:return {'items':[],'message':'Enter a legal topic, title or section number.'}
 quoted=['"'+t.replace('"','""')+'"' for t in tokens]
 clause=' AND source=?' if source in SOURCES else ''
 sql='SELECT title,body,source,record_id,url,part,kind,bm25(passages,4,1) FROM passages WHERE passages MATCH ?'+clause+' ORDER BY bm25(passages,4,1) LIMIT 80'
 with connect() as db:
  # Passages containing every term first; fill up with any-term matches when there are too few.
  rows=db.execute(sql,[' AND '.join(quoted)]+([source] if source in SOURCES else [])).fetchall() if len(quoted)>1 else []
  if len(rows)<8:
   have={(r[3],r[5]) for r in rows}
   rows+=[r for r in db.execute(sql,[' OR '.join(quoted)]+([source] if source in SOURCES else [])).fetchall() if (r[3],r[5]) not in have]
 # Re-rank: a law whose title names the query terms (e.g. "BNSS" -> Bharatiya Nagarik Suraksha Sanhita) beats passages that merely
 # mention them, and central Acts get a small preference. bm25 is negative; lower is better.
 def score(r):
  title=set(re.findall(r'\w+',r[0].lower()))
  return r[7]-3*sum(t in title for t in tokens)-(2 if r[2]=='central' else 0)
 rows=sorted(rows,key=score)
 items=[];seen={}
 for title,body,s,r,u,p,k,score in rows:
  if seen.get(r,0)>=2:continue
  seen[r]=seen.get(r,0)+1
  items.append({'citation':f'R{len(items)+1}','title':title,'passage':body,'source':s,'recordId':r,'url':u,'part':p,'kind':k})
  if len(items)==8:break
 return {'items':items,'message':'Retrieved excerpts, not an AI legal opinion. Dataset copies may be incomplete or outdated; verify against the official text and applicable date.','query':query}

