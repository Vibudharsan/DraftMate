from ai_service import config
import urllib.request,urllib.error,json
k=config()['gemini']
for model in ['gemini-3.1-flash-lite','gemini-3.5-flash-lite']:
 try:
  body={'contents':[{'parts':[{'text':'Reply only: READY'}]}],'generationConfig':{'maxOutputTokens':512}}
  req=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',data=json.dumps(body).encode(),headers={'x-goog-api-key':k,'Content-Type':'application/json','User-Agent':'DraftMate/1.0'})
  with urllib.request.urlopen(req,timeout=25) as r:d=json.load(r)
  print(model,'OK',d.get('candidates',[{}])[0].get('content',{}));break
 except urllib.error.HTTPError as e:
  d=e.read().decode();print(model,e.code,d.replace(k,'[redacted]')[:800])

 except Exception as e:print(model,type(e).__name__)

