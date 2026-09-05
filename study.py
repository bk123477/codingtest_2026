#!/usr/bin/env python3
"""Dependency-free study CLI. Dates use Korea Standard Time (UTC+09:00)."""
import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import html
import json
from pathlib import Path
import re
import subprocess
import sys
from string import Template
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
LANGUAGES = {
    'python': ('solution.py', '# TODO: 풀이를 작성하세요.\n'),
    'javascript': ('solution.js', '// TODO: 풀이를 작성하세요.\n'),
    'typescript': ('solution.ts', '// TODO: 풀이를 작성하세요.\n'),
    'java': ('Solution.java', '// TODO: 풀이를 작성하세요.\n'),
    'cpp': ('solution.cpp', '// TODO: 풀이를 작성하세요.\n'),
    'c': ('solution.c', '// TODO: 풀이를 작성하세요.\n'),
    'kotlin': ('Solution.kt', '// TODO: 풀이를 작성하세요.\n'),
    'go': ('solution.go', '// TODO: 풀이를 작성하세요.\n'),
    'swift': ('solution.swift', '// TODO: 풀이를 작성하세요.\n'),
    'rust': ('solution.rs', '// TODO: 풀이를 작성하세요.\n'),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def today():
    return datetime.now(timezone(timedelta(hours=9))).date().isoformat()


def valid_date(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), '날짜는 YYYY-MM-DD 형식입니다.')
    date.fromisoformat(value)
    return value


def valid_user(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?', value),
            '아이디는 영문 소문자, 숫자, 하이픈을 사용하며 1~39자입니다.')
    return value


def positive(value):
    require(type(value) is int and value > 0, '목표는 1 이상의 정수입니다.')
    return value


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def settings():
    return read_json(ROOT / 'study.json')


def local():
    path = ROOT / '.study/config.json'
    require(path.exists(), '먼저 python3 study.py init GitHub아이디 를 실행하세요.')
    data = read_json(path)
    valid_user(data['user'])
    return data


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()


def daily_path(user, day):
    return ROOT / 'records' / day.replace('-', '/') / user


def identify(url):
    parsed = urlsplit(url)
    require(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password,
            '문제 링크는 http(s) URL이어야 합니다.')
    host = parsed.hostname.lower()
    path = parsed.path.rstrip('/')
    if host == 'school.programmers.co.kr' and (m := re.fullmatch(r'/learn/courses/30/lessons/(\d+)', path)):
        platform, pid = 'programmers', m[1]
    elif host in ('www.acmicpc.net', 'acmicpc.net') and (m := re.fullmatch(r'/problem/(\d+)', path)):
        platform, pid, host = 'baekjoon', m[1], 'www.acmicpc.net'
    elif host == 'leetcode.com' and (m := re.fullmatch(r'/problems/([a-z0-9-]+)(?:/description)?', path)):
        platform, pid = 'leetcode', m[1]
        path = '/problems/' + pid
    else:
        raise ValueError('지원 링크: 프로그래머스, 백준, LeetCode 문제 URL')
    return platform, pid, urlunsplit(('https', host, path, '', ''))


def record_type(data):
    # Records written before learning notes were introduced are coding problems.
    return data.get('type', 'problem')


def is_complete(data):
    return data['status'] == ('completed' if record_type(data) == 'note' else 'solved')


def type_label(data):
    return '학습 정리' if record_type(data) == 'note' else '코딩 문제'


def valid_note_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value)
            and len(value) <= 80, '정리 식별자는 1~80자의 영문 소문자·숫자·중간 하이픈을 사용하세요.')
    return value


def valid_reference(value):
    require(isinstance(value, str) and not re.search(r'\s', value), '참고 링크에는 공백을 넣지 마세요.')
    parsed = urlsplit(value)
    require(parsed.scheme in ('https', 'http') and parsed.hostname and not parsed.username and not parsed.password,
            '참고 링크는 http(s) URL이어야 합니다.')
    return value


