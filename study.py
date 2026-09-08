#!/usr/bin/env python3
"""Dependency-free study CLI. Dates use Korea Standard Time (UTC+09:00)."""
from study_wiki.common import normalize

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from string import Template
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

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
SOLVING_METHODS = {
    'self': '스스로 해결',
    'hint': '힌트 참고',
    'answer': '답안·해설 참고',
}
UNSET = object()


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


def valid_goal(value):
    """A goal is a positive count, or None for self-directed participation."""
    if value is None:
        return None
    return positive(value)


def command_goal(value):
    """Parse the human-facing goal argument while keeping validation errors readable."""
    if isinstance(value, str) and value.lower() == 'none':
        return None
    try:
        return positive(int(value))
    except (TypeError, ValueError):
        raise ValueError('목표는 1 이상의 정수 또는 none입니다.')


def csv_values(value):
    return [item.strip() for item in value.split(',') if item.strip()]


def solving_method_label(value):
    return SOLVING_METHODS.get(value, '미입력')


def metadata_text(values):
    return ', '.join(values) if values else '미입력'


def goal_progress(done, goal):
    if goal is None:
        return f'완료 **{done}건** · 자율 기록'
    return f'완료 **{done} / {goal}** · ' + ('목표 달성 ✅' if done >= goal else '진행 중')


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
    return subprocess.run(
        ['git', *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def github_repository(remote):
    """Return (owner, repo) when the Git remote points to github.com."""
    try:
        remote_url = git('remote', 'get-url', remote).strip()
    except subprocess.CalledProcessError:
        return None

    # git@github.com:owner/repo.git
    if remote_url.startswith('git@github.com:'):
        path = remote_url.removeprefix('git@github.com:')
    else:
        # https://github.com/owner/repo.git
        # ssh://git@github.com/owner/repo.git
        parsed = urlsplit(remote_url)
        if parsed.hostname != 'github.com':
            return None
        path = parsed.path.lstrip('/')

    path = path.rstrip('/').removesuffix('.git')
    parts = path.split('/')

    if (
        len(parts) != 2
        or not all(re.fullmatch(r'[A-Za-z0-9_.-]+', part) for part in parts)
    ):
        return None

    return tuple(parts)


def github_api_json(url):
    """Read JSON from the GitHub API.

    API/network failures return None so branch cleanup always fails safe.
    """
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'codingtest-2026-study-cli',
        'X-GitHub-Api-Version': '2022-11-28',
    }

    # Optional. Public repositories also work without a token.
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    request = Request(url, headers=headers)

    try:
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except (OSError, ValueError):
        # Network failure, rate limit, invalid JSON, etc.
        # Never force-delete a branch when verification is unavailable.
        return None


def github_merged_pr(repository, base_branch, branch, tip):
    """Return the merged PR proving that this exact local branch tip was merged.

    Returns:
      dict  -> exact merged PR found
      False -> GitHub responded, but no matching merged PR exists
      None  -> GitHub verification was unavailable
    """
    if repository is None:
        return None

    owner, repo = repository

    url = (
        f'https://api.github.com/repos/'
        f'{quote(owner, safe="")}/{quote(repo, safe="")}'
        f'/commits/{quote(tip, safe="")}/pulls'
    )

    pull_requests = github_api_json(url)

    if not isinstance(pull_requests, list):
        return None

    for pr in pull_requests:
        head = pr.get('head') or {}
        base = pr.get('base') or {}

        # All four conditions must match.
        #
        # 1. The PR was actually merged.
        # 2. It was merged into the expected base branch.
        # 3. The PR's original branch name matches this local branch.
        # 4. The PR's exact head commit still matches this local branch tip.
        #
        # Condition 4 is particularly important:
        # if a user added commits locally after the PR was merged,
        # the branch must NOT be deleted.
        if (
            pr.get('merged_at')
            and base.get('ref') == base_branch
            and head.get('ref') == branch
            and head.get('sha') == tip
        ):
            return pr

    return False


def cleanup_merged_branches(remote, base_branch, protected_branches=()):
    """Update base and safely remove locally completed branches.

    Normal merge:
        Git can prove ancestry -> git branch -d

    Squash / rebase merge:
        GitHub must prove that the exact local tip was the head of a merged PR
        -> git branch -D
    """
    require(
        not git('status', '--porcelain'),
        '미커밋 변경이 있어 브랜치 정리를 중단합니다. '
        '먼저 커밋하거나 별도로 보관하세요.',
    )

    if git('branch', '--show-current') != base_branch:
        git('switch', base_branch)

    git('fetch', '--prune', remote)
    git('pull', '--ff-only', remote, base_branch)

    local_branches = [
        branch.strip()
        for branch in git(
            'branch',
            '--format=%(refname:short)',
        ).splitlines()
        if branch.strip()
    ]

    merged_branches = {
        branch.strip()
        for branch in git(
            'branch',
            '--merged',
            base_branch,
            '--format=%(refname:short)',
        ).splitlines()
        if branch.strip()
    }

    repository = github_repository(remote)

    # If the remote is GitHub, branches that Git cannot identify as merged
    # may still have been squash/rebase merged.
    github_check_available = repository is not None
    github_check_failed = False

    deleted = []
    deleted_labels = []

    for branch in local_branches:
        if (
            branch == base_branch
            or branch in protected_branches
        ):
            continue

        # Case 1: normal merge.
        #
        # Git itself can prove that the branch tip is already reachable
        # from main, so ordinary safe deletion (-d) is sufficient.
        if branch in merged_branches:
            try:
                git('branch', '-d', branch)
            except subprocess.CalledProcessError:
                # For example, the branch may be checked out
                # in another worktree.
                continue

            deleted.append(branch)
            deleted_labels.append(branch)
            continue

        # Case 2: squash/rebase merge.
        #
        # The commit graph alone cannot prove the merge, so require
        # GitHub to confirm the exact branch name + exact tip SHA.
        if not github_check_available:
            continue

        tip = git('rev-parse', f'refs/heads/{branch}')

        pr = github_merged_pr(
            repository,
            base_branch,
            branch,
            tip,
        )

        if pr is None:
            # Stop using the API for the remainder of this cleanup run.
            # Nothing is force-deleted when verification is uncertain.
            github_check_available = False
            github_check_failed = True
            continue

        if not pr:
            continue

        try:
            # Git cannot prove ancestry after squash/rebase,
            # but GitHub has proved that this exact tip was merged.
            git('branch', '-D', branch)
        except subprocess.CalledProcessError:
            # Keep worktree-in-use branches and any other branch
            # Git refuses to delete.
            continue

        deleted.append(branch)

        number = pr.get('number')
        if isinstance(number, int):
            deleted_labels.append(
                f'{branch} (GitHub PR #{number} 확인)'
            )
        else:
            deleted_labels.append(
                f'{branch} (GitHub PR 병합 확인)'
            )

    if deleted:
        print(
            '병합 완료 로컬 브랜치 정리: '
            + ', '.join(deleted_labels)
        )
    else:
        print('삭제할 병합 완료 로컬 브랜치가 없습니다.')

    if github_check_failed:
        print(
            'GitHub PR 병합 여부를 확인하지 못해 '
            'Git이 병합으로 판단하지 않는 브랜치는 보존했습니다.'
        )

    return deleted


def daily_path(user, day):
    return ROOT / 'records' / day.replace('-', '/') / user


def is_allowed_daily_pr_path(path, user, day):
    p = PurePosixPath(path)
    if p.is_absolute() or any(part in ('', '.', '..') for part in p.parts):
        return False
    parts = p.parts

    # 1. 본인 참여자 파일: members/<user>.json
    if parts == ('members', f'{user}.json'):
        return True

    # 2. 해당 날짜 본인 기록 전체: records/YYYY/MM/DD/<user>/**
    prefix_parts = daily_path(user, day).relative_to(ROOT).parts
    if len(parts) > len(prefix_parts) and parts[:len(prefix_parts)] == prefix_parts:
        return True

    # 3. 본인의 다른 날짜 기록 중 meta.json만: records/YYYY/MM/DD/<user>/<record>/meta.json
    if len(parts) == 7:
        if (parts[0] == 'records' and
            parts[4] == user and
            parts[6] == 'meta.json'):
            y, m, d = parts[1], parts[2], parts[3]
            if not (re.fullmatch(r'\d{4}', y) and re.fullmatch(r'\d{2}', m) and re.fullmatch(r'\d{2}', d)):
                return False
            try:
                valid_date(f'{y}-{m}-{d}')
            except (ValueError, TypeError):
                return False
            record = parts[5]
            if not re.fullmatch(r'[A-Za-z0-9._-]+', record) or record in ('.', '..'):
                return False
            return True

    return False


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
    elif host in ('codetree.ai', 'www.codetree.ai'):
        # CodeTree currently exposes both localized frequent-problem URLs and
        # the older training-field URL shape. Keep the category in the URL,
        # while using the stable problem slug as the record identifier.
        patterns = (
            r'/(?:ko|en)/frequent-problems/(?:[^/]+/)?problems/([a-z0-9-]+)(?:/[^/]*)?',
            r'/training-field/frequent-problems/(?:[^/]+/)?problems/([a-z0-9-]+)(?:/[^/]*)?',
        )
        match = next(
            (match for pattern in patterns if (match := re.fullmatch(pattern, path))),
            None,
        )
        require(match is not None, '지원하는 CodeTree 문제 URL 형식을 확인하세요.')
        platform, pid, host = 'codetree', match[1], 'www.codetree.ai'
    else:
        raise ValueError('지원 링크: 프로그래머스, 백준, LeetCode, CodeTree 문제 URL')
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
            valid_goal(item['daily_goal'])
        require(days == sorted(set(days)) and days[0] == data['joined'], f'{path}: 목표 적용일 순서/시작일을 확인하세요.')
        daily_goals = data.get('daily_goals', [])
        require(isinstance(daily_goals, list), f'{path}: daily_goals는 배열입니다.')
        override_days = []
        for item in daily_goals:
            require(isinstance(item, dict), f'{path}: daily_goals 항목은 객체입니다.')
            override_day = valid_date(item.get('date'))
            require(override_day >= data['joined'], f'{path}: 일일 목표 날짜는 참여 시작일 이후여야 합니다.')
            override_days.append(override_day)
            valid_goal(item.get('daily_goal'))
        require(override_days == sorted(set(override_days)), f'{path}: 일일 목표 날짜 순서/중복을 확인하세요.')
        result[user] = data
    return result


def goal_at(profile, day):
    for item in profile.get('daily_goals', []):
        if item['date'] == day:
            return item['daily_goal']
    goals = [item['daily_goal'] for item in profile['goals'] if item['from'] <= day]
    return goals[-1] if goals else None


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
    require(day >= members[user]['joined'], f'{folder}: 참여 시작일 전 기록입니다.')
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
        require(isinstance(data.get('level', ''), str), f'{folder}: level은 문자열입니다.')
        solve_method = data.get('solve_method', '')
        require(solve_method in ('', *SOLVING_METHODS), f'{folder}: solve_method가 올바르지 않습니다.')
        for field in ('data_structures', 'algorithms'):
            values = data.get(field, [])
            require(isinstance(values, list) and all(isinstance(value, str) and value.strip() for value in values),
                    f'{folder}: {field}는 비어 있지 않은 문자열 배열입니다.')
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
        lines = [f'# {day} · {user}', '', goal_progress(done, goal), '',
                 f'코딩 문제 {counts["problem"]}건 · 학습 정리 {counts["note"]}건 (완료 기록 1개 = 목표 1건)', '',
                 '<!-- study.py 자동 생성: 각 기록의 README를 수정하세요. -->', '',
                 '| 유형 | 기록 | 상태 | 코드 / 본문 |', '| --- | --- | --- | --- |']
        for folder, data in rows:
            target = data['solution'] if record_type(data) == 'problem' else 'README.md'
            lines.append(f"| {type_label(data)} | [{md(data['title'])}]({folder.name}/README.md) | {data['status']} | [보기]({folder.name}/{target}) |")
        return '\n'.join(lines) + '\n'
    # Preserve existing problem-only indexes so old records need no migration.
    lines = [f'# {day} · {user}', '', goal_progress(done, goal), '',
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
    goal = valid_goal(config['default_daily_goal']) if args.goal is UNSET else command_goal(args.goal)
    write_json(ROOT / '.study/config.json', {'user': user, 'language': args.lang or config['default_language'],
                                          'daily_goal': goal})
    print(f'{user} 로컬 설정 완료. 첫 new 또는 note 실행 시 참여자 파일을 생성합니다. start --goal로 오늘 목표를 정할 수도 있습니다.')


def cmd_start(args):
    local_config = local()
    user = local_config['user']
    day = valid_date(args.date)
    config = settings()
    requested_goal = command_goal(args.goal) if args.goal is not UNSET else UNSET
    members = profiles()
    profile = members.get(user)
    if profile is not None:
        require(day >= profile['joined'], '참여 시작일 전입니다. members 파일의 시작일을 먼저 조정하세요.')
    require(not git('status', '--porcelain'), '미커밋 변경이 있습니다. 먼저 커밋하거나 별도로 보관하세요.')
    branch = f'study/{user}/{day}'
    cleanup_merged_branches(config['remote'], config['base_branch'], {branch})
    git('switch', '--no-track', '-c', branch, f"{config['remote']}/{config['base_branch']}")
    if requested_goal is not UNSET:
        today_goal = requested_goal
        if profile is None:
            profile = {'user': user, 'joined': day,
                       'goals': [{'from': day, 'daily_goal': valid_goal(local_config['daily_goal'])}]}
        overrides = [item for item in profile.get('daily_goals', []) if item['date'] != day]
        profile['daily_goals'] = sorted(overrides + [{'date': day, 'daily_goal': today_goal}], key=lambda item: item['date'])
        write_json(ROOT / 'members' / f'{user}.json', profile)
    else:
        today_goal = goal_at(profile, day) if profile else valid_goal(local_config['daily_goal'])
    goal_text = '자율 기록' if today_goal is None else f'{today_goal}건'
    print(f'{branch} 생성 완료. 최신 {config["base_branch"]}에서 시작했습니다. 오늘 목표: {goal_text}')


def cmd_cleanup_merged_branches(args):
    cleanup_merged_branches(args.remote, args.base)


def member_for_new_record(config, day):
    user = config['user']
    members = profiles()
    if user not in members:
        profile = {'user': user, 'joined': day, 'goals': [{'from': day, 'daily_goal': valid_goal(config['daily_goal'])}]}
    else:
        profile = members[user]
        require(day >= profile['joined'], '참여 시작일 전입니다. members 파일의 시작일을 먼저 조정하세요.')
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
            'level': args.level, 'solve_method': args.solve_method,
            'data_structures': normalize(csv_values(args.data_structures), 'data_structures'), 'algorithms': normalize(csv_values(args.algorithms), 'algorithms'),
            'tags': normalize(csv_values(args.tags), 'tags'), 'minutes': None}
    content = Template((ROOT / 'templates/problem.md').read_text(encoding='utf-8')).substitute(
        **data, level_text=data['level'] or '미입력', solve_method_text=solving_method_label(data['solve_method']),
        data_structures_text=metadata_text(data['data_structures']), algorithms_text=metadata_text(data['algorithms']))
    folder.mkdir(parents=True)
    write_json(ROOT / 'members' / f'{user}.json', profile)
    write_json(folder / 'meta.json', data)
    (folder / 'README.md').write_text(content, encoding='utf-8')
    (folder / filename).write_text(code, encoding='utf-8')
    refresh(user, day)
    print(folder.relative_to(ROOT).as_posix())
    print(f'코드와 README의 3개 TODO를 작성한 뒤 python3 study.py done {folder.name} --date {day} 를 실행하세요.')


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
            'status': 'draft', 'tags': normalize(csv_values(args.tags), 'tags'),
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


def done_candidates(rows):
    return ', '.join(f'{folder.name} ({data["title"]})' for folder, data in rows)


def resolve_done_target(user, day, target):
    """Resolve a URL, record folder, numeric problem ID, or the only draft record."""
    rows = [(folder, data) for folder, data in records() if data['user'] == user and data['date'] == day]
    if target is None:
        drafts = [(folder, data) for folder, data in rows if not is_complete(data)]
        require(drafts, '작성 중인 기록이 없습니다. 완료한 기록의 시간만 바꾸려면 폴더명·문제 번호·URL을 지정하세요.')
        require(len(drafts) == 1,
                f'작성 중 기록이 여러 개입니다: {done_candidates(drafts)}. 폴더명 또는 문제 번호를 지정하세요.')
        return drafts[0]
    exact = [(folder, data) for folder, data in rows if folder.name == target]
    if exact:
        return exact[0]
    if target.isdecimal():
        matches = [(folder, data) for folder, data in rows
                   if record_type(data) == 'problem' and data['problem_id'] == target]
        require(matches, f'문제 번호 {target}의 오늘 기록을 찾을 수 없습니다.')
        require(len(matches) == 1,
                f'문제 번호 {target}과 일치하는 기록이 여러 개입니다: {done_candidates(matches)}. 폴더명을 지정하세요.')
        return matches[0]
    if target.startswith(('http://', 'https://')):
        platform, pid, _ = identify(target)
        folder = daily_path(user, day) / f'{platform}-{pid}'
        require((folder / 'meta.json').is_file(), f'해당 날짜의 기록을 찾을 수 없습니다: {folder.name}')
        return folder, read_json(folder / 'meta.json')
    raise ValueError('완료 대상은 생략(작성 중 기록 1개), 문제 번호, 기록 폴더명 또는 문제 URL입니다.')


def draft_records(user, day):
    return [(folder, data) for folder, data in records()
            if data['user'] == user and data['date'] == day and not is_complete(data)]


def sync_problem_metadata(folder, data):
    block = '\n'.join([
        '## 풀이 정보', '',
        f'- 난이도: {data.get("level") or "미입력"}',
        f'- 풀이 방식: {solving_method_label(data.get("solve_method", ""))}',
        f'- 자료구조: {metadata_text(data.get("data_structures", []))}',
        f'- 알고리즘: {metadata_text(data.get("algorithms", []))}', '',
    ])
    path = folder / 'README.md'
    content = path.read_text(encoding='utf-8')
    if re.search(r'^## 풀이 정보\s*$', content, flags=re.M):
        content = re.sub(r'^## 풀이 정보\s*.*?(?=^## |\Z)', block, content, count=1, flags=re.M | re.S)
    else:
        require(re.search(r'^## 문제\s*$', content, flags=re.M), f'{folder}: 문제 항목을 찾을 수 없습니다.')
        content = re.sub(r'^## 문제\s*$', block + '\n## 문제', content, count=1, flags=re.M)
    path.write_text(content, encoding='utf-8')


def cmd_done(args):
    user, day = local()['user'], valid_date(args.date)
    require(not (args.all and args.target is not None), '--all은 완료 대상을 함께 지정할 수 없습니다.')
    metadata_changed = any(value is not None for value in
                           (args.level, args.solve_method, args.data_structures, args.algorithms))
    require(not (args.all and (args.minutes is not None or metadata_changed)),
            '--all에는 --minutes, 난이도, 풀이 방식, 자료구조, 알고리즘 옵션을 함께 사용할 수 없습니다.')
    if args.all:
        targets = draft_records(user, day)
        require(targets, '작성 중인 기록이 없습니다.')
    else:
        targets = [resolve_done_target(user, day, args.target)]

    # Complete every target only after all validation succeeds, so --all never
    # leaves a mixture of completed and draft records.
    for folder, data in targets:
        validate_record(folder, data, profiles(), completed=True)

    for folder, data in targets:
        if args.level is not None:
            data['level'] = args.level
        if args.solve_method is not None:
            data['solve_method'] = args.solve_method
        if args.data_structures is not None:
            data['data_structures'] = normalize(csv_values(args.data_structures), 'data_structures')
        if args.algorithms is not None:
            data['algorithms'] = normalize(csv_values(args.algorithms), 'algorithms')
        data['status'] = 'completed' if record_type(data) == 'note' else 'solved'
        if args.minutes is not None:
            data['minutes'] = args.minutes
        write_json(folder / 'meta.json', data)
        if metadata_changed and record_type(data) == 'problem':
            sync_problem_metadata(folder, data)
    refresh(user, day)
    if args.all:
        print(f'{len(targets)}건 완료 처리. 코딩 문제의 채점 결과는 본인이 확인한 것으로 기록합니다.')
        return

    folder, data = targets[0]
    message = '학습 정리를 완료 처리했습니다.' if record_type(data) == 'note' else '채점 결과는 본인이 확인한 것으로 기록합니다.'
    print(f'{folder.name} 완료 처리. {message}')


def cmd_goal(args):
    config = local()
    user = config['user']
    goal = command_goal(args.count)
    members = profiles()
    if args.day is not None:
        day = valid_date(args.day)
        profile = members.get(user)
        if profile is None:
            profile = {'user': user, 'joined': day,
                       'goals': [{'from': day, 'daily_goal': valid_goal(config['daily_goal'])}]}
        else:
            require(day >= profile['joined'], '참여 시작일 전입니다. members 파일의 시작일을 먼저 조정하세요.')
        overrides = [item for item in profile.get('daily_goals', []) if item['date'] != day]
        profile['daily_goals'] = sorted(overrides + [{'date': day, 'daily_goal': goal}], key=lambda item: item['date'])
        write_json(ROOT / 'members' / f'{user}.json', profile)
        if any(d['user'] == user and d['date'] == day for _, d in records()):
            refresh(user, day)
        print(f'{day} 하루 목표를 변경했습니다. 변경된 참여자 파일과 일일 README를 함께 커밋하세요.')
        return
    day = valid_date(args.start or today())
    require(user in members, '첫 new 또는 note 실행으로 참여자를 등록한 뒤 목표를 변경하세요.')
    profile = members[user]
    require(day >= profile['joined'], '참여 시작일 이후 날짜를 사용하세요.')
    profile['goals'] = sorted([g for g in profile['goals'] if g['from'] != day] + [{'from': day, 'daily_goal': goal}], key=lambda g: g['from'])
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
        require(changed and all(is_allowed_daily_pr_path(p, user, day) for p in changed),
                '일일 PR에는 해당 날짜 본인 기록, 본인 참여자 파일, 본인 기존 기록의 meta.json만 포함할 수 있습니다.')
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


def cmd_status(args):
    """Show the selected day's progress without requiring completed records."""
    config = local()
    user, day = config['user'], valid_date(args.date)
    members = profiles()
    profile = members.get(user)
    goal = goal_at(profile, day) if profile and day >= profile['joined'] else valid_goal(config['daily_goal'])
    rows = [(path, data) for path, data in records() if data['user'] == user and data['date'] == day]
    done = sum(is_complete(data) for _, data in rows)
    drafts = [(path, data) for path, data in rows if not is_complete(data)]
    expected_branch = f'study/{user}/{day}'
    current_branch = git('branch', '--show-current')
    dirty = git('status', '--porcelain').splitlines()
    goal_text = f'완료 {done}건 · 자율 기록' if goal is None else f'완료 {done} / {goal}'
    lines = [f'[{day}] {user} 진행 상태', '', f'- 현재 브랜치: {current_branch}',
             f'- 작업 브랜치: {expected_branch}',
             f'- 작업 트리: {"깨끗함" if not dirty else f"변경 {len(dirty)}개"}',
             f'- 목표: {goal_text}']
    if not rows:
        lines.append('- 기록: 아직 없습니다.')
    else:
        lines.append(f'- 기록: 완료 {done}건 · 작성 중 {len(drafts)}건')
        for folder, data in rows:
            state = '완료' if is_complete(data) else '작성 중'
            lines.append(f'  - {state}: {type_label(data)} · {data["title"]} ({folder.name})')
    if current_branch != expected_branch:
        if dirty:
            next_step = '현재 브랜치의 미커밋 변경을 먼저 commit하거나 정리한 뒤 작업 브랜치로 전환하세요.'
        elif git('branch', '--list', expected_branch):
            next_step = f'git switch {expected_branch}'
        elif git('branch', '--remotes', '--list', f'{settings()["remote"]}/{expected_branch}'):
            next_step = f'git switch --track -c {expected_branch} {settings()["remote"]}/{expected_branch}'
        else:
            next_step = f'python3 study.py start --date {day}'
        lines += ['', f'다음: {next_step}']
    elif not rows:
        lines += ['', f'다음: python3 study.py new 문제URL --title "문제 제목" --date {day}',
                  f'또는 python3 study.py note --title "학습 주제" --date {day}']
    elif drafts:
        folder, data = drafts[0]
        target = folder.name
        lines += ['', f'다음: README와 코드를 작성한 뒤 python3 study.py done {target} --date {day}']
        if len(drafts) > 1:
            lines.append(f'모든 기록의 완료를 확인했다면: python3 study.py done --all --date {day}')
    else:
        lines += ['', f'다음: python3 study.py prepare --date {day}']
    print('\n'.join(lines))


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
    title = f'[{day}] {user} · {len(rows)}' + ('건 (자율)' if goal is None else f'/{goal}건')
    repo = repository_url()
    def record_link(label, path):
        return f'[{label}]({repo}/blob/{quote(branch, safe="")}/{path})' if repo else f'{label}: `{path}`'
    lines = [f'## {title}', '', f'- 일일 기록: {record_link(day + " / " + user, folder + "/README.md")}',
             f'- 완료 / 목표: **{len(rows)}건 / 자율**' if goal is None else f'- 완료 / 목표: **{len(rows)} / {goal}**',
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
    if goal is not None and len(rows) < goal:
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
             '목표 단위는 완료 기록 수입니다. 코딩 문제 1개 또는 학습 정리 1개를 각각 1건으로 셉니다. 자율 참여자는 완료 건수만 표시합니다.', '',
             '✅ 목표 달성 · 🔸 일부 완료 · — 완료 없음 · 자율 자율 기록 · · 참여 전', '',
             '| 참여자 | 오늘 완료 / 목표 | 누적 완료 |', '| --- | --- | --- |']
    for user, profile in members.items():
        goal = goal_at(profile, day)
        current = '참여 전' if day < profile['joined'] else f'{counts[user, day]}건 / 자율' if goal is None else f'{counts[user, day]} / {goal}'
        lines.append(f'| {user} | {current} | {totals[user]} |')
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
                cell = '·' if current < members[user]['joined'] else f'자율 {count}건' if goal is None else f'{"✅" if count >= goal else "🔸" if count else "—"} {count}/{goal}'
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
    init.add_argument('--goal', default=UNSET, metavar='건수|none', help='일일 목표. none이면 자율 기록')
    init.set_defaults(func=cmd_init)
    cleanup = sub.add_parser('cleanup-merged-branches', help='main에 병합된 로컬 브랜치 안전하게 정리')
    commands['cleanup-merged-branches'] = cleanup
    cleanup.add_argument('remote', nargs='?', default='origin')
    cleanup.add_argument('base', nargs='?', default='main')
    cleanup.set_defaults(func=cmd_cleanup_merged_branches)
    start = sub.add_parser('start', help='최신 main에서 오늘 개인 브랜치 생성 (선택: 오늘 목표)')
    commands['start'] = start
    start.add_argument('--goal', default=UNSET, metavar='건수|none', help='이 날짜에만 적용할 목표. 생략하면 init/goal의 기본 목표 사용')
    start.set_defaults(func=cmd_start)
    new = sub.add_parser('new', help='문제 URL로 기록 생성')
    commands['new'] = new
    new.add_argument('url')
    new.add_argument('--title', required=True)
    new.add_argument('--lang', choices=LANGUAGES)
    new.add_argument('--source', help='기존 풀이 파일 복사')
    new.add_argument('--level', '--difficulty', dest='level', default='', help='난이도')
    new.add_argument('--solve-method', '--method', choices=SOLVING_METHODS, default='',
                     help='풀이 방식: self(스스로), hint(힌트), answer(답안·해설)')
    new.add_argument('--data-structures', '--structures', default='', help='사용한 자료구조 (쉼표로 구분)')
    new.add_argument('--algorithms', default='', help='사용한 알고리즘 (쉼표로 구분)')
    new.add_argument('--tags', default='', help='쉼표 구분. 핵심 분류 별칭은 통합하고, 그 외 표현은 Wiki 검색어로 보존')
    new.set_defaults(func=cmd_new)
    note = sub.add_parser('note', help='학습 정리 템플릿 생성 (코드·문제 URL 불필요)')
    commands['note'] = note
    note.add_argument('--title', required=True)
    note.add_argument('--slug', help='폴더 식별자 (예: git-branch). 생략하면 01부터 자동 번호')
    note.add_argument('--tags', default='', help='쉼표 구분. 핵심 분류 별칭은 통합하고, 그 외 표현은 Wiki 검색어로 보존')
    note.add_argument('--reference', action='append', default=[], help='참고 URL (여러 번 지정 가능)')
    note.add_argument('--source', help='기존 UTF-8 Markdown/텍스트 파일을 notes.md로 복사')
    note.set_defaults(func=cmd_note)
    done = sub.add_parser('done', help='필수 설명/코드 확인 후 완료 표시')
    commands['done'] = done
    done.add_argument('target', nargs='?', help='생략, 문제 번호, programmers-12345 같은 폴더명 또는 문제 URL')
    done.add_argument('--all', action='store_true', help='해당 날짜의 작성 중 기록을 모두 완료 처리')
    done.add_argument('--minutes', type=int)
    done.add_argument('--level', '--difficulty', dest='level', help='난이도 덮어쓰기')
    done.add_argument('--solve-method', '--method', choices=SOLVING_METHODS, help='풀이 방식 덮어쓰기')
    done.add_argument('--data-structures', '--structures', help='사용한 자료구조 덮어쓰기 (쉼표로 구분)')
    done.add_argument('--algorithms', help='사용한 알고리즘 덮어쓰기 (쉼표로 구분)')
    done.set_defaults(func=cmd_done)
    goal = sub.add_parser('goal', help='기본 목표 또는 특정 하루의 목표 변경 (none: 자율 기록)')
    commands['goal'] = goal
    goal.add_argument('count', metavar='건수|none', help='1 이상의 목표 건수 또는 none')
    goal_target = goal.add_mutually_exclusive_group()
    goal_target.add_argument('--from', dest='start', help='이 날짜 이후의 기본 목표 변경')
    goal_target.add_argument('--date', dest='day', help='이 날짜에만 적용할 목표 변경')
    goal.set_defaults(func=cmd_goal)
    index = sub.add_parser('index', help='일일 목록 재생성')
    commands['index'] = index
    index.add_argument('--user')
    index.set_defaults(func=cmd_index)
    status = sub.add_parser('status', help='현재 날짜의 진행 상태와 다음 단계 보기')
    commands['status'] = status
    status.set_defaults(func=cmd_status)
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
    for command in (start, new, note, done, index, status, prepare, report):
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
