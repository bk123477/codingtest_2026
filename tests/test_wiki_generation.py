import json
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from study_wiki.generate import parse_request, select_sources, call_model, save_note, DEFAULT_MODEL
from study_wiki.knowledge import concept_graph, exam_metadata, read_ai_notes
from study_wiki.build import read_records, build
from wiki import WikiRequestHandler


class GenerationTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for user in ('alice','bob'):
            folder=self.root/'records/2026/09/08'/user/'programmers-1'
            folder.mkdir(parents=True)
            meta=dict(type='problem',title='해시 연습',user=user,date='2026-09-08',status='solved',tags=['Python','Lv.1'],
                      data_structures=['해시'],algorithms=['문자열 처리'],platform='programmers',problem_id='1',solution='solution.py')
            (folder/'meta.json').write_text(json.dumps(meta))
            (folder/'README.md').write_text('# 문제\n\n## 풀이\n키를 셉니다.\n')
            (folder/'solution.py').write_text('def solution(s):\n    # 한글 주석\n    return {}\n')
        self.sources=select_sources(self.root,'해시')
        self.response={'title':'해시와 문자열','summary':'빈도 계산 접근을 비교합니다.','topics':['해시','문자열 처리'],
                       'body':'## 핵심 개념\n키로 조회합니다. [S1]\n## 기록에서 확인한 접근\n빈도를 기록합니다. [S2]',
                       'used_sources':['S1','S2']}

        keys=[source['key'] for source in self.sources]
        self.response['body']=self.response['body'].replace('[S1]','['+keys[0]+']').replace('[S2]','['+keys[1]+']')
        self.response['used_sources']=keys

    def test_request_validation(self):
        event={'issue':{'body':'<!-- study-wiki-note-request -->\n```json\n{"topic":"해시","user":"alice"}\n```'}}
        self.assertEqual(parse_request(event),('해시','alice'))
        for value in ({'issue':{'body':'run something'}},{'inputs':{'topic':'a','command':'bad'}},{'inputs':{'topic':[]}}):
            with self.assertRaises(ValueError):parse_request(value)

    def test_completed_only_and_minimum_sources(self):
        folder=self.root/'records/2026/09/08/bob/programmers-1'
        data=json.loads((folder/'meta.json').read_text());data['status']='draft'
        (folder/'meta.json').write_text(json.dumps(data))
        with self.assertRaises(ValueError):select_sources(self.root,'해시')

    def test_ai_provenance_links_and_staleness(self):
        folder=save_note(self.root,self.response,self.sources,DEFAULT_MODEL,'해시','','abc123')
        rows=read_records(self.root)
        notes=read_ai_notes(self.root,rows)
        self.assertEqual(notes[0]['status'],'unreviewed')
        self.assertFalse(notes[0]['stale'])
        self.assertEqual(notes[0]['contributors'],['alice','bob'])
        self.assertEqual(len(read_records(self.root)),2) # AI never re-enters the prompt corpus.
        build(self.root,self.root/'out')
        data=json.loads((self.root/'out/data.js').read_text().removeprefix('window.STUDY_WIKI = ').rstrip(';\n'))
        note=next(r for r in data['records'] if r['kind']=='ai_note')
        self.assertIn('#record=records',note['html'])
        self.assertIn('AI 자동 생성',note['html'])
        source=self.root/self.sources[0]['id']/'solution.py';source.write_text('# 수정\n')
        self.assertTrue(read_ai_notes(self.root,read_records(self.root))[0]['stale'])
        with self.assertRaises(ValueError):save_note(self.root,self.response,self.sources,DEFAULT_MODEL,'해시','','abc123')
        self.assertTrue(folder.exists())

    def test_refuse_fabricated_sources_or_missing_citations(self):
        result=dict(self.response,used_sources=['S1','S99'])
        with self.assertRaises(ValueError):save_note(self.root,result,self.sources,DEFAULT_MODEL,'해시','','abc')
        result=dict(self.response,body='근거 없는 설명')
        with self.assertRaises(ValueError):save_note(self.root,result,self.sources,DEFAULT_MODEL,'해시','','abc')
        self.assertFalse((self.root/'wiki_notes').exists())

    def test_free_only_no_retry(self):
        with patch('study_wiki.generate.urlopen') as request:
            with self.assertRaises(ValueError):call_model(self.sources,'해시','nvidia/nemotron-paid','test-key')
            request.assert_not_called()
        with patch('study_wiki.generate.urlopen',side_effect=HTTPError('url',429,'limit',{},None)) as request:
            with self.assertRaisesRegex(ValueError,'429'):call_model(self.sources,'해시',api_key='test-key')
            self.assertEqual(request.call_count,1)

    def test_valid_model_response_and_truncation(self):
        from io import BytesIO
        payload={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(self.response)}}]}
        with patch('study_wiki.generate.urlopen',return_value=BytesIO(json.dumps(payload).encode())) as request:
            generated=call_model(self.sources,'해시',api_key='test-key')
            self.assertEqual(generated,self.response)
            sent=json.loads(request.call_args.args[0].data)
            self.assertIn('taxonomy.json',sent['messages'][0]['content'])
            self.assertIn('data_structures',sent['messages'][0]['content'])
        payload['choices'][0]['finish_reason']='length'
        with patch('study_wiki.generate.urlopen',return_value=BytesIO(json.dumps(payload).encode())):
            with self.assertRaises(ValueError):call_model(self.sources,'해시',api_key='test-key')

    def test_new_ai_concept_registers_taxonomy_for_review_pr(self):
        (self.root/'study_wiki').mkdir()
        shutil.copy(Path(__file__).resolve().parents[1]/'study_wiki/taxonomy.json', self.root/'study_wiki/taxonomy.json')
        result=dict(self.response, topics=['세그먼트 트리'],
                    new_taxonomy={'data_structures':[{'name':'세그먼트 트리','aliases':['segment tree']}], 'algorithms':[]})
        folder=save_note(self.root,result,self.sources,DEFAULT_MODEL,'auto','','ref')
        taxonomy=json.loads((self.root/'study_wiki/taxonomy.json').read_text())
        self.assertEqual(taxonomy['data_structures']['세그먼트 트리'],['segment tree'])
        metadata=json.loads((folder/'meta.json').read_text())
        self.assertEqual(metadata['topics'],['세그먼트 트리'])
        self.assertIn('세그먼트 트리',metadata['taxonomy_updates']['data_structures'][0]['name'])

    def test_unknown_ai_topic_must_include_taxonomy_proposal(self):
        result=dict(self.response, topics=['새 알고리즘'])
        with self.assertRaisesRegex(ValueError,'new_taxonomy'):
            save_note(self.root,result,self.sources,DEFAULT_MODEL,'auto','','ref')

    def test_concepts_have_evidence_and_ignore_generic_tags(self):
        graph=concept_graph(read_records(self.root))
        self.assertEqual({n['name'] for n in graph['nodes']},{'해시','문자열 처리'})
        self.assertEqual(graph['edges'][0]['count'],2)

    def test_exam_validation_and_utf8_viewer(self):
        self.assertEqual(exam_metadata({'name':'공채','year':'2024'})['year'],'2024')
        for value in ({'year':'2024'},{'name':'a','url':'javascript:alert(1)'},{'name':'a','year':2024}):
            with self.assertRaises(ValueError):exam_metadata(value)
        out=self.root/'out';build(self.root,out)
        viewer=next(out.rglob('solution.py.html')).read_text()
        self.assertIn('charset="utf-8"',viewer)
        self.assertIn('    # 한글 주석',viewer)
        handler=WikiRequestHandler.__new__(WikiRequestHandler)
        self.assertEqual(handler.guess_type('solution.py'),'text/plain; charset=utf-8')
