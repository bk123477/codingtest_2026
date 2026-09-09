import json
import unicodedata
from pathlib import Path
from copy import deepcopy

PACKAGE = Path(__file__).resolve().parent
TAXONOMY_PATH = PACKAGE / 'taxonomy.json'
TAXONOMY = json.loads(TAXONOMY_PATH.read_text(encoding='utf-8'))


PLACEHOLDERS = {'none', 'null', 'n/a', '미분류', '미입력', '없음', '-'}

def is_placeholder(value):
    return isinstance(value,str) and value.strip().casefold() in PLACEHOLDERS

def term_key(value):
    """Spacing, Unicode presentation and case never define a new category."""
    return ''.join(unicodedata.normalize('NFKC', value).casefold().split())


def alias_map(field, taxonomy=None):
    taxonomy = TAXONOMY if taxonomy is None else taxonomy
    groups = taxonomy.values() if field == 'tags' else [taxonomy.get(field, {})]
    aliases = {}
    for group in groups:
        for name, names in group.items():
            for alias in [name, *names]:
                key = term_key(alias)
                if key in aliases and aliases[key] != name:
                    raise ValueError(f'분류 별칭 충돌: {alias}')
                aliases[key] = name
    return aliases


def normalize(values, field, taxonomy=None):
    aliases = alias_map(field, taxonomy)
    if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f'{field}: 비어 있지 않은 문자열 배열이 필요합니다.')
    result = {}
    for value in values:
        if is_placeholder(value):
            continue
        name = aliases.get(term_key(value), ' '.join(unicodedata.normalize('NFKC', value).split()))
        result.setdefault(term_key(name), name)
    return list(result.values())


def _clean_taxonomy_text(value, label):
    if not isinstance(value, str):
        raise ValueError(f'{label}: 문자열이어야 합니다.')
    if '\n' in value or '\r' in value:
        raise ValueError(f'{label}: 한 줄 문자열이어야 합니다.')
    value = ' '.join(unicodedata.normalize('NFKC', value).split())
    if not value or len(value) > 80 or is_placeholder(value):
        raise ValueError(f'{label}: 1~80자의 유효한 분류명이어야 합니다.')
    return value


def validate_taxonomy(taxonomy):
    """Validate the checked-in taxonomy and reject ambiguous aliases."""
    if not isinstance(taxonomy, dict) or set(taxonomy) != {'data_structures', 'algorithms'}:
        raise ValueError('taxonomy는 data_structures/algorithms 객체여야 합니다.')
    for field, group in taxonomy.items():
        if not isinstance(group, dict):
            raise ValueError(f'taxonomy.{field}는 객체여야 합니다.')
        for name, aliases in group.items():
            _clean_taxonomy_text(name, f'taxonomy.{field}')
            if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
                raise ValueError(f'taxonomy.{field}.{name}의 별칭 배열이 올바르지 않습니다.')
    alias_map('tags', taxonomy)
    return taxonomy


def taxonomy_proposals(value):
    """Normalize an LLM's new_taxonomy object without writing files.

    Each entry may be a canonical string or {name, aliases}. Strings are useful
    for a genuinely new term when no spelling variant is known yet.
    """
    if value in (None, {}):
        return {'data_structures': [], 'algorithms': []}
    if not isinstance(value, dict) or set(value) - {'data_structures', 'algorithms'}:
        raise ValueError('new_taxonomy는 data_structures/algorithms만 포함해야 합니다.')
    result = {'data_structures': [], 'algorithms': []}
    for field in result:
        entries = value.get(field, [])
        if not isinstance(entries, list) or len(entries) > 16:
            raise ValueError(f'new_taxonomy.{field}는 최대 16개의 항목 배열이어야 합니다.')
        seen = set()
        for index, entry in enumerate(entries):
            label = f'new_taxonomy.{field}[{index}]'
            if isinstance(entry, str):
                name, aliases = entry, []
            elif isinstance(entry, dict):
                if set(entry) - {'name', 'aliases'} or 'name' not in entry:
                    raise ValueError(f'{label}은 name/aliases 객체여야 합니다.')
                name, aliases = entry['name'], entry.get('aliases', [])
                if not isinstance(aliases, list) or len(aliases) > 16:
                    raise ValueError(f'{label}.aliases는 최대 16개의 문자열 배열이어야 합니다.')
            else:
                raise ValueError(f'{label}은 문자열 또는 객체여야 합니다.')
            name = _clean_taxonomy_text(name, label + '.name')
            if any(not isinstance(alias, str) for alias in aliases):
                raise ValueError(f'{label}.aliases의 항목은 문자열이어야 합니다.')
            cleaned_aliases = []
            alias_keys = {term_key(name)}
            for alias in aliases:
                alias = _clean_taxonomy_text(alias, label + '.aliases')
                if term_key(alias) not in alias_keys:
                    cleaned_aliases.append(alias)
                    alias_keys.add(term_key(alias))
            aliases = cleaned_aliases
            key = term_key(name)
            if key in seen:
                raise ValueError(f'{label}: 같은 새 분류가 중복되었습니다.')
            seen.add(key)
            result[field].append({'name': name, 'aliases': aliases})
    return result