def profiles():
    result = {}
    for path in sorted((ROOT / 'members').glob('*.json')):
        data = read_json(path)
        require(isinstance(data, dict), f'{path}: JSON 객체가 필요합니다.')
        user = valid_user(data.get('user'))
        require(path.stem == user, f'{path}: 아이디와 파일명이 다릅니다.')
        valid_date(data.get('joined'))
        goals = data.get('goals')
        require(isinstance(goals, list) and goals, f'{path}: goals가 비어 있습니다.')
        days = []
        for item in goals:
            days.append(valid_date(item['from']))
            positive(item['daily_goal'])
        require(days == sorted(set(days)) and days[0] == data['joined'], f'{path}: 목표 적용일 순서/시작일을 확인하세요.')
        result[user] = data
    return result


def goal_at(profile, day):
    goals = [item['daily_goal'] for item in profile['goals'] if item['from'] <= day]
    return goals[-1] if goals else 0


def records():
    return [(path.parent, read_json(path)) for path in sorted((ROOT / 'records').rglob('meta.json'))]


def md(value):
    return html.escape(str(value)).replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;').replace('\n', ' ')


def body_sections(path):
    content = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8'), flags=re.S)
    parts = re.split(r'^## (.+)\s*$', content, flags=re.M)
    return {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts), 2)}


def validate_record(folder, data, members, completed=False):
    require(isinstance(data, dict), f'{folder}: meta.json 객체가 필요합니다.')
    kind = record_type(data)
    require(kind in ('problem', 'note'), f'{folder}: type은 problem 또는 note입니다.')
    for key in ('user', 'date', 'title', 'status', 'tags'):
        require(key in data, f'{folder}: {key} 누락')
    user, day = valid_user(data['user']), valid_date(data['date'])
    require(user in members, f'{folder}: 참여자 등록이 없습니다.')
    require(goal_at(members[user], day) > 0, f'{folder}: 참여 시작일 전 기록입니다.')
    require(isinstance(data['title'], str) and data['title'].strip() and '\n' not in data['title'], f'{folder}: 제목이 필요합니다.')
    require(isinstance(data['tags'], list) and all(isinstance(tag, str) for tag in data['tags']), f'{folder}: tags는 문자열 배열입니다.')
    require(data.get('minutes') is None or (type(data['minutes']) is int and data['minutes'] >= 0), f'{folder}: minutes는 0 이상의 정수입니다.')
    files = ['README.md', 'meta.json']
    if kind == 'problem':
        for key in ('platform', 'problem_id', 'url', 'language', 'solution'):
            require(key in data, f'{folder}: {key} 누락')
        platform, pid, canonical = identify(data['url'])
        require((platform, pid, canonical) == (data['platform'], data['problem_id'], data['url']), f'{folder}: 링크와 문제 정보 불일치')
        require(folder == daily_path(user, day) / f'{platform}-{pid}', f'{folder}: 날짜/아이디/문제 폴더 불일치')
        require(data['language'] in LANGUAGES, f'{folder}: 지원하지 않는 언어')
        filename, starter = LANGUAGES[data['language']]
        require(data['solution'] == filename, f'{folder}: 코드 파일명이 다릅니다.')
        files.append(filename)
        required_sections = ('문제', '풀이', '확인한 예제 / 경계 조건')
        completed_status = 'solved'
    else:
        note_id = valid_note_id(data.get('note_id'))
        require(folder == daily_path(user, day) / f'note-{note_id}', f'{folder}: 날짜/아이디/정리 폴더 불일치')
        references = data.get('references')
        require(isinstance(references, list), f'{folder}: references는 링크 배열입니다.')
        for reference in references:
            valid_reference(reference)
        if 'source_file' in data:
            require(data['source_file'] == 'notes.md', f'{folder}: 가져온 정리 파일명은 notes.md입니다.')
            files.append('notes.md')
        required_sections = ('학습 주제 / 목표', '정리 내용', '배운 점 / 확인한 내용')
        completed_status = 'completed'
    require(data['status'] in ('draft', completed_status), f'{folder}: status는 draft 또는 {completed_status}')
    for name in files:
        require((folder / name).is_file() and not (folder / name).is_symlink(), f'{folder}: {name} 파일이 없거나 심볼릭 링크입니다.')
    sections = body_sections(folder / 'README.md')
    for section in required_sections:
        require(section in sections, f'{folder}: {section} 항목 누락')
        if completed or is_complete(data):
            require(sections[section] and 'TODO:' not in sections[section], f'{folder}: {section} 항목을 작성하세요.')
    if kind == 'problem' and (completed or is_complete(data)):
        code = (folder / filename).read_text(encoding='utf-8').strip()
        require(code and code != starter.strip(), f'{folder}: 실제 풀이 코드를 작성하세요.')
    if kind == 'note' and 'source_file' in data:
        require((folder / 'notes.md').read_text(encoding='utf-8').strip(), f'{folder}: 가져온 정리 파일이 비어 있습니다.')


