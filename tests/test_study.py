import contextlib
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import study

SOURCE = Path(study.__file__).parent
URL = 'https://school.programmers.co.kr/learn/courses/30/lessons/42747'
DAY = '2026-09-05'


class StudyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.root_patch = patch.object(study, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        shutil.copy(SOURCE / 'study.json', self.root)
        shutil.copy(SOURCE / '.gitignore', self.root)
        shutil.copytree(SOURCE / 'templates', self.root / 'templates')
        self.run_git('init', '-b', 'main')
        self.run_git('config', 'user.name', 'Test User')
        self.run_git('config', 'user.email', 'test@example.invalid')
        self.run_git('add', '.')
        self.run_git('commit', '-m', 'initial')
        self.base = self.run_git('rev-parse', 'HEAD')
        self.remote = Path(self.temp.name) / 'remote.git'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        self.run_git('remote', 'add', 'origin', str(self.remote))
        self.run_git('push', '-u', 'origin', 'main')
        self.cli('init', 'alice', '--goal', '5')

    def run_git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def cli(self, *args):
        parsed = study.parser().parse_args(list(args))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            parsed.func(parsed)
        return output.getvalue()

    def create(self, url=URL, day=DAY, **options):
        args = ['new', url, '--title', '테스트 문제', '--date', day]
        for key, value in options.items():
            args += ['--' + key, value]
        self.cli(*args)
        platform, pid, _ = study.identify(url)
        return study.daily_path(study.local()['user'], day) / f'{platform}-{pid}'

    def solve(self, url=URL, day=DAY):
        folder = self.create(url, day)
        notes = folder / 'README.md'
        notes.write_text(notes.read_text(encoding='utf-8').replace('TODO: 무엇을 구하는 문제인가요?', '배열의 합을 구합니다.')
                         .replace('TODO: 어떻게 풀었나요?', '배열을 순회하며 더합니다.')
                         .replace('TODO: 직접 확인한 입력과 예상 결과를 하나 이상 적어주세요.', '[1, 2] → 3, [] → 0'), encoding='utf-8')
        (folder / 'solution.py').write_text('def solution(values):\n    return sum(values)\n', encoding='utf-8')
        self.cli('done', url, '--date', day, '--minutes', '20')
        return folder

    def finish_note(self, folder, day=DAY):
        path = folder / 'README.md'
        path.write_text(path.read_text(encoding='utf-8')
                        .replace('TODO: 오늘의 학습 주제와 목표를 작성하세요.', 'Git 브랜치가 가리키는 대상을 이해한다.')
                        .replace('TODO: 오늘 정리한 내용을 작성하세요.', '브랜치는 커밋을 가리키며, 새 커밋에 따라 이동한다.')
                        .replace('TODO: 배운 점이나 직접 확인한 내용을 작성하세요.', '임시 저장소에서 브랜치를 전환하고 파일 변화를 확인했다.'), encoding='utf-8')
        self.cli('done', folder.name, '--date', day, '--minutes', '30')

    def test_complete_daily_lifecycle_and_partial_goal(self):
        self.cli('start', '--date', DAY)
        folder = self.solve()
        output = self.cli('prepare', '--date', DAY)
        self.assertIn('목표 미달', output)
        self.assertIn('gh pr create', output)
        self.assertIn('1 / 5', (self.root / '.study/PR.md').read_text(encoding='utf-8'))
        self.run_git('add', 'records', 'members')
        self.run_git('commit', '-m', 'solve')
        self.cli('check', '--branch', 'study/alice/' + DAY, '--base', self.base)
        self.assertEqual(study.read_json(folder / 'meta.json')['minutes'], 20)
        self.assertIn('🔸 1/5', study.dashboard(DAY))

    def test_import_duplicate_and_canonical_url(self):
        source = self.root / 'original.py'
        source.write_text('print(42)\n')
        folder = self.create(URL + '/?utm_source=test#code', source=str(source))
        self.assertEqual((folder / 'solution.py').read_text(), 'print(42)\n')
        self.assertEqual(study.read_json(folder / 'meta.json')['url'], URL)
        with self.assertRaisesRegex(ValueError, '이미 존재'):
            self.create()
        self.assertEqual((folder / 'solution.py').read_text(), 'print(42)\n')

    def test_supported_platforms_and_bad_urls(self):
        self.assertEqual(study.identify('http://acmicpc.net/problem/1000')[0:2], ('baekjoon', '1000'))
        self.assertEqual(study.identify('https://leetcode.com/problems/two-sum/description/?x=1')[1], 'two-sum')
        for url in ('file:///tmp/1', 'https://evil.com/problem/1000', 'https://acmicpc.net.evil.com/problem/1', 'https://x:y@acmicpc.net/problem/1'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                study.identify(url)

    def test_draft_cannot_be_completed_or_submitted(self):
        self.cli('start', '--date', DAY)
        folder = self.create()
        with self.assertRaisesRegex(ValueError, '항목을 작성'):
            self.cli('done', URL, '--date', DAY)
        self.assertEqual(study.read_json(folder / 'meta.json')['status'], 'draft')
        with self.assertRaisesRegex(ValueError, 'draft'):
            self.cli('prepare', '--date', DAY)
        self.run_git('add', 'records', 'members')
        self.run_git('commit', '-m', 'draft')
        with self.assertRaisesRegex(ValueError, 'draft'):
            study.check_all('study/alice/' + DAY, self.base)

    def test_identity_dates_and_goals(self):
        for name in ('../escape', 'a/b', '-name', 'a b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.cli('init', '--', name)
        for day in ('2026-02-30', '2026-9-5', '../../'):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.create(day=day)
        for goal in ('0', '-1'):
            with self.subTest(goal=goal), self.assertRaises(ValueError):
                self.cli('init', 'alice', '--goal', goal)

    def test_goal_history_and_zero_days(self):
        self.solve()
        self.cli('goal', '2', '--from', '2026-09-06')
        profile = study.profiles()['alice']
        self.assertEqual(study.goal_at(profile, DAY), 5)
        self.assertEqual(study.goal_at(profile, '2026-09-06'), 2)
        report = study.dashboard('2026-09-06', 3)
        self.assertIn('— 0/2', report)
        self.assertIn('🔸 1/5', report)
        self.assertIn('| 2026-09-04 | · |', report)
        self.cli('check')

    def test_stale_index_and_missing_metadata_detected(self):
        folder = self.solve()
        (folder.parent / 'README.md').write_text('stale')
        with self.assertRaisesRegex(ValueError, '목록이 오래'):
            study.check_all()
        self.cli('index', '--date', DAY)
        self.cli('check')
        (folder / 'meta.json').unlink()
        with self.assertRaisesRegex(ValueError, 'meta.json 누락'):
            study.check_all()

    def test_wrong_folder_and_code_path(self):
        folder = self.create()
        data = study.read_json(folder / 'meta.json')
        data['solution'] = '../../outside.py'
        study.write_json(folder / 'meta.json', data)
        with self.assertRaisesRegex(ValueError, '코드 파일명'):
            study.check_all()
        data['solution'] = 'solution.py'
        data['problem_id'] = '1000'
        study.write_json(folder / 'meta.json', data)
        with self.assertRaisesRegex(ValueError, '불일치'):
            study.check_all()

    def test_start_preserves_dirty_work_and_uses_main(self):
        (self.root / 'notes.txt').write_text('my work')
        with self.assertRaisesRegex(ValueError, '미커밋'):
            self.cli('start', '--date', DAY)
        self.assertEqual(self.run_git('branch', '--show-current'), 'main')
        self.run_git('add', '.')
        self.run_git('commit', '-m', 'local only')
        self.cli('start', '--date', DAY)
        self.assertEqual(self.run_git('rev-parse', 'HEAD'), self.base)
        self.assertEqual(self.run_git('show', 'main:notes.txt'), 'my work')
        with self.assertRaises(subprocess.CalledProcessError):
            self.cli('start', '--date', DAY)

    def test_daily_branch_rejects_unrelated_files_and_other_date(self):
        self.cli('start', '--date', DAY)
        self.solve()
        (self.root / 'unrelated.txt').write_text('unrelated')
        self.run_git('add', '.')
        self.run_git('commit', '-m', 'unrelated')
        with self.assertRaisesRegex(ValueError, '일일 PR에는'):
            study.check_all('study/alice/' + DAY, self.base)

    def test_reviewer_rotation_is_balanced_without_self_review(self):
        members = {name: {'joined': DAY} for name in ('alice', 'bob', 'charlie', 'dana')}
        seen = set()
        for day in ('2026-09-05', '2026-09-06', '2026-09-07'):
            reviewers = [study.reviewer_for(user, day, members) for user in members]
            self.assertEqual(len(set(reviewers)), 4)
            for user, reviewer in zip(members, reviewers):
                self.assertNotEqual(user, reviewer)
            seen.add(study.reviewer_for('alice', day, members))
        self.assertEqual(seen, {'bob', 'charlie', 'dana'})

    def test_multilanguage_and_draft_excluded_from_totals(self):
        for index, language in enumerate(study.LANGUAGES):
            folder = self.create(f'https://www.acmicpc.net/problem/{1000 + index}', lang=language)
            self.assertTrue((folder / study.LANGUAGES[language][0]).exists())
        self.cli('check')
        self.assertIn('| alice | 0 / 5 | 0 |', study.dashboard(DAY))

    def test_publish_creates_and_updates_only_progress(self):
        self.solve()
        self.cli('note', '--title', 'Git 정리', '--date', DAY)
        self.finish_note(study.daily_path('alice', DAY) / 'note-01')
        self.cli('report', '--date', DAY)
        spec = importlib.util.spec_from_file_location('publish_progress', SOURCE / 'scripts/publish_progress.py')
        publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publisher)
        with patch.object(publisher, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()):
            publisher.publish()
            first = self.run_git('ls-remote', 'origin', 'refs/heads/progress')
            publisher.publish()
            self.assertEqual(first, self.run_git('ls-remote', 'origin', 'refs/heads/progress'))
            self.cli('report', '--date', '2026-09-06')
            publisher.publish()
        self.assertNotEqual(first, self.run_git('ls-remote', 'origin', 'refs/heads/progress'))
        self.run_git('fetch', 'origin', 'progress')
        self.assertEqual(self.run_git('ls-tree', '--name-only', 'FETCH_HEAD'), 'README.md')
        self.assertIn('Git 정리', self.run_git('show', 'FETCH_HEAD:README.md'))
        self.assertEqual(self.run_git('rev-parse', 'main'), self.base)
        self.assertEqual(self.run_git('branch', '--show-current'), 'main')

    def test_repository_url_and_absolute_pr_links(self):
        self.cli('start', '--date', DAY)
        self.solve()
        for remote in ('https://github.com/team/study.git', 'git@github.com:team/study.git'):
            self.run_git('remote', 'set-url', 'origin', remote)
            self.assertEqual(study.repository_url(), 'https://github.com/team/study')
        self.cli('prepare', '--date', DAY)
        body = (self.root / '.study/PR.md').read_text(encoding='utf-8')
        self.assertIn('https://github.com/team/study/blob/study%2Falice%2F2026-09-05/records/', body)

    def test_note_only_lifecycle_without_code_or_problem_url(self):
        self.cli('init', 'alice', '--goal', '1')
        self.cli('start', '--date', DAY)
        output = self.cli('note', '--title', 'Git 브랜치 정리', '--date', DAY)
        folder = study.daily_path('alice', DAY) / 'note-01'
        self.assertIn('done note-01 --date ' + DAY, output)
        self.assertEqual({p.name for p in folder.iterdir()}, {'README.md', 'meta.json'})
        content = (folder / 'README.md').read_text(encoding='utf-8')
        self.assertIn('# Git 브랜치 정리', content)
        self.assertNotIn('$title', content)
        self.finish_note(folder)
        self.cli('prepare', '--date', DAY)
        body = (self.root / '.study/PR.md').read_text(encoding='utf-8')
        self.assertIn('1/1건', body)
        self.assertIn('학습 정리', body)
        self.assertNotIn('채점 사이트', body)
        data = study.read_json(folder / 'meta.json')
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['minutes'], 30)
        self.run_git('add', 'records', 'members')
        self.run_git('commit', '-m', 'learning note')
        self.cli('check', '--branch', 'study/alice/' + DAY, '--base', self.base)
        report = study.dashboard(DAY)
        self.assertIn('✅ 1/1', report)
        self.assertIn('| alice | 0 | 1 |', report)
        self.assertIn('note-01/README.md', report)

    def test_mixed_records_share_one_goal_and_pr(self):
        self.cli('init', 'alice', '--goal', '2')
        self.cli('start', '--date', DAY)
        self.solve()
        self.cli('note', '--title', '학습 정리', '--date', DAY)
        self.finish_note(study.daily_path('alice', DAY) / 'note-01')
        self.cli('prepare', '--date', DAY)
        body = (self.root / '.study/PR.md').read_text(encoding='utf-8')
        self.assertIn('2/2건', body)
        self.assertIn('코딩 문제', body)
        self.assertIn('학습 정리', body)
        self.assertIn('채점 사이트', body)
        daily = (study.daily_path('alice', DAY) / 'README.md').read_text(encoding='utf-8')
        self.assertIn('코딩 문제 1건 · 학습 정리 1건', daily)
        report = study.dashboard(DAY)
        self.assertIn('| alice | 1 | 1 |', report)
        self.assertIn('✅ 2/2', report)
        self.assertIn('학습 정리 모아보기', report)
        self.cli('check')

    def test_note_draft_is_excluded_and_cannot_be_submitted(self):
        self.cli('start', '--date', DAY)
        self.cli('note', '--title', '미완료 정리', '--date', DAY)
        folder = study.daily_path('alice', DAY) / 'note-01'
        with self.assertRaisesRegex(ValueError, '항목을 작성'):
            self.cli('done', 'note-01', '--date', DAY)
        self.assertEqual(study.read_json(folder / 'meta.json')['status'], 'draft')
        self.assertIn('| alice | 0 / 5 | 0 |', study.dashboard(DAY))
        with self.assertRaisesRegex(ValueError, 'draft'):
            self.cli('prepare', '--date', DAY)
        self.run_git('add', 'records', 'members')
        self.run_git('commit', '-m', 'draft note')
        with self.assertRaisesRegex(ValueError, 'draft'):
            self.cli('check', '--branch', 'study/alice/' + DAY, '--base', self.base)

    def test_note_numbering_custom_slug_and_no_overwrite(self):
        for title in ('첫 정리', '두 번째 정리'):
            self.cli('note', '--title', title, '--date', DAY)
        daily = study.daily_path('alice', DAY)
        self.assertTrue((daily / 'note-01/meta.json').exists())
        self.assertTrue((daily / 'note-02/meta.json').exists())
        self.cli('note', '--title', 'Git', '--slug', 'git-branch', '--date', DAY)
        with self.assertRaisesRegex(ValueError, '이미 존재'):
            self.cli('note', '--title', '덮어쓰기', '--slug', 'git-branch', '--date', DAY)
        self.assertEqual(study.read_json(daily / 'note-git-branch/meta.json')['title'], 'Git')
        for slug in ('../escape', '한글', '-git', 'a/b'):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                self.cli('note', '--title', 'Git', '--slug=' + slug, '--date', DAY)
        self.cli('note', '--title', '다음 날', '--date', '2026-09-06')
        self.assertTrue((study.daily_path('alice', '2026-09-06') / 'note-01/meta.json').exists())

    def test_note_import_preserves_source_and_renders_references(self):
        source = self.root / 'existing.md'
        original = '# 내 정리\n\n## 제목\n\n변수 $HOME와 Markdown **본문**\n'
        source.write_text(original, encoding='utf-8')
        reference = 'https://example.com/guide'
        self.cli('note', '--title', '기존 글 가져오기', '--source', str(source), '--reference', reference,
                 '--reference', 'https://example.com/other', '--date', DAY)
        folder = study.daily_path('alice', DAY) / 'note-01'
        self.assertEqual((folder / 'notes.md').read_text(encoding='utf-8'), original)
        self.assertEqual(source.read_text(encoding='utf-8'), original)
        readme = (folder / 'README.md').read_text(encoding='utf-8')
        self.assertIn('[notes.md](notes.md)', readme)
        self.assertIn(reference, readme)
        self.finish_note(folder)
        self.cli('check')
        (folder / 'notes.md').write_text(' ', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '비어 있습니다'):
            self.cli('check')

    def test_invalid_notes_do_not_create_records(self):
        for reference in ('file:///tmp/private', 'javascript:alert(1)', 'https://a:b@example.com', 'https://example.com/a b'):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                self.cli('note', '--title', '정리', '--reference', reference, '--date', DAY)
        empty = self.root / 'empty.md'
        empty.write_text('', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '비어 있습니다'):
            self.cli('note', '--title', '빈 정리', '--source', str(empty), '--date', DAY)
        self.assertEqual(study.records(), [])
        self.assertEqual(study.profiles(), {})

    def test_note_schema_and_required_sections_are_enforced(self):
        self.cli('note', '--title', '정리', '--date', DAY)
        folder = study.daily_path('alice', DAY) / 'note-01'
        data = study.read_json(folder / 'meta.json')
        for field, value in (('type', 'unknown'), ('note_id', '02'), ('source_file', '../../outside.md'), ('status', 'solved')):
            with self.subTest(field=field), self.assertRaises(ValueError):
                study.validate_record(folder, dict(data, **{field: value}), study.profiles())
        readme = folder / 'README.md'
        readme.write_text(readme.read_text(encoding='utf-8').replace('## 정리 내용', '## 다른 제목'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '정리 내용 항목 누락'):
            self.cli('check')

    def test_legacy_problem_records_work_without_type_or_index_migration(self):
        folder = self.solve()
        data = study.read_json(folder / 'meta.json')
        data.pop('type')
        study.write_json(folder / 'meta.json', data)
        # Exact original problem-only daily format must remain valid.
        expected = ('# 2026-09-05 · alice\n\n완료 **1 / 5** · 진행 중\n\n'
                    '<!-- study.py 자동 생성: 문제별 README를 수정하세요. -->\n\n'
                    '| 문제 | 언어 | 상태 | 코드 |\n| --- | --- | --- | --- |\n'
                    '| [테스트 문제](programmers-42747/README.md) | python | solved | [보기](programmers-42747/solution.py) |\n')
        self.assertEqual((folder.parent / 'README.md').read_text(encoding='utf-8'), expected)
        self.cli('check')
        self.assertIn('| alice | 1 | 0 |', study.dashboard(DAY))

    def test_template_updates_apply_only_to_new_records(self):
        for command, template_name in (('new', 'problem.md'), ('note', 'note.md')):
            with self.subTest(command=command):
                if command == 'new':
                    first = self.create()
                else:
                    self.cli('note', '--title', '첫 정리', '--date', DAY)
                    first = study.daily_path('alice', DAY) / 'note-01'
                original = (first / 'README.md').read_text(encoding='utf-8')
                template = self.root / 'templates' / template_name
                template.write_text(template.read_text(encoding='utf-8') + '\n## 추가 질문 (선택)\n\n새 항목입니다.\n', encoding='utf-8')
                if command == 'new':
                    second = self.create('https://www.acmicpc.net/problem/1000')
                else:
                    self.cli('note', '--title', '두 번째 정리', '--date', DAY)
                    second = study.daily_path('alice', DAY) / 'note-02'
                self.assertEqual((first / 'README.md').read_text(encoding='utf-8'), original)
                self.assertIn('새 항목입니다.', (second / 'README.md').read_text(encoding='utf-8'))
        self.cli('check')


if __name__ == '__main__':
    unittest.main()
