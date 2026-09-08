import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study_wiki.pipeline import run_pipeline, chunks, Paused, INPUT_CHARS
from study_wiki.common import normalize
from study_wiki.generate import select_sources, parse_request


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.sources=[dict(key='S'+str(i),id='records/'+str(i),hash=str(i),text='내용'+str(i)) for i in range(1,32)]
        self.calls=[]

    def caller(self,items,topic,model,**kwargs):
        self.assertLessEqual(len(json.dumps(items,ensure_ascii=False,sort_keys=True)),INPUT_CHARS)
        self.calls.append(items)
        if kwargs:
            keys=list(dict.fromkeys(k for item in items for k in (item.get('used_sources') or [item['key']])))
            return {'summary':' '.join('분석 ['+k+']' for k in keys),'used_sources':keys}
        return {'done':True}

    def run_it(self, sources=None, **options):
        return run_pipeline(sources or self.sources,'auto','model',self.root/'cache',self.caller,lambda value:None,**options)

    def test_resume_and_unchanged_records_reused(self):
        with self.assertRaises(Paused):self.run_it(max_calls=3)
        self.assertEqual(len(self.calls),3)
        progress=json.loads((self.root/'cache/progress.json').read_text())
        self.assertEqual(progress['completed_chunks'],3)
        self.run_it(max_calls=100)
        self.assertEqual(len(self.calls),32) # 31 records + final, without repeated calls.
        self.run_it(max_calls=100)
        self.assertEqual(len(self.calls),32)
        updated=[dict(s) for s in self.sources]
        updated[0]['text']='새 내용';updated[0]['hash']='new'
        self.run_it(updated,max_calls=100)
        # Unchanged semantic summary can reuse the final synthesis.
        self.assertEqual(len(self.calls),33)

    def test_all_records_and_long_tail_are_preserved(self):
        source={**self.sources[0],'text':'가'*18000+'END-OF-RECORD'}
        parts=chunks([source])
        self.assertEqual(''.join(p['text'] for p in parts),source['text'])
        self.assertEqual(len(chunks(self.sources)),31)

    def test_rate_limit_saves_completed_work(self):
        def fail(items,*args,**kwargs):
            if items[0].get('key')=='S2':raise ValueError('HTTP 429')
            return self.caller(items,*args,**kwargs)
        with self.assertRaisesRegex(ValueError,'429'):
            run_pipeline(self.sources,'auto','model',self.root/'cache',fail,lambda _:None)
        self.run_it(max_calls=100)
        self.assertEqual(sum(items[0].get('key')=='S1' for items in self.calls),1)

    def test_hierarchical_reduction_keeps_inputs_bounded(self):
        def verbose(items,topic,model,**kwargs):
            result=self.caller(items,topic,model,**kwargs)
            if kwargs and 'key' in items[0]:result['summary']+='가'*4000
            return result
        run_pipeline(self.sources,'auto','model',self.root/'cache',verbose,lambda _:None,max_calls=100)
        self.assertGreater(len(self.calls),32)

    def test_no_24_record_limit_and_stable_keys(self):
        rows=[dict(id='records/'+str(i),files={'README.md':'가'*12000+'TAIL'},source_hash=str(i),
                   title='제목',user='alice',data_structures=[],algorithms=[],tags=[],search='') for i in range(35)]
        with patch('study_wiki.generate.read_records',return_value=rows):
            sources=select_sources(self.root)
        self.assertEqual(len(sources),35)
        self.assertTrue(all(s['text'].endswith('TAIL') for s in sources))
        with patch('study_wiki.generate.read_records',return_value=rows[1:]):
            subset=select_sources(self.root)
        self.assertEqual({s['id']:s['key'] for s in subset},{s['id']:s['key'] for s in sources if s['id']!='records/0'})

    def test_placeholder_values_are_not_concepts(self):
        self.assertEqual(normalize(['none','None','미분류','null','해시'],'tags'),['해시'])
        self.assertEqual(parse_request({'inputs':{'topic':'none'}}),('auto',''))