def daily_markdown(user, day, rows, members):
    done = sum(is_complete(data) for _, data in rows)
    goal = goal_at(members[user], day)
    if any(record_type(data) == 'note' for _, data in rows):
        counts = Counter(record_type(data) for _, data in rows if is_complete(data))
        lines = [f'# {day} · {user}', '', f'완료 **{done} / {goal}** · ' + ('목표 달성 ✅' if done >= goal else '진행 중'), '',
                 f'코딩 문제 {counts["problem"]}건 · 학습 정리 {counts["note"]}건 (완료 기록 1개 = 목표 1건)', '',
                 '<!-- study.py 자동 생성: 각 기록의 README를 수정하세요. -->', '',
                 '| 유형 | 기록 | 상태 | 코드 / 본문 |', '| --- | --- | --- | --- |']
        for folder, data in rows:
            target = data['solution'] if record_type(data) == 'problem' else 'README.md'
            lines.append(f"| {type_label(data)} | [{md(data['title'])}]({folder.name}/README.md) | {data['status']} | [보기]({folder.name}/{target}) |")
        return '\n'.join(lines) + '\n'
    # Preserve existing problem-only indexes so old records need no migration.
    lines = [f'# {day} · {user}', '', f'완료 **{done} / {goal}** · ' + ('목표 달성 ✅' if done >= goal else '진행 중'), '',
             '<!-- study.py 자동 생성: 문제별 README를 수정하세요. -->', '',
             '| 문제 | 언어 | 상태 | 코드 |', '| --- | --- | --- | --- |']
    for folder, data in rows:
        lines.append(f"| [{md(data['title'])}]({folder.name}/README.md) | {data['language']} | {data['status']} | [보기]({folder.name}/{data['solution']}) |")
    return '\n'.join(lines) + '\n'


def refresh(user, day):
    rows = [(p, d) for p, d in records() if d['user'] == user and d['date'] == day]
    if rows:
        (daily_path(user, day) / 'README.md').write_text(daily_markdown(user, day, rows, profiles()), encoding='utf-8')
    return rows


def cmd_init(args):
    config = settings()
    user = valid_user(args.user.lower())
    positive(args.goal if args.goal is not None else config['default_daily_goal'])
    write_json(ROOT / '.study/config.json', {'user': user, 'language': args.lang or config['default_language'],
                                          'daily_goal': args.goal if args.goal is not None else config['default_daily_goal']})
    print(f'{user} 로컬 설정 완료. 첫 new 또는 note 실행 시 참여자 파일을 생성합니다. 기존 참여자의 목표 변경은 goal 명령을 사용하세요.')


def cmd_start(args):
    user = local()['user']
    day = valid_date(args.date)
    config = settings()
    require(not git('status', '--porcelain'), '미커밋 변경이 있습니다. 먼저 커밋하거나 별도로 보관하세요.')
    branch = f'study/{user}/{day}'
    git('fetch', config['remote'], config['base_branch'])
    git('switch', '--no-track', '-c', branch, f"{config['remote']}/{config['base_branch']}")
    print(f'{branch} 생성 완료. 최신 {config["base_branch"]}에서 시작했습니다.')


def member_for_new_record(config, day):
    user = config['user']
    members = profiles()
    if user not in members:
        profile = {'user': user, 'joined': day, 'goals': [{'from': day, 'daily_goal': positive(config['daily_goal'])}]}
    else:
        profile = members[user]
        require(goal_at(profile, day) > 0, '참여 시작일 전입니다. members 파일의 시작일을 먼저 조정하세요.')
    return profile