def taxonomy_with_proposals(proposals, taxonomy=None):
    """Return a validated, in-memory taxonomy with proposals merged."""
    current = deepcopy(TAXONOMY if taxonomy is None else taxonomy)
    validate_taxonomy(current)
    proposals = taxonomy_proposals(proposals)
    for field, entries in proposals.items():
        for entry in entries:
            name, aliases = entry['name'], entry['aliases']
            candidate_names = [name, *aliases]
            name_matches = {}
            matches = {}
            for candidate_index, candidate in enumerate(candidate_names):
                key = term_key(candidate)
                for existing_field, group in current.items():
                    existing = alias_map(existing_field, current)
                    if key in existing:
                        matches.setdefault(existing_field, set()).add(existing[key])
                        if candidate_index == 0:
                            name_matches.setdefault(existing_field, set()).add(existing[key])
            if matches:
                # An alias may extend a known entry only when the proposed
                # canonical name itself already identifies that same entry.
                # Otherwise a typo or an accidental synonym would silently
                # rename an established category.
                if not name_matches:
                    raise ValueError(f'새 분류 별칭이 기존 분류와 충돌합니다: {name}')
                if set(matches) != {field} or len(matches[field]) != 1:
                    raise ValueError(f'새 분류 별칭이 기존 분류와 충돌합니다: {name}')
                canonical = next(iter(matches[field]))
                target = current[field][canonical]
                alias_keys = {term_key(canonical), *(term_key(alias) for alias in target)}
                for alias in candidate_names:
                    if term_key(alias) not in alias_keys:
                        target.append(alias)
                        alias_keys.add(term_key(alias))
                continue
            current[field][name] = aliases
            # Re-run the global collision check after each insertion so a
            # proposal cannot shadow a term in the other category.
            alias_map('tags', current)
    return current


def register_taxonomy(proposals, path=None):
    """Persist validated LLM proposals and refresh the process-local taxonomy."""
    proposals = taxonomy_proposals(proposals)
    if not any(proposals.values()):
        return {'added': [], 'merged': [], 'path': str(path or TAXONOMY_PATH)}
    target = Path(path or TAXONOMY_PATH).absolute()
    # Check the file and its repository directory. System paths such as
    # macOS /var may themselves be compatibility symlinks and are harmless.
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError(f'taxonomy 경로에 심볼릭 링크가 있습니다: {target}')
    target = target.resolve()
    if not target.is_file():
        raise ValueError(f'taxonomy 파일이 없습니다: {target}')
    current = json.loads(target.read_text(encoding='utf-8'))
    before = deepcopy(current)
    merged = taxonomy_with_proposals(proposals, current)
    added = [entry['name'] for field in proposals for entry in proposals[field]
             if entry['name'] in merged[field] and entry['name'] not in before[field]]
    if merged == before:
        return {'added': added, 'merged': [], 'path': str(target)}
    temporary = target.with_suffix(target.suffix + '.tmp')
    temporary.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(target)
    if target == TAXONOMY_PATH.resolve():
        TAXONOMY.clear()
        TAXONOMY.update(merged)
    return {'added': added, 'merged': [entry['name'] for field in proposals for entry in proposals[field]
                                      if entry['name'] not in added], 'path': str(target)}


def unknown_taxonomy_terms(values, taxonomy=None):
    """Return only new core labels from a record's DS/algorithm fields."""
    taxonomy = TAXONOMY if taxonomy is None else taxonomy
    result = {'data_structures': [], 'algorithms': []}
    for field in result:
        raw = values.get(field, []) if isinstance(values, dict) else []
        normalized = normalize(raw, field, taxonomy)
        aliases = alias_map(field, taxonomy)
        result[field] = [term for term in normalized if term_key(term) not in aliases]
    return result


def classify(record):
    """Only curated core concepts become facets; unknown terms remain searchable.

    No fuzzy matching: an unseen technique cannot safely be assigned a meaning.
    Legacy metadata is projected without rewriting the author's source files.
    """
    values = []
    for field in ('data_structures', 'algorithms', 'tags'):
        values.extend(normalize(record.get(field, []), 'tags'))
    values = normalize(values, 'tags')
    known = alias_map('tags')
    return {
        'data_structures': [v for v in dict.fromkeys(values) if v in TAXONOMY['data_structures']],
        'algorithms': [v for v in dict.fromkeys(values) if v in TAXONOMY['algorithms']],
        'tags': [],
        'keywords': [v for v in dict.fromkeys(values) if term_key(v) not in known],
    }


def safe_file(root, path):
    """Never read a symlink or a file outside the selected source tree."""
    root = root.resolve()
    if not path.is_absolute():
        path = root / path
    if not path.resolve().is_relative_to(root):
        raise ValueError(f'원본 폴더 밖의 경로: {path}')
    current = path
    while True:
        if current.is_symlink():
            raise ValueError(f'심볼릭 링크는 지원하지 않습니다: {path}')
        if current.resolve() == root:
            break
        if current == current.parent:
            raise ValueError(f'원본 경로를 확인할 수 없습니다: {path}')
        current = current.parent
    if not path.is_file():
        raise ValueError(f'파일이 없습니다: {path}')
    return path
