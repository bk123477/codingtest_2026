import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import enrich
import study
from study_wiki.build import build, read_records
from study_wiki.render import markdown


class WikiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.out = self.root / '.study/wiki'

    def record(self, user='alice', kind='problem', status=None, pid='42747', **extra):
        folder = self.root / 'records/2026/09/08' / user / ('programmers-' + pid if kind == 'problem' else 'note-01')
        folder.mkdir(parents=True)
        data = dict(type=kind, title='해시 학습', date='2026-09-08', user=user,
                    status=status or ('solved' if kind == 'problem' else 'completed'), tags=[])
        if kind == 'problem':
            data.update(platform='programmers', problem_id=pid, url='https://school.programmers.co.kr/learn/courses/30/lessons/'+pid,
                        language='python', solution='solution.py')
            (folder / 'solution.py').write_text('def solution(a):\n    return "<script>"\n', encoding='utf-8')
            body = '# 해시 학습\n\n## 문제\n요약\n\n## 풀이\n키를 조회합니다.\n\n## 확인한 예제 / 경계 조건\n예상 결과: 1\n'
        else:
            data.update(note_id='01', references=[])
            body = '# 노트\n\n## 학습 주제 / 목표\n해시\n\n## 정리 내용\n자료\n\n## 배운 점 / 확인한 내용\n확인\n'
        data.update(extra)
        (folder / 'README.md').write_text(body, encoding='utf-8')
        (folder / 'meta.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return folder

    def test_legacy_terms_are_core_facets_without_source_changes(self):
        folder = self.record(data_structures=['리스트'], algorithms=['순회'],
                             tags=['완전탐색', '완전 탐색', '처음 보는 표현'])
        before = (folder / 'meta.json').read_bytes()
        row = read_records(self.root)[0]
        self.assertEqual(row['data_structures'], ['배열'])
        self.assertEqual(row['algorithms'], ['구현', '완전 탐색'])
        self.assertEqual(row['tags'], [])
        self.assertEqual(row['keywords'], ['처음 보는 표현'])
        self.assertIn('처음 보는 표현', row['search'])
        self.assertIn('순회', row['search'])
        self.assertEqual((folder / 'meta.json').read_bytes(), before)

    def test_completed_shared_personal_notes_and_rebuild(self):
        a = self.record(data_structures=['dict', '해시'])
        b = self.record('bob', data_structures=['해시'])
        self.record('charlie', status='draft')
        note = self.record('bob', kind='note', tags=['해시'], source_file='notes.md')
        (note / 'notes.md').write_text('## 내부 구조\n버킷과 충돌\n', encoding='utf-8')
        original = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = build(self.root, self.out)
        self.assertEqual((result['records'], result['problems'], result['members']), (3,1,2))
        self.assertEqual(read_records(self.root)[0]['data_structures'], ['해시'])
        self.assertIn('버킷과 충돌', (self.out/'data.js').read_text())
        for path, body in original.items(): self.assertEqual(path.read_bytes(), body)
        snapshot = {str(p.relative_to(self.out)): p.read_bytes() for p in self.out.rglob('*') if p.is_file()}
        build(self.root, self.out)
        self.assertEqual(snapshot, {str(p.relative_to(self.out)): p.read_bytes() for p in self.out.rglob('*') if p.is_file()})
        build(self.root, self.out, user='alice')
        self.assertFalse((self.out / 'sources' / b.relative_to(self.root)).exists())
        self.assertNotIn('bob', (self.out/'data.js').read_text())
        self.assertEqual(build(self.root, self.out, include_drafts=True)['records'],4)
        self.assertTrue((self.out/'sources'/a.relative_to(self.root)/'solution.py').exists())

    def test_markdown_links_and_source_lineage(self):
        folder = self.record()
        readme = folder/'README.md'
        readme.write_text(readme.read_text()+'\n[코드](solution.py)\n[노트](../note-01/README.md)\n')
        self.record(kind='note')
        build(self.root, self.out, repo_url='https://github.com/a/repo', ref='abc123')
        payload = (self.out/'data.js').read_text()
        self.assertIn('https://github.com/a/repo/blob/abc123/',payload)
        self.assertIn('#record=records%2F',payload)
        self.assertIn('&amp;tab=code',payload)
        manifest = json.loads((self.out/'manifest.json').read_text())
        old = manifest['sources'][folder.relative_to(self.root).as_posix()]
        readme.write_text(readme.read_text()+'\n새 설명\n')
        build(self.root,self.out)
        self.assertNotEqual(old,json.loads((self.out/'manifest.json').read_text())['sources'][folder.relative_to(self.root).as_posix()])
        for page in (self.out/'markdown').rglob('*.md'):
            import re
            from urllib.parse import unquote
            for target in re.findall(r'\]\(([^)]+)\)',page.read_text()):
                self.assertTrue((page.parent/unquote(target)).resolve().exists(),target)

    def test_unclassified_and_empty_repository(self):
        self.assertEqual(build(self.root,self.out)['records'],0)
        self.record()
        self.assertEqual(build(self.root,self.out)['unclassified'],1)
        self.assertIn('미분류',(self.out/'markdown/README.md').read_text())

    def test_untrusted_markdown_is_inert_and_code_preserved(self):
        text = '<script>alert(1)</script>\n\n[bad](javascript:alert)\n\n```python\n<!-- code -->\nprint("<img>")\n```\n\n| a | b |\n| --- | --- |\n| **x** | `y` |\n'
        rendered=markdown(text)
        self.assertNotIn('<script>',rendered)
        self.assertNotIn('href="javascript:',rendered)
        self.assertIn('&lt;!-- code --&gt;',rendered)
        self.assertIn('<table>',rendered)
        self.record(title='</script><script>bad</script>')
        build(self.root,self.out)
        self.assertNotIn('</script>',(self.out/'data.js').read_text())

    def test_refuses_symlinks_escape_and_unowned_output(self):
        folder=self.record()
        code=folder/'solution.py'
        code.unlink()
        outside=self.root/'secret';outside.write_text('not a record')
        code.symlink_to(outside)
        with self.assertRaises(ValueError): build(self.root,self.out)
        code.unlink();code.write_text('valid')
        for dest in (self.root, self.root.parent, self.root/'records/out'):
            with self.assertRaises(ValueError):build(self.root,dest)
        self.out.mkdir(parents=True);(self.out/'keep').write_text('keep')
        with self.assertRaises(ValueError):build(self.root,self.out)
        self.assertEqual((self.out/'keep').read_text(),'keep')
        meta=json.loads((folder/'meta.json').read_text());meta['solution']='../../secret'
        (folder/'meta.json').write_text(json.dumps(meta))
        with self.assertRaises(ValueError):read_records(self.root)

    def test_invalid_input_preserves_previous_build(self):
        folder=self.record();build(self.root,self.out)
        before=(self.out/'data.js').read_bytes()
        (folder/'meta.json').write_text('{invalid')
        with self.assertRaises(ValueError):build(self.root,self.out)
        self.assertEqual(before,(self.out/'data.js').read_bytes())

    def test_enrich_preserves_status_existing_fields_and_code(self):
        folder=self.record(status='draft', data_structures=['배열'], solve_method='hint',minutes=20)
        (self.root/'members').mkdir()
        (self.root/'members/alice.json').write_text(json.dumps(dict(user='alice',joined='2026-09-08',goals=[{'from':'2026-09-08','daily_goal':5}])))
        original=(folder/'solution.py').read_bytes()
        with patch.object(study,'ROOT',self.root):
            changed,kept=enrich.enrich(folder,dict(data_structures=['dict'],algorithms=['DFS'],tags=['graph']))
            self.assertIn('data_structures',kept)
            data=json.loads((folder/'meta.json').read_text())
            self.assertEqual((data['status'],data['minutes'],data['solve_method']),('draft',20,'hint'))
            self.assertEqual(data['data_structures'],['배열'])
            self.assertEqual(data['algorithms'],['깊이 우선 탐색'])
            self.assertIn('- 알고리즘: 깊이 우선 탐색',(folder/'README.md').read_text())
            enrich.enrich(folder,dict(data_structures=['dict']),replace=True)
            self.assertEqual(json.loads((folder/'meta.json').read_text())['data_structures'],['해시'])
            with self.assertRaises(ValueError):enrich.enrich(folder,dict(status='solved'))
        self.assertEqual(original,(folder/'solution.py').read_bytes())

    def test_local_server_starts_without_reverse_dns(self):
        from wiki import LocalWikiServer
        from http.server import SimpleHTTPRequestHandler
        with patch('socket.getfqdn', side_effect=AssertionError('no DNS needed')):
            with LocalWikiServer(('127.0.0.1', 0), SimpleHTTPRequestHandler) as server:
                self.assertEqual(server.server_name, 'localhost')
                self.assertGreater(server.server_port, 0)

    def test_enrich_note_tags_without_completion(self):
        folder=self.record(kind='note',status='draft')
        (self.root/'members').mkdir()
        (self.root/'members/alice.json').write_text(json.dumps(dict(user='alice',joined='2026-09-08',goals=[{'from':'2026-09-08','daily_goal':5}])))
        readme=(folder/'README.md').read_bytes()
        with patch.object(study,'ROOT',self.root):
            enrich.enrich(folder,dict(tags=['Git']))
        self.assertEqual(json.loads((folder/'meta.json').read_text())['status'],'draft')
        self.assertEqual(readme,(folder/'README.md').read_bytes())

    def test_enrich_can_register_llm_discovered_core_terms(self):
        folder=self.record(status='draft')
        (self.root/'members').mkdir()
        (self.root/'members/alice.json').write_text(json.dumps(dict(user='alice',joined='2026-09-08',goals=[{'from':'2026-09-08','daily_goal':5}])))
        (self.root/'study_wiki').mkdir()
        shutil.copy(Path(study.__file__).parent/'study_wiki/taxonomy.json', self.root/'study_wiki/taxonomy.json')
        with patch.object(study,'ROOT',self.root):
            enrich.enrich(folder, dict(data_structures=['세그먼트 트리'], algorithms=['파라메트릭 서치']), add_taxonomy=True)
        taxonomy=json.loads((self.root/'study_wiki/taxonomy.json').read_text())
        self.assertIn('세그먼트 트리', taxonomy['data_structures'])
        self.assertIn('파라메트릭 서치', taxonomy['algorithms'])
        data=json.loads((folder/'meta.json').read_text())
        self.assertEqual(data['data_structures'],['세그먼트 트리'])
        self.assertEqual(data['algorithms'],['파라메트릭 서치'])


if __name__=='__main__':unittest.main()
