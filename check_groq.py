import json,urllib.request,urllib.error
from pathlib import Path
k=json.loads(Path('data/provider-secrets.json').read_text())
try:
 req=urllib.request.Request('https://api.groq.com/openai/v1/models',headers={'Authorization':'Bearer '+k['groq'],'User-Agent':'DraftMate/1.0'})
 with urllib.request.urlopen(req,timeout=20) as r: print('Groq OK; Whisper models:',[x['id'] for x in json.load(r)['data'] if 'whisper' in x['id']])
except urllib.error.HTTPError as e:
 raw=e.read().decode(errors='replace')
 try:
  d=json.loads(raw);error=d.get('error',{});print('Groq HTTP',e.code,'type:',error.get('type'),'code:',error.get('code'),'message:',str(error.get('message','')).replace(k['groq'],'[redacted]')[:240])
 except:print('Groq HTTP',e.code,'non-JSON access response')