def cmd_new(args):
    config = local()
    user, day = config['user'], valid_date(args.date)
    platform, pid, url = identify(args.url)
    require(args.title.strip() and '\n' not in args.title, '한 줄 제목이 필요합니다.')
    language = args.lang or config['language']
    filename, starter = LANGUAGES[language]
    folder = daily_path(user, day) / f'{platform}-{pid}'
    require(not folder.exists(), f'이미 존재합니다: {folder.relative_to(ROOT)} (덮어쓰지 않습니다.)')
    source = Path(args.source).resolve() if args.source else None
    require(not source or source.is_file(), '가져올 코드 파일을 찾을 수 없습니다.')
    code = source.read_text(encoding='utf-8') if source else starter
    profile = member_for_new_record(config, day)
    data = {'type': 'problem', 'user': user, 'date': day, 'platform': platform, 'problem_id': pid, 'url': url,
            'title': args.title.strip(), 'language': language, 'solution': filename, 'status': 'draft',
            'level': args.level, 'tags': [tag.strip() for tag in args.tags.split(',') if tag.strip()], 'minutes': None}
    content = Template((ROOT / 'templates/problem.md').read_text(encoding='utf-8')).substitute(**data)
    folder.mkdir(parents=True)
    write_json(ROOT / 'members' / f'{user}.json', profile)
    write_json(folder / 'meta.json', data)
    (folder / 'README.md').write_text(content, encoding='utf-8')
    (folder / filename).write_text(code, encoding='utf-8')
    refresh(user, day)
    print(folder.relative_to(ROOT).as_posix())
    print('코드와 README의 3개 TODO를 작성한 뒤 done 문제URL 을 실행하세요.')


def cmd_note(args):
    config = local()
    user, day = config['user'], valid_date(args.date)
    require(args.title.strip() and '\n' not in args.title, '한 줄 제목이 필요합니다.')
    if args.slug:
        note_id = valid_note_id(args.slug)
    else:
        numbers = [int(path.name[5:]) for path in daily_path(user, day).glob('note-*') if path.name[5:].isdigit()]
        note_id = f'{max(numbers, default=0) + 1:02d}'
    folder = daily_path(user, day) / f'note-{note_id}'
    require(not folder.exists(), f'이미 존재합니다: {folder.relative_to(ROOT)} (덮어쓰지 않습니다.)')
    references = [valid_reference(url) for url in args.reference]
    source = Path(args.source).resolve() if args.source else None
    require(not source or source.is_file(), '가져올 정리 파일을 찾을 수 없습니다.')
    content = source.read_text(encoding='utf-8') if source else None
    require(content is None or content.strip(), '가져올 정리 파일이 비어 있습니다.')
    profile = member_for_new_record(config, day)
    data = {'type': 'note', 'note_id': note_id, 'user': user, 'date': day, 'title': args.title.strip(),
            'status': 'draft', 'tags': [tag.strip() for tag in args.tags.split(',') if tag.strip()],
            'references': references, 'minutes': None}
    if source:
        data['source_file'] = 'notes.md'
    reference_text = '\n'.join(f'- [{md(url)}](<{url}>)' for url in references) or '<!-- 참고한 링크나 책 이름을 자유롭게 적으세요. -->'
    note_content = '가져온 정리: [notes.md](notes.md)' if source else 'TODO: 오늘 정리한 내용을 작성하세요.'
    rendered = Template((ROOT / 'templates/note.md').read_text(encoding='utf-8')).substitute(
        **data, reference_text=reference_text, note_content=note_content)
    folder.mkdir(parents=True)
    write_json(ROOT / 'members' / f'{user}.json', profile)
    write_json(folder / 'meta.json', data)
    (folder / 'README.md').write_text(rendered, encoding='utf-8')
    if source:
        (folder / 'notes.md').write_text(content, encoding='utf-8')
    refresh(user, day)
    print(folder.relative_to(ROOT).as_posix())
    print(f'README의 TODO를 작성한 뒤 python3 study.py done {folder.name} --date {day} 를 실행하세요.')


