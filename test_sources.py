import unittest
from server import parse_cases, parse_feed, category

class SourceTests(unittest.TestCase):
    def test_transcripts_group_hearings_by_case(self):
        rows=''.join(f'<tr><td>12 / 2024 C.A. 1/2024</td><td>A VERSUS B</td><td>{day}-Feb-2024</td><td><a href="/view-pdf/?day={day}">Read Transcript</a></td></tr>' for day in ['01','02'])
        items=parse_cases(('<table>'+rows+'</table>').encode())
        self.assertEqual(len(items),1)
        self.assertEqual(len(items[0]['hearings']),2)
        self.assertEqual(items[0]['hearings'][0]['date'],'2024-02-02')
    def test_feed_retains_provenance_and_missing_date(self):
        xml=b'<rss><channel><item><title>Court hears petition</title><link>https://example.com/story</link></item><item><title>Unsafe link</title><link>javascript:alert(1)</link></item></channel></rss>'
        result=parse_feed('Test publisher',xml)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['source'],'Test publisher')
        self.assertIsNone(result[0]['publishedAt'])
        self.assertEqual(result[0]['category'],'Courts & law')
    def test_no_entity_expansion(self):
        with self.assertRaises(ValueError): parse_feed('Test',b'<!DOCTYPE rss><rss/>')
    def test_general_fallback(self):
        self.assertEqual(category('A local celebration'),'General')

if __name__=='__main__': unittest.main()
