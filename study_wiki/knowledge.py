"""Concept links, exam provenance and generated-note records."""
from collections import Counter, defaultdict
import hashlib
import json
import re
from pathlib import Path

from .common import normalize, safe_file, is_placeholder, classify


def exam_metadata(value):
    if value in (None, {}):
        return {}
    if not isinstance(value, dict) or set(value) - {'organization', 'name', 'year', 'round', 'url'}:
        raise ValueError('exam: organization/name/year/round/url 객체가 필요합니다.')
    result = {}
    for key, text in value.items():
        if not isinstance(text, str) or len(text) > 300 or '\n' in text:
            raise ValueError(f'exam.{key}: 한 줄 문자열이 필요합니다.')
        if text.strip():
            result[key] = text.strip()
    if result and not result.get('name'):
        raise ValueError('기출 정보에는 시험·채용 이름(name)이 필요합니다.')
    if result.get('url'):
        from urllib.parse import urlsplit
        url = urlsplit(result['url'])
        if url.scheme not in ('https', 'http') or not url.netloc:
            raise ValueError('기출 출처는 http(s) URL이어야 합니다.')
    return result


def concept_terms(record):
    # Language/difficulty tags are useful filters but not concept relationships.
    generic = {'python','javascript','typescript','java','c','cpp','c++','go','rust','kotlin','swift'}
    core = classify(record)
    return sorted({t for t in core['data_structures'] + core['algorithms']
                   if not is_placeholder(t) and t.casefold() not in generic and not re.match(r'^(lv\.?|level)\s*\d', t, re.I)})


def concept_graph(records):
    groups = defaultdict(list)
    edges = Counter()
    for r in records:
        terms = concept_terms(r)
        for term in terms:
            groups[term].append(r['id'])
        # AI-generated prose must not manufacture evidence of a concept connection.
        if r['kind'] != 'ai_note':
            for i, term in enumerate(terms):
                for other in terms[i+1:]:
                    edges[(term, other)] += 1
    return {'nodes': [{'name': t, 'records': groups[t]} for t in sorted(groups)],
            'edges': [{'source': a, 'target': b, 'count': n} for (a,b), n in sorted(edges.items())]}


def read_ai_notes(root, human_records, user=None):
    root = Path(root).resolve()
    humans = {r['id']: r for r in human_records}
    results = []
    for meta in sorted((root / 'wiki_notes/generated').glob('*/meta.json')):
        safe_file(root, meta)
        folder = meta.parent
        data = json.loads(meta.read_text(encoding='utf-8'))
        if data.get('type') != 'ai_note' or data.get('generated') is not True:
            raise ValueError(f'AI 생성 표시가 필요합니다: {meta}')
        if data.get('review_status') not in ('unreviewed', 'reviewed'):
            raise ValueError(f'AI 노트 검토 상태 오류: {meta}')
        for key in ('title', 'model', 'date'):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(f'AI 노트 {key} 누락: {meta}')
        sources = data.get('sources')
        if not isinstance(sources, list) or len(sources) < 2:
            raise ValueError(f'AI 노트는 원본 근거가 2개 이상 필요합니다: {meta}')
        if any(not isinstance(s, dict) or not isinstance(s.get('id'), str) or not s['id'].startswith('records/')
               or '..' in Path(s['id']).parts or not re.fullmatch('[a-f0-9]{64}', s.get('hash', '')) for s in sources):
            raise ValueError(f'AI 노트 원본 경로·해시 오류: {meta}')
        contributors = sorted({humans[s['id']]['user'] for s in sources if s['id'] in humans})
        if user and user not in contributors:
            continue
        body = safe_file(root, folder/'README.md').read_text(encoding='utf-8')
        tags = normalize(data.get('topics', []), 'algorithms')
        stale = any(s['id'] not in humans or humans[s['id']]['source_hash'] != s['hash'] for s in sources)
        results.append(dict(id=folder.relative_to(root).as_posix(), kind='ai_note', user='AI', contributors=contributors,
                            title=data['title'], date=data['date'], status=data['review_status'], language='',level='',
                            platform='',problem_id='',url='',solve_method='',**classify({'tags': tags}),
                            exam={},origin='ai',model=data['model'],stale=stale,sources=sources,
                            files={'README.md':body},summary=data.get('summary','AI 생성 개념 노트'),
                            search=(body+' '+data['title']+' '+' '.join(tags+contributors)).casefold(),
                            source_hash=hashlib.sha256((body+json.dumps(data,sort_keys=True)).encode()).hexdigest()))
    return results