def cmd_done(args):
    user, day = local()['user'], valid_date(args.date)
    if args.target.startswith('note-'):
        folder = daily_path(user, day) / ('note-' + valid_note_id(args.target[5:]))
    else:
        platform, pid, _ = identify(args.target)
        folder = daily_path(user, day) / f'{platform}-{pid}'
    data = read_json(folder / 'meta.json')
    data['status'] = 'completed' if record_type(data) == 'note' else 'solved'
    if args.minutes is not None:
        data['minutes'] = args.minutes
    validate_record(folder, data, profiles(), completed=True)
    write_json(folder / 'meta.json', data)
    refresh(user, day)
    message = '학습 정리를 완료 처리했습니다.' if record_type(data) == 'note' else '채점 결과는 본인이 확인한 것으로 기록합니다.'
    print(f'{folder.name} 완료 처리. {message}')


def cmd_goal(args):
    user, day = local()['user'], valid_date(args.start)
    positive(args.count)
    members = profiles()
    require(user in members, '첫 new 또는 note 실행으로 참여자를 등록한 뒤 목표를 변경하세요.')
    profile = members[user]
    require(day >= profile['joined'], '참여 시작일 이후 날짜를 사용하세요.')
    profile['goals'] = sorted([g for g in profile['goals'] if g['from'] != day] + [{'from': day, 'daily_goal': args.count}], key=lambda g: g['from'])
    write_json(ROOT / 'members' / f'{user}.json', profile)
    for record_day in sorted({d['date'] for _, d in records() if d['user'] == user and d['date'] >= day}):
        refresh(user, record_day)
    print('목표 이력을 저장했습니다. 변경된 참여자 파일과 일일 README를 함께 커밋하세요.')


def check_all(branch=None, base=None):
    members = profiles()
    rows = records()
    # Orphaned code/notes must not silently disappear from the count.
    for path in (ROOT / 'records').rglob('*'):
        require(not path.is_symlink(), f'{path}: 심볼릭 링크는 지원하지 않습니다.')
        if path.is_file() and len(path.relative_to(ROOT / 'records').parts) >= 6:
            parts = path.relative_to(ROOT / 'records').parts
            folder = ROOT / 'records' / Path(*parts[:5])
            require((folder / 'meta.json').is_file(), f'{folder}: meta.json 누락')
    for folder, data in rows:
        validate_record(folder, data, members)
    for user, day in sorted({(d['user'], d['date']) for _, d in rows}):
        subset = [(p, d) for p, d in rows if d['user'] == user and d['date'] == day]
        index = daily_path(user, day) / 'README.md'
        require(index.is_file() and index.read_text(encoding='utf-8') == daily_markdown(user, day, subset, members),
                f'{index}: 일일 목록이 오래되었습니다. python3 study.py index --user {user} --date {day}')
    if branch and branch.startswith('study/'):
        match = re.fullmatch(r'study/([^/]+)/(\d{4}-\d{2}-\d{2})', branch)
        require(match is not None, '브랜치 형식: study/아이디/YYYY-MM-DD')
        user, day = match.groups()
        valid_user(user)
        valid_date(day)
        require(base, 'study 브랜치 검사에는 --base 커밋이 필요합니다.')
        changed = git('diff', '--name-only', '--no-renames', f'{base}...HEAD').splitlines()
        prefix = daily_path(user, day).relative_to(ROOT).as_posix() + '/'
        require(changed and all(p.startswith(prefix) or p == f'members/{user}.json' for p in changed),
                '일일 PR에는 해당 날짜/본인 기록과 본인 참여자 파일만 포함하세요. 도구 변경은 별도 브랜치를 사용하세요.')
        daily = [(p, d) for p, d in rows if d['user'] == user and d['date'] == day]
        require(daily, '일일 PR에 학습 기록이 없습니다.')
        require(all(is_complete(d) for _, d in daily), '일일 PR에 draft가 남아 있습니다. done 처리하세요.')
    return rows, members


def cmd_check(args):
    rows, _ = check_all(args.branch, args.base)
    print(f'검증 통과: {len(rows)}개 기록. 코드 실행/채점은 수행하지 않습니다.')


