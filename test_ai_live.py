from pathlib import Path
import base64,uuid,json
from document_engine import parse_document,retrieve,collection
from ai_service import generate,transcribe
ids=[]
try:
 for filename in ['parser-test.docx','parser-test.pdf']:
  identity=str(uuid.uuid4());ids.append(identity)
  result=parse_document({'id':identity,'name':filename,'content':base64.b64encode((Path('data/tmp')/filename).read_bytes()).decode()})
  assert 'November 2026' in result['text'];print(filename,'parsed:',result['parser'],'passages:',result['passages'])
 refs,_=retrieve('When is the demonstration case hearing?',ids)
 assert any(r['source']=='private' and '17 November' in r['passage'] for r in refs)
 other,_=retrieve('When is the demonstration case hearing?',[])
 assert not any(r['source']=='private' for r in other);print('Document isolation passed.')
 result=generate({'task':'answer','prompt':'What is the hearing date in the demonstration case document? Answer briefly with its citation.','documentIds':[ids[0]],'language':'en-IN'})
 print('Gemini model:',result['model'],'answer:',result['answer'][:700]);assert '17' in result['answer'] and '[R' in result['answer']
 audio=base64.b64encode(Path('data/tmp/voice-test.wav').read_bytes()).decode()
 result=transcribe({'audio':audio,'mime':'audio/wav','language':'en-IN'})
 print('Groq transcription:',result['text']);assert 'case' in result['text'].lower()
finally:
 for identity in ids:collection('case_documents_v1').delete(where={'documentId':identity})
