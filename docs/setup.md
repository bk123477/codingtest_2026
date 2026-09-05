# 운영자: GitHub에 처음 적용하기

현재 작업 결과는 로컬 파일입니다. 아래 원격 설정은 아직 적용되지 않았습니다.
기존 원격 주소는 `https://github.com/bk123477/codingtest_2026.git`입니다.

## 1. 구성을 main에 올리기

현재 변경 내용을 확인하고 GitHub에 올립니다. 최초 구성 이후부터 참여자의 일일 브랜치를 사용합니다.

```bash
python3 -m unittest discover -s tests -v
python3 study.py check
git add README.md CONTRIBUTING.md study.py study.json .gitignore .gitattributes .github scripts templates tests docs examples records members
git commit -m "Set up coding study workflow and automation"
git push origin main
```

main이 이미 보호되어 있다면 먼저 `git switch -c chore/study-setup`으로 옮겨 커밋하고,
그 브랜치를 push해 설정 PR로 merge합니다.

## 2. 팀원 초대와 기본 규칙

GitHub **Settings → Collaborators**에서 팀원에게 쓰기 권한을 부여합니다.
각자 `init`으로 자신의 아이디·언어·최초 목표를 설정합니다. 첫 풀이 PR에 등록 파일이 포함됩니다.
시작 전에 특정 날짜부터 4명 전원을 현황에 표시하려면 운영자가 아래 형식으로
`members/실제아이디.json`을 만들어 등록 PR로 추가해도 됩니다.

```json
{
  "user": "실제아이디를-소문자-영문으로",
  "joined": "2026-09-05",
  "goals": [{"from": "2026-09-05", "daily_goal": 5}]
}
```

예시의 user 값을 실제 GitHub 아이디로 바꾸세요. JSON 파일명과 user 값은 같아야 합니다.
공용 프로필이 이미 있으면 로컬 `init --goal`보다 공용 프로필의 목표 이력이 우선합니다.

## 3. Actions 실행 확인

**Actions → Study validation**에서 `study-check`가 성공했는지 확인합니다.
**Actions → Study progress**가 성공하면 `progress` 브랜치가 생성되고 README의 학습 현황 링크가 열립니다.
필요하면 **Run workflow**로 수동 갱신할 수 있습니다.

기본 `GITHUB_TOKEN`만 사용하며 별도 PAT를 등록할 필요는 없습니다.
보고서 workflow는 `contents: write`를 요청합니다. 조직 정책이 이를 제한하거나
모든 브랜치 생성/쓰기를 막으면 운영자가 해당 정책에서 progress 브랜치 쓰기를 허용해야 합니다.
`progress`는 자동 생성 파일 전용입니다. 보호 규칙은 우선 main만 대상으로 설정하세요.
수동으로 progress README를 수정하면 다음 갱신에서 생성된 내용으로 대체됩니다.

예약 실행은 한국 시간 00:15이며 지연될 수 있습니다. 비활성 레포의 예약 실행이 중지되면
Actions 화면에서 다시 활성화하거나 수동 실행하세요. main push 시에도 갱신됩니다.

## 4. main 보호 설정

첫 workflow가 실행되어 검사 이름이 표시된 뒤, **Settings → Rules → Rulesets** 또는
**Settings → Branches**에서 main 대상 보호 규칙을 추가합니다.

- PR을 통해서만 merge하도록 설정합니다.
- 승인 최소 1명을 요구합니다. 본인 승인은 동료 리뷰를 대체하지 못합니다.
- 새 커밋 후 이전 승인을 무효화하도록 설정합니다.
- `study-check` 상태 검사 통과를 요구합니다.
- 리뷰 대화를 해결한 뒤 merge하도록 설정합니다.
- force push와 브랜치 삭제를 허용하지 않습니다.

저장소 **Settings → General → Pull Requests**에서 Squash merge와 merge 후 브랜치 자동 삭제를 권장합니다.
운영자도 가급적 같은 PR 흐름을 사용합니다. main 보호 기능의 사용 가능 범위는 저장소 공개 여부와 플랜에 따라 다릅니다.
[GitHub 공식 문서](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

일일 브랜치 검사는 교육용 규칙이며 사용자 인증 수단은 아닙니다.
작성자의 GitHub 계정과 폴더 소유자를 강제로 매핑하지 않으며, 운영·도구 변경 PR은 일반 리뷰로 확인합니다.
공용 레포에는 신뢰하는 팀원을 초대하고 CI 변경도 리뷰하세요.

## 5. 다른 스터디에서 재사용

Settings → General에서 **Template repository**를 켜면 다른 사람이 **Use this template**으로
새 레포를 만들 수 있습니다. 이 설정은 GitHub 관리자 권한이 필요하며 파일만으로 활성화되지는 않습니다.
기존 공부 기록까지 복사하고 싶지 않다면 새 저장소에서 `records/`와 `members/`의 실제 데이터만 정리합니다.
README·템플릿·스크립트는 유지하고 GitHub 주소를 새 레포에 맞춥니다.

[공식 설정 안내](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
