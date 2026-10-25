import unittest,tempfile
from pathlib import Path
import legal_reference as lr
class RetrievalTests(unittest.TestCase):
 def setUp(self):
  self.old=lr.DB;self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent / 'data');lr.DB=Path(self.temp.name)/'test.sqlite'
 def tearDown(self):lr.DB=self.old;self.temp.cleanup()
 def test_dedup_sources_and_citations(self):
  with lr.connect() as db:
   self.assertEqual(lr.add_record(db,'central','1','Agriculture Act','agricultural marketing legislation','https://example.org'),1)
   self.assertEqual(lr.add_record(db,'central','1','Duplicate','agriculture'),0)
   lr.add_record(db,'mapping','1','Mapping','murder IPC 302 BNS 103')
  rows=lr.search('marketing','central')['items'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['url'],'https://example.org');self.assertEqual(rows[0]['part'],1)
  self.assertEqual(lr.search('murder','central')['items'],[])
  self.assertEqual(lr.search('zzzznonexistent')['items'],[])
 def test_abbreviations_expand(self):
  with lr.connect() as db:lr.add_record(db,'central','3','The Digital Personal Data Protection Act, 2023','consent of the data principal')
  self.assertEqual(lr.search('summarise the DPDP act')['items'][0]['title'],'The Digital Personal Data Protection Act, 2023')
 def test_long_text_and_untrusted_query(self):
  with lr.connect() as db:lr.add_record(db,'central','2','Long text','alpha '*1500+'lastword')
  self.assertIn('lastword',lr.search('lastword')['items'][0]['passage'])
  lr.search('" OR * ; DROP TABLE passages --')
  self.assertEqual(lr.status()['sources'][0]['records'],1)
if __name__=='__main__':unittest.main()

