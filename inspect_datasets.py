import urllib.request,json
urls=['https://datasets-server.huggingface.co/rows?dataset=KanoonGPT/indian-legal-documents&config=default&split=train&offset=0&length=1','https://datasets-server.huggingface.co/rows?dataset=KanoonGPT/indian-case-laws&config=default&split=train&offset=0&length=1','https://www.kaggle.com/api/v1/datasets/list/tanujsaxena/bns-ipc-mapping']
for u in urls:
 try:
  with urllib.request.urlopen(u,timeout=25) as r: print(u, r.read(2000).decode()[:2000])
 except Exception as e: print(str(e))
