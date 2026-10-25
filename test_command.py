import unittest,json
from unittest import mock
import ai_service

TARGETS=[{'id':'case.new','label':'Create a new case','fields':['name*','type (Civil/Criminal)']},{'id':'cases','label':'My cases list'}]
def reply(obj):return {'candidates':[{'content':{'parts':[{'text':json.dumps(obj)}]}}],'usageMetadata':{'promptTokenCount':900}}

class CommandTests(unittest.TestCase):
 def setUp(self):
  self.cfg=mock.patch.object(ai_service,'config',return_value={'gemini':'test-key','groq':'','model':ai_service.MODELS[0]});self.cfg.start()
 def tearDown(self):self.cfg.stop()

 def test_request_shape_and_result(self):
  with mock.patch.object(ai_service,'provider_request',return_value=reply({'action':'fill','target':'case.new','fields':[{'name':'name','value':'State v. Kumar'},{'name':'type','value':'Criminal'}],'missing':[],'message':'Creating case'})) as req:
   out=ai_service.command({'text':'new criminal case State v Kumar','targets':TARGETS,'today':'2026-10-25'})
  body=json.loads(req.call_args[0][2])
  self.assertEqual(body['generationConfig']['maxOutputTokens'],512)
  self.assertEqual(body['generationConfig']['responseMimeType'],'application/json')
  sent=json.loads(body['contents'][0]['parts'][0]['text'])
  self.assertNotIn('sources',sent)  # routing never sends documents
  self.assertEqual(sent['site_map'],TARGETS)
  self.assertEqual(out['action'],'fill');self.assertEqual(out['target'],'case.new')
  self.assertEqual(out['fields'],{'name':'State v. Kumar','type':'Criminal'})

 def test_unknown_target_becomes_clarify(self):
  with mock.patch.object(ai_service,'provider_request',return_value=reply({'action':'navigate','target':'admin.delete','fields':[],'missing':[],'message':'x'})):
   out=ai_service.command({'text':'delete everything','targets':TARGETS})
  self.assertEqual(out['action'],'clarify');self.assertEqual(out['target'],'')

 def test_answer_and_pending_passthrough(self):
  with mock.patch.object(ai_service,'provider_request',return_value=reply({'action':'answer','target':'','fields':[],'missing':[],'message':'Answering'})) as req:
   out=ai_service.command({'text':'what is the hearing date?','targets':TARGETS,'pending':{'target':'case.new','fields':{'type':'Civil'}}})
  self.assertEqual(out['target'],'answer')
  sent=json.loads(json.loads(req.call_args[0][2])['contents'][0]['parts'][0]['text'])
  self.assertEqual(sent['pending'],{'target':'case.new','fields':{'type':'Civil'}})

 def test_validation(self):
  for payload in [{'text':'','targets':TARGETS},{'text':'x'*2001,'targets':TARGETS},{'text':'hi','targets':[]},{'text':'hi','targets':[{'id':'a','label':'x'*13000}]}]:
   with self.assertRaises(ValueError):ai_service.command(payload)

 def test_unreadable_reply(self):
  with mock.patch.object(ai_service,'provider_request',return_value={'candidates':[{'content':{'parts':[{'text':'not json'}]}}]}):
   with self.assertRaises(ValueError):ai_service.command({'text':'hi','targets':TARGETS})

