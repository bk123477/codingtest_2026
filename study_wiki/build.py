"""Reproducible, API-free knowledge index and static reader."""
from collections import defaultdict
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote, urlsplit

from .common import PACKAGE, normalize, safe_file, TAXONOMY
from .render import markdown, safe_url
from .knowledge import exam_metadata, concept_graph, read_ai_notes


def read_records(root, include_drafts=False, user=None):
    root = Path(root).resolve()
    records = []
    for meta in sorted((root / 'records').rglob('meta.json')):
        safe_file(root / 'records', meta)
        data = json.loads(meta.read_text(encoding='utf-8'))
        folder = meta.parent
        relative = folder.relative_to(root).as_posix()
        parts = folder.relative_to(root / 'records').parts
        if len(parts) != 5 or data.get('user') != parts[3] or data.get('date') != '-'.join(parts[:3]):
            raise ValueError(f'날짜·작성자·경로 불일치: {meta}')
        kind = data.get('type', 'problem')
        if kind not in ('problem', 'note') or data.get('status') not in ('draft', 'solved' if kind == 'problem' else 'completed'):
            raise ValueError(f'기록 유형 또는 상태 오류: {meta}')
        if not include_drafts and data['status'] == 'draft':
            continue
        if user and data['user'] != user:
            continue
        for field in ('title', 'user', 'date'):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise ValueError(f'{field} 누락: {meta}')
        files = ['README.md']
        if kind == 'problem':
            name = data.get('solution', '')
            if not name or Path(name).name != name:
                raise ValueError(f'코드 파일명 오류: {meta}')
            files.append(name)
        elif data.get('source_file'):
            if data['source_file'] != 'notes.md':
                raise ValueError(f'학습 원본 파일명 오류: {meta}')
            files.append('notes.md')
        contents = {name: safe_file(root / 'records', folder / name).read_text(encoding='utf-8') for name in files}
        digest = hashlib.sha256(json.dumps([data, contents], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        item = {key: data.get(key, '') for key in ('title', 'user', 'date', 'status', 'language', 'level', 'platform', 'problem_id', 'url', 'solve_method')}
        item.update(id=relative, kind=kind, files=contents, source_hash=digest, origin='human', exam=exam_metadata(data.get('exam')))
        for field in ('data_structures', 'algorithms', 'tags'):
            item[field] = normalize(data.get(field, []), field)
        text = re.sub(r'<!--.*?-->', '', contents['README.md'], flags=re.S)
        sections = re.split(r'^## (.+)\s*$', text, flags=re.M)
        sections = {sections[n].strip(): sections[n+1].strip() for n in range(1, len(sections), 2)}
        item['summary'] = sections.get('Wiki 요약') or sections.get('풀이' if kind == 'problem' else '학습 주제 / 목표', '')
        item['summary'] = re.sub(r'\s+', ' ', item['summary'])[:240]
        item['search'] = '\n'.join([text, *contents.values(), *map(str, item.values())]).casefold()
        records.append(item)
    return sorted(records, key=lambda r: (r['date'], r['id']), reverse=True)


def build(root, output, include_drafts=False, user=None, repo_url='', ref='main'):
    root, output = Path(root).resolve(), Path(output).absolute()
    # Build only to an owned directory; never recursively delete a user directory.
    if output.is_symlink() or output.resolve() == root or root.is_relative_to(output.resolve()):
        raise ValueError('출력 폴더는 저장소 루트 또는 상위 경로일 수 없습니다.')
    if output.resolve().is_relative_to(root / 'records'):
        raise ValueError('records 안에는 Wiki를 생성할 수 없습니다.')
    marker = output / '.study-wiki-output'
    if output.exists() and (not output.is_dir() or (any(output.iterdir()) and not marker.is_file())):
        raise ValueError('비어 있거나 Wiki 생성기가 관리하는 출력 폴더를 지정하세요.')
    if output.exists() and any(p.is_symlink() for p in output.rglob('*')):
        raise ValueError('출력 폴더에 심볼릭 링크가 있습니다.')
    human_records = read_records(root, include_drafts)
    records = [r for r in human_records if not user or r['user'] == user]
    records += read_ai_notes(root, human_records, user)
    if repo_url and (urlsplit(repo_url).scheme != 'https' or not urlsplit(repo_url).netloc or urlsplit(repo_url).query or urlsplit(repo_url).fragment):
        raise ValueError('--repo-url은 HTTPS 저장소 URL이어야 합니다.')
    repo_url = repo_url.rstrip('/')
    blob = f'{repo_url}/blob/{quote(ref, safe="")}/' if repo_url else ''
    ids = {r['id'] for r in records}
    for record in records:
        def resolve(target, record=record):
            if urlsplit(target).scheme or target.startswith(('//', '#')):
                return target if safe_url(target) else ''
            path = (root / record['id'] / target).resolve()
            if not (path.is_relative_to(root / 'records') or path.is_relative_to(root / 'wiki_notes')):
                return ''
            relative = path.relative_to(root).as_posix()
            if path.name == 'README.md' and path.parent.relative_to(root).as_posix() in ids:
                return '#record=' + quote(path.parent.relative_to(root).as_posix(), safe='')
            if path.name in record['files'] and relative == record['id'] + '/' + path.name:
                if record['kind'] == 'problem' and path.name not in ('README.md', 'notes.md'):
                    return '#record=' + quote(record['id'], safe='') + '&tab=code'
                return 'sources/' + quote(relative, safe='/') + '.html'
            return blob + quote(relative, safe='/') if blob else ''
        record['html'] = markdown(record['files']['README.md'], resolve)
        if 'notes.md' in record['files']:
            record['html'] += '<hr><h2>가져온 학습 정리</h2>' + markdown(record['files']['notes.md'], resolve)
        record['code'] = next((body for name, body in record['files'].items() if name not in ('README.md', 'notes.md')), '')
        record['source_url'] = blob + quote(record['id'] + '/README.md', safe='/') if blob else 'sources/' + quote(record['id'] + '/README.md', safe='/') + '.html'
    # Everything above is checked before replacing previous generated output.
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    marker.write_text('Generated by wiki.py. Do not edit.\n', encoding='utf-8')
    for asset in (PACKAGE / 'assets').iterdir():
        if asset.is_file():
            shutil.copyfile(asset, output / asset.name)
    (output / '.nojekyll').touch()
    people, topics, problems = defaultdict(list), defaultdict(list), defaultdict(list)
    for record in records:
        for person in record.get('contributors', [record['user']]):
            people[person].append(record)
        for topic in dict.fromkeys(record['data_structures'] + record['algorithms'] + record['tags']):
            topics[topic].append(record)
        if record['kind'] == 'problem':
            problems[record['platform'] + '-' + str(record['problem_id'])].append(record)
        for name, body in record['files'].items():
            dest = output / 'sources' / record['id'] / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding='utf-8')
            # A portable UTF-8 viewer is needed on Pages as well as localhost.
            viewer = '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(name) + '</title><body><p><a href="' + quote(name) + '" download>원본 다운로드</a></p><pre style="white-space:pre;tab-size:4;line-height:1.7;overflow:auto">' + html.escape(body) + '</pre></body></html>'
            dest.with_name(name + '.html').write_text(viewer, encoding='utf-8')
    data = {'version': 1, 'ref': ref, 'preview': include_drafts, 'user': user or '', 'records': [{k: v for k, v in r.items() if k != 'files'} for r in records], 'taxonomy': TAXONOMY, 'graph': concept_graph(records), 'repo_url': repo_url}
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    (output / 'data.js').write_text('window.STUDY_WIKI = ' + payload + ';\n', encoding='utf-8')
    mdroot = output / 'markdown'
    mdroot.mkdir()
    def label(value):
        return html.escape(str(value)).replace('[', '&#91;').replace(']', '&#93;').replace('\n', ' ')
    def page(category, title, rows):
        slug = hashlib.sha256(title.encode()).hexdigest()[:16]
        name = category + '/' + slug + '.md'
        dest = mdroot / name
        dest.parent.mkdir(exist_ok=True)
        lines = [f'# {label(title)}', '', '원본 기록에서 생성한 연결 목록입니다. 설명 보완은 원본 README에서 검토합니다.', '']
        for r in rows:
            link = '../../sources/' + quote(r['id'] + '/README.md', safe='/')
            lines += [f'- [{label(r["title"])}]({link}) · {label(r["user"])} · {r["date"]} · {r["status"]}', '  ' + label(r['summary'])]
        dest.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return f'- [{label(title)}]({name}) · {len(rows)}건'
    index = ['# Study Wiki', '', f'기록 {len(records)}건 · 참여자 {len(people)}명 · 문제 {len(problems)}개', '', '## 참여자', '']
    index += [page('members', key, people[key]) for key in sorted(people)]
    index += ['', '## 개념', ''] + [page('topics', key, topics[key]) for key in sorted(topics)]
    index += ['', '## 문제별 풀이', ''] + [page('problems', key, problems[key]) for key in sorted(problems)]
    unclassified = [r for r in records if not (r['data_structures'] or r['algorithms'] or (r['tags'] if r['kind'] == 'note' else []))]
    if unclassified:
        index += ['', '## 분류 대기', '', page('topics', '미분류', unclassified)]
    (mdroot / 'README.md').write_text('\n'.join(index) + '\n', encoding='utf-8')
    manifest = {'ref': ref, 'include_drafts': include_drafts, 'user': user, 'sources': {r['id']: r['source_hash'] for r in records}}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return {'records': len(records), 'members': len(people), 'topics': len(topics), 'problems': len(problems), 'unclassified': len(unclassified), 'output': str(output)}