def cmd_index(args):
    user = valid_user(args.user) if args.user else local()['user']
    require(refresh(user, valid_date(args.date)), '해당 날짜의 기록이 없습니다.')
    print('일일 목록 갱신 완료.')


def reviewer_for(user, day, members):
    names = sorted(name for name, profile in members.items() if profile['joined'] <= day)
    if user not in names or len(names) < 2:
        return None
    offset = date.fromisoformat(day).toordinal() % (len(names) - 1) + 1
    return names[(names.index(user) + offset) % len(names)]


def repository_url():
    remote = git('remote', 'get-url', settings()['remote'])
    match = re.fullmatch(r'(?:https://github.com/|git@github.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?', remote)
    return 'https://github.com/' + match[1] if match else None


def cmd_prepare(args):
    user, day = local()['user'], valid_date(args.date)
    rows = refresh(user, day)
    require(rows, '해당 날짜의 기록이 없습니다.')
    _, members = check_all()
    require(all(is_complete(d) for _, d in rows), 'draft가 남아 있습니다. 기록 작성 완료 후 done을 실행하세요.')
    goal = goal_at(members[user], day)
    reviewer = reviewer_for(user, day, members)
    folder = daily_path(user, day).relative_to(ROOT).as_posix()
    branch = f'study/{user}/{day}'
    require(git('branch', '--show-current') == branch, f'{branch} 브랜치에서 실행하세요. 현재 브랜치의 변경을 먼저 확인하세요.')
    title = f'[{day}] {user} · {len(rows)}/{goal}건'
    repo = repository_url()
    def record_link(label, path):
        return f'[{label}]({repo}/blob/{quote(branch, safe="")}/{path})' if repo else f'{label}: `{path}`'
    lines = [f'## {title}', '', f'- 일일 기록: {record_link(day + " / " + user, folder + "/README.md")}',
             f'- 완료 / 목표: **{len(rows)} / {goal}**',
             f'- 추천 리뷰어: {reviewer or "다른 참여자 등록 후 표시됩니다"}', '',
             '| 유형 | 기록 | 코드 / 본문 |', '| --- | --- | --- |']
    for path, data in rows:
        rel = path.relative_to(ROOT).as_posix()
        target = data['solution'] if record_type(data) == 'problem' else 'README.md'
        title_link = f"[{md(data['title'])}]({data['url']})" if record_type(data) == 'problem' else record_link(md(data['title']), rel + '/README.md')
        lines.append(f"| {type_label(data)} | {title_link} | {record_link(target, rel + '/' + target)} |")
    lines += ['', '## 리뷰 요청', '', '<!-- 특히 봐줬으면 하는 문제, 정리 내용, 코드 줄을 적어주세요. -->', '']
    if any(record_type(d) == 'problem' for _, d in rows):
        lines.append('- [ ] 코딩 문제는 채점 사이트에서 정답을 확인했습니다.')
    if any(record_type(d) == 'note' for _, d in rows):
        lines.append('- [ ] 학습 정리는 주제·정리 내용·배운 점을 작성하고 내용을 확인했습니다.')
    lines += ['- [ ] 리뷰를 받고 피드백을 반영하겠습니다.', '']
    output = ROOT / '.study/PR.md'
    output.parent.mkdir(exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')
    if len(rows) < goal:
        print('목표 미달: 제출은 허용합니다. PR에 이유나 다음 계획을 적어주세요.')
    print(f'PR 본문 생성: {output.relative_to(ROOT)}')
    print(f'git add {folder} members/{user}.json')
    print(f'git commit -m "study: {day} {user}"')
    print(f'git push -u {settings()["remote"]} {branch}')
    print(f'gh pr create --base {settings()["base_branch"]} --head {branch} --title "{title}" --body-file .study/PR.md' +
          (f' --reviewer {reviewer}' if reviewer else ''))
    print('GitHub 웹에서 PR을 만들 경우 .study/PR.md 내용을 붙여넣으세요.')


def dashboard(day, days=14, repo_url=None, ref=None):
    rows, members = check_all()
    end = date.fromisoformat(valid_date(day))
    require(1 <= days <= 366, '--days는 1~366입니다.')
    counts = Counter((d['user'], d['date']) for _, d in rows if is_complete(d))
    totals = Counter(d['user'] for _, d in rows if is_complete(d) and d['date'] <= day)
    type_totals = Counter((d['user'], record_type(d)) for _, d in rows if is_complete(d) and d['date'] <= day)
    def link(path):
        return f'{repo_url.rstrip("/")}/blob/{quote(ref or settings()["base_branch"], safe="")}/{path}' if repo_url else f'../{path}'
    lines = ['# 스터디 학습 현황', '', f'기준일: **{day} (KST)** · 완료는 자기 신고', '',
             '현재 체크아웃된 기록을 집계합니다. progress 브랜치의 보고서는 main에 합쳐진 기록 기준입니다.', '',
             '목표 단위는 완료 기록 수입니다. 코딩 문제 1개 또는 학습 정리 1개를 각각 1건으로 셉니다.', '',
             '✅ 목표 달성 · 🔸 일부 완료 · — 완료 없음 · · 참여 전', '',
             '| 참여자 | 오늘 완료 / 목표 | 누적 완료 |', '| --- | --- | --- |']
    for user, profile in members.items():
        goal = goal_at(profile, day)
        lines.append(f'| {user} | {counts[user, day]} / {goal if goal else "참여 전"} | {totals[user]} |')
    if not members:
        lines += ['', '아직 등록된 참여자가 없습니다. 첫 기록을 올리면 여기에 표시됩니다.']
    if members:
        lines += ['', '## 유형별 누적 완료', '', '| 참여자 | 코딩 문제 | 학습 정리 |', '| --- | --- | --- |']
        for user in members:
            lines.append(f'| {user} | {type_totals[user, "problem"]} | {type_totals[user, "note"]} |')
    lines += ['', f'## 최근 {days}일', '']
    if members:
        names = sorted(members)
        lines += ['| 날짜 | ' + ' | '.join(names) + ' |', '| --- | ' + ' | '.join(['---'] * len(names)) + ' |']
        for offset in range(days):
            current = (end - timedelta(days=offset)).isoformat()
            cells = []
            for user in names:
                goal = goal_at(members[user], current)
                count = counts[user, current]
                cell = '·' if not goal else f'{"✅" if count >= goal else "🔸" if count else "—"} {count}/{goal}'
                if count:
                    path = daily_path(user, current).relative_to(ROOT).as_posix() + '/README.md'
                    cell = f'[{cell}]({link(path)})'
                cells.append(cell)
            lines.append('| ' + current + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', '## 문제별 모아보기', '', '| 문제 | 날짜 | 작성자 | 언어 | 코드 |', '| --- | --- | --- | --- | --- |']
    problems = [(p, d) for p, d in rows if record_type(d) == 'problem']
    for folder, data in sorted(problems, key=lambda row: (row[1]['platform'], row[1]['problem_id'], row[1]['date'], row[1]['user'])):
        if not is_complete(data) or data['date'] > day:
            continue
        path = folder.relative_to(ROOT).as_posix()
        lines.append(f"| [{md(data['title'])}]({link(path + '/README.md')}) | {data['date']} | {data['user']} | {data['language']} | [보기]({link(path + '/' + data['solution'])}) |")
    lines += ['', '## 학습 정리 모아보기', '', '| 주제 | 날짜 | 작성자 | 태그 |', '| --- | --- | --- | --- |']
    notes = [(p, d) for p, d in rows if record_type(d) == 'note']
    for folder, data in sorted(notes, key=lambda row: (row[1]['date'], row[1]['user'], row[1]['note_id']), reverse=True):
        if not is_complete(data) or data['date'] > day:
            continue
        path = folder.relative_to(ROOT).as_posix()
        lines.append(f"| [{md(data['title'])}]({link(path + '/README.md')}) | {data['date']} | {data['user']} | {md(', '.join(data['tags']))} |")
    return '\n'.join(lines) + '\n'


def cmd_report(args):
    content = dashboard(args.date, args.days, args.repo_url, args.ref)
    output = ROOT / '.study/dashboard.md'
    output.parent.mkdir(exist_ok=True)
    output.write_text(content, encoding='utf-8')
    print(content)


def cmd_help(args):
    if args.command:
        args.commands[args.command].print_help()
    else:
        args.root_parser.print_help()


def parser():
    p = argparse.ArgumentParser(description='코딩 문제·학습 정리 기록과 일일 PR 준비 (Python 3.10+, 외부 패키지 없음)')
    sub = p.add_subparsers(dest='command', required=True)
    commands = {}
    init = sub.add_parser('init', help='아이디, 기본 언어, 최초 목표를 로컬에 저장')
    commands['init'] = init
    init.add_argument('user')
    init.add_argument('--lang', choices=LANGUAGES)
    init.add_argument('--goal', type=int)
    init.set_defaults(func=cmd_init)
    start = sub.add_parser('start', help='최신 main에서 오늘 개인 브랜치 생성')
    commands['start'] = start
    start.set_defaults(func=cmd_start)
    new = sub.add_parser('new', help='문제 URL로 기록 생성')
    commands['new'] = new
    new.add_argument('url')
    new.add_argument('--title', required=True)
    new.add_argument('--lang', choices=LANGUAGES)
    new.add_argument('--source', help='기존 풀이 파일 복사')
    new.add_argument('--level', default='')
    new.add_argument('--tags', default='')
    new.set_defaults(func=cmd_new)
    note = sub.add_parser('note', help='학습 정리 템플릿 생성 (코드·문제 URL 불필요)')
    commands['note'] = note
    note.add_argument('--title', required=True)
    note.add_argument('--slug', help='폴더 식별자 (예: git-branch). 생략하면 01부터 자동 번호')
    note.add_argument('--tags', default='')
    note.add_argument('--reference', action='append', default=[], help='참고 URL (여러 번 지정 가능)')
    note.add_argument('--source', help='기존 UTF-8 Markdown/텍스트 파일을 notes.md로 복사')
    note.set_defaults(func=cmd_note)
    done = sub.add_parser('done', help='필수 설명/코드 확인 후 완료 표시')
    commands['done'] = done
    done.add_argument('target', help='문제 URL 또는 note-01 같은 학습 정리 폴더명')
    done.add_argument('--minutes', type=int)
    done.set_defaults(func=cmd_done)
    goal = sub.add_parser('goal', help='적용일별 일일 목표 변경')
    commands['goal'] = goal
    goal.add_argument('count', type=int)
    goal.add_argument('--from', dest='start', default=today())
    goal.set_defaults(func=cmd_goal)
    index = sub.add_parser('index', help='일일 목록 재생성')
    commands['index'] = index
    index.add_argument('--user')
    index.set_defaults(func=cmd_index)
    prepare = sub.add_parser('prepare', help='일일 PR 본문과 Git 명령 생성')
    commands['prepare'] = prepare
    prepare.set_defaults(func=cmd_prepare)
    check = sub.add_parser('check', help='기록 형식과 일일 목록 검증')
    commands['check'] = check
    check.add_argument('--branch')
    check.add_argument('--base')
    check.set_defaults(func=cmd_check)
    report = sub.add_parser('report', help='목표 달성 현황과 문제별 인덱스 생성')
    commands['report'] = report
    report.add_argument('--days', type=int, default=14)
    report.add_argument('--repo-url', help='GitHub 보고서의 절대 링크용 레포 URL')
    report.add_argument('--ref', help='GitHub 보고서 링크의 브랜치/커밋 (기본: main)')
    report.set_defaults(func=cmd_report)
    for command in (start, new, note, done, index, prepare, report):
        command.add_argument('--date', default=today(), help='YYYY-MM-DD (기본: 한국 날짜)')
    help_cmd = sub.add_parser('help', help='명령어 도움말 보기')
    help_cmd.add_argument('command', nargs='?', choices=tuple(commands), help='도움말을 볼 명령어')
    help_cmd.set_defaults(func=cmd_help, root_parser=p, commands=commands)
    return p


def main():
    args = parser().parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        print(f'오류: {detail}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
