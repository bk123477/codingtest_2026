#!/usr/bin/env python3
"""Apply evidence-based metadata without marking a record complete or calling AI."""
import argparse
import json
from pathlib import Path
import sys

import study
from study_wiki.common import (TAXONOMY, TAXONOMY_PATH, alias_map, normalize,
                                safe_file, register_taxonomy, taxonomy_proposals,
                                term_key)
from study_wiki.knowledge import exam_metadata


def enrich(folder, values, replace=False, add_taxonomy=False):
    root = study.ROOT.resolve()
    folder = Path(folder)
    if not folder.is_absolute():
        folder = root / folder
    meta = safe_file(root / 'records', folder / 'meta.json')
    readme = safe_file(root / 'records', folder / 'README.md')
    data = json.loads(meta.read_text(encoding='utf-8'))
    before = dict(data)
    changed, kept = [], []
    taxonomy_file = root / 'study_wiki' / 'taxonomy.json'
    taxonomy_backup = (taxonomy_file.read_bytes()
                       if add_taxonomy and taxonomy_file.is_file() and not taxonomy_file.is_symlink()
                       and not taxonomy_file.parent.is_symlink()
                       else None)
    pending_taxonomy = {'data_structures': [], 'algorithms': []}
    for field, value in values.items():
        if value is None:
            continue
        if field not in ('data_structures', 'algorithms', 'tags', 'level', 'exam'):
            raise ValueError(f'지원하지 않는 필드: {field}')
        if field == 'exam':
            value = exam_metadata(value)
        elif field == 'level':
            if study.record_type(data) != 'problem':
                raise ValueError('학습 정리에는 난이도를 지정하지 않습니다.')
            value = value.strip()
        else:
            value = normalize(value, field)
        if data.get(field) and not replace:
            kept.append(field)
        elif data.get(field) != value:
            data[field] = value
            changed.append(field)
    original = readme.read_bytes()
    original_meta = meta.read_bytes()
    try:
        if add_taxonomy:
            local_taxonomy = None
            if taxonomy_file.is_file() and not taxonomy_file.is_symlink():
                local_taxonomy = json.loads(taxonomy_file.read_text(encoding='utf-8'))
            for field in ('data_structures', 'algorithms'):
                if values.get(field) is not None and (field not in kept or replace):
                    normalized = normalize(values[field], field)
                    known = alias_map(field, local_taxonomy) if local_taxonomy is not None else alias_map(field)
                    pending_taxonomy[field] = [term for term in normalized if term_key(term) not in known]
            taxonomy_proposals(pending_taxonomy)
            if any(pending_taxonomy.values()):
                register_taxonomy(pending_taxonomy, path=taxonomy_file)
                # Re-normalize with the newly registered canonical labels.
                for field in ('data_structures', 'algorithms'):
                    if pending_taxonomy[field]:
                        data[field] = normalize(data[field], field)
        # Validate before writing; status, author, dates and personal experience stay intact.
        study.validate_record(folder, data, study.profiles())
        if changed:
            if study.record_type(data) == 'problem' and any(f in ('level', 'data_structures', 'algorithms') for f in changed):
                study.sync_problem_metadata(folder, data)
            study.write_json(meta, data)
    except Exception:
        readme.write_bytes(original)
        meta.write_bytes(original_meta)
        if taxonomy_backup is not None:
            taxonomy_file.write_bytes(taxonomy_backup)
            if taxonomy_file.resolve() == TAXONOMY_PATH.resolve():
                TAXONOMY.clear()
                TAXONOMY.update(json.loads(taxonomy_backup.decode('utf-8')))
        raise
    assert data['status'] == before['status']
    return changed, kept


def main(argv=None):
    parser = argparse.ArgumentParser(description='근거를 확인한 메타데이터 보완. AI 호출·코드 변경·완료 처리는 하지 않습니다.')
    parser.add_argument('record', help='records/.../문제 또는 note 폴더')
    for flag in ('data-structures', 'algorithms', 'tags'):
        parser.add_argument('--' + flag, help='쉼표로 구분. 기존 값은 기본적으로 보존')
    parser.add_argument('--difficulty', dest='level', help='원문에서 확인한 난이도')
    parser.add_argument('--exam-name', help='확인된 시험·채용 이름')
    parser.add_argument('--exam-organization', help='주관 기관·기업')
    parser.add_argument('--exam-year', help='출제 연도')
    parser.add_argument('--exam-round', help='회차·직군')
    parser.add_argument('--exam-url', help='확인 가능한 기출 출처 링크')
    parser.add_argument('--replace', action='store_true', help='명시한 필드만 기존 값을 교체 (빈 문자열은 비우기)')
    parser.add_argument('--add-taxonomy', action='store_true',
                        help='LLM이 제안한 새 자료구조·알고리즘을 taxonomy.json에 등록 (관리 PR에서 사용)')
    args = parser.parse_args(argv)
    values = {f: getattr(args, f) for f in ('data_structures', 'algorithms', 'tags', 'level')}
    for field in ('data_structures', 'algorithms', 'tags'):
        if values[field] is not None:
            values[field] = [s.strip() for s in values[field].split(',') if s.strip()]
    exam = {key: getattr(args, 'exam_' + key) for key in ('name','organization','year','round','url') if getattr(args, 'exam_' + key) is not None}
    if exam:
        values['exam'] = exam
    try:
        changed, kept = enrich(args.record, values, args.replace, args.add_taxonomy)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'오류: {exc}\n')
    suffix = '; 새 자료구조·알고리즘은 taxonomy.json에 등록했습니다' if args.add_taxonomy else ''
    print(f'보완: {", ".join(changed) or "변경 없음"}; 기존 값 보존: {", ".join(kept) or "없음"}. 완료 상태는 유지했습니다{suffix}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
