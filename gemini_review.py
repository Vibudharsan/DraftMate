from ai_service import provider_request,config
from pathlib import Path
import json
c=config()
source=Path('ai_service.py').read_text(encoding='utf-8-sig')+Path('document_engine.py').read_text(encoding='utf-8-sig')
prompt='Review this local legal RAG prototype backend. Return at most 5 concrete correctness bugs or privacy issues, with concise fixes. Do not request secrets. Focus on retrieval isolation, file parsing, API errors. Code:\n'+source
body={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'maxOutputTokens':1200}}
r=provider_request('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent',{'x-goog-api-key':c['gemini'],'Content-Type':'application/json'},json.dumps(body).encode())
t='\n'.join(p.get('text','') for x in r.get('candidates',[]) for p in x.get('content',{}).get('parts',[]))
Path('data/gemini-review.txt').write_text(t,encoding='utf-8');print(t)