class CourtroomTests(unittest.TestCase):
 def setUp(self):
  self.cfg=mock.patch.object(ai_service,'config',return_value={'gemini':'test-key','groq':'','model':ai_service.MODELS[0]});self.cfg.start()
  import document_engine
  self.ret=mock.patch.object(document_engine,'retrieve',return_value=([{'citation':'R1','title':'Agreement','kind':'User document','passage':'Delivery by 15 March.'}],''));self.ret.start()
 def tearDown(self):self.ret.stop();self.cfg.stop()

 def test_turn(self):
  with mock.patch.object(ai_service,'provider_request',return_value=reply({'opponent':'The delivery date is disputed [R1].','judge':'Counsel, what proves receipt?','score':9,'feedback':'Cite the delivery note.'})) as req:
   out=ai_service.courtroom({'text':'The goods were delivered on time.','role':'Petitioner','history':[{'speaker':'judge','text':'You may begin.'},{'speaker':'hacker','text':'x'}]})
  body=json.loads(req.call_args[0][2]);sent=json.loads(body['contents'][0]['parts'][0]['text'])
  self.assertEqual(body['generationConfig']['maxOutputTokens'],700)
  self.assertEqual(sent['latest_submission'],'The goods were delivered on time.')
  self.assertEqual(sent['transcript'][1]['speaker'],'counsel')  # unknown speakers are normalised
  self.assertEqual(out['score'],5)  # clamped to 1-5
  self.assertEqual(out['judge'],'Counsel, what proves receipt?')

 def test_verdict_needs_submission(self):
  with self.assertRaises(ValueError):ai_service.courtroom({'mode':'verdict','history':[{'speaker':'judge','text':'Begin.'}]})
  with mock.patch.object(ai_service,'provider_request',return_value=reply({'ruling':'Respondent more persuasive.','strengths':['Clear'],'weaknesses':['No proof of receipt'],'prepare':['Delivery note']})):
   out=ai_service.courtroom({'mode':'verdict','history':[{'speaker':'counsel','text':'Delivered.'}]})
  self.assertEqual(out['mode'],'verdict');self.assertEqual(out['weaknesses'],['No proof of receipt'])

 def test_turn_validation(self):
  for text in ['','x'*3001]:
   with self.assertRaises(ValueError):ai_service.courtroom({'text':text})

def text_reply(text,grounding=None):
 cand={'content':{'parts':[{'text':text}]}}
 if grounding:cand['groundingMetadata']=grounding
 return {'candidates':[cand],'usageMetadata':{}}

class WebFallbackTests(unittest.TestCase):
 REF=[{'citation':'R1','title':'Private note','kind':'User document','source':'private','recordId':'private:x','part':1,'passage':'SECRET CLIENT FACT','url':''}]
 def setUp(self):
  self.cfg=mock.patch.object(ai_service,'config',return_value={'gemini':'k','groq':'','model':ai_service.MODELS[0]});self.cfg.start()
  import document_engine;self.de=document_engine
 def tearDown(self):self.cfg.stop()
 def run_generate(self,refs,replies):
  with mock.patch.object(self.de,'retrieve',return_value=(refs,'')),mock.patch.object(ai_service,'provider_request',side_effect=replies) as req:
   out=ai_service.generate({'prompt':'What did the court hold in Puttaswamy?','task':'answer'})
  return out,[json.loads(c[0][2]) for c in req.call_args_list]

 def test_local_answer_uses_no_web(self):
  out,bodies=self.run_generate(self.REF,[text_reply('Answer from sources [R1].')])
  self.assertFalse(out['web']);self.assertEqual(len(bodies),1);self.assertNotIn('tools',bodies[0])

 def test_falls_back_when_sources_lack_answer(self):
  grounding={'groundingChunks':[{'web':{'uri':'https://example.org/puttaswamy','title':'example.org'}}]}
  out,bodies=self.run_generate(self.REF,[text_reply('NEED_WEB_SEARCH'),text_reply('Privacy is a fundamental right (Puttaswamy, 2017).',grounding)])
  self.assertTrue(out['web']);self.assertEqual(len(bodies),2)
  self.assertEqual(bodies[1]['tools'],[{'google_search':{}}])
  self.assertNotIn('SECRET CLIENT FACT',json.dumps(bodies[1]))  # private passages never go to the web call
  self.assertEqual(out['sources'][0]['citation'],'W1');self.assertEqual(out['sources'][0]['url'],'https://example.org/puttaswamy')
  self.assertTrue(any('web' in w.lower() for w in out['warnings']))

 def test_nothing_retrieved_goes_straight_to_web(self):
  out,bodies=self.run_generate([],[text_reply('Web answer.',{'groundingChunks':[]})])
  self.assertTrue(out['web']);self.assertEqual(len(bodies),1);self.assertIn('tools',bodies[0])
  self.assertTrue(any('not report any web sources' in w for w in out['warnings']))

class WebUnavailableTests(WebFallbackTests):
 def test_web_failure_returns_explanation(self):
  out,bodies=self.run_generate(self.REF,[text_reply('NEED_WEB_SEARCH'),ValueError('Provider quota or rate limit reached.')])
  self.assertFalse(out['web']);self.assertIn('web search could not be used',out['answer'])
  self.assertTrue(any('billing' in w for w in out['warnings']))

if __name__=='__main__':unittest.main()
