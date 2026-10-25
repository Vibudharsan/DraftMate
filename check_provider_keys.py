import json,urllib.request,urllib.error
from pathlib import Path
keys=json.loads((Path(__file__).parent/'data/provider-secrets.json').read_text())
for name,url,header in [('gemini','https://generativelanguage.googleapis.com/v1beta/models',{'x-goog-api-key':keys['gemini']}),('groq','https://api.groq.com/openai/v1/models',{'Authorization':'Bearer '+keys['groq']})]:
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers=header),timeout=20) as r:d=json.load(r)
  models=[x.get('name',x.get('id','')) for x in d.get('models',d.get('data',[]))]
  print(name,'OK', [m for m in models if 'flash' in m or 'whisper' in m][:15])
 except urllib.error.HTTPError as e:
  print(name,'HTTP',e.code)
 except Exception as e:print(name,type(e).__name__)
