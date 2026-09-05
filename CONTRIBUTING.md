# 참여 안내

## 첫 참여

운영자에게 collaborator 초대를 받아 공용 레포를 clone하는 흐름을 기본으로 합니다.
README의 `init → start → new → done → prepare` 순서로 진행하세요.
처음 제출할 때 자동 생성된 `members/아이디.json`을 빠뜨리지 마세요.
Git 사용자 설정도 처음 한 번 필요합니다.

```bash
git config user.name "이름"
git config user.email "GitHub에 등록한 이메일 또는 GitHub noreply 이메일"
```

본인 문제 폴더 안에서 테스트 파일, 입력 예제, 다른 풀이 파일을 추가해도 됩니다.
`meta.json`의 `solution`은 해당 언어의 기본 코드 파일을 가리키도록 유지합니다.
Java 백준 문제에서 `public class Main`을 실행할 경우 로컬에서 `Main.java`로 복사해 테스트하거나,
제출 코드를 사이트 편집기에 붙여넣으세요. 기록의 기본 파일명은 `Solution.java`입니다.

## 하루 하나의 PR

- 브랜치: `study/아이디/YYYY-MM-DD`
- 포함 범위: 그날 본인의 문제 폴더·일일 README·본인 참여자 파일
- 제출 시 모든 문제는 `solved`여야 합니다. 미완성 문제는 완료 후 제출하거나 따로 보관하세요.
- 제목·본문은 `python3 study.py prepare`로 생성합니다.
- 목표 미달은 제출 실패가 아닙니다. 부족한 이유나 다음 계획을 짧게 덧붙이세요.
- 도구·공용 문서 수정은 `chore/설명` 같은 별도 브랜치에서 제출합니다.

첫 Git 연습에서는 생성된 Git 명령을 직접 실행하고 각각의 의미를 확인하세요.
`prepare`는 push나 PR 생성을 실행하지 않습니다. PR 생성과 리뷰 제출을 직접 경험하도록 남겼습니다.

```bash
git status                         # 바뀐 파일 확인
git diff                           # 수정 내용 확인
git add records/YYYY/MM/DD/아이디 members/아이디.json
git commit -m "study: YYYY-MM-DD 아이디"
git push -u origin study/아이디/YYYY-MM-DD
```

GitHub CLI를 선택했다면 미리 설치하고 `gh auth login`을 실행합니다.
이미 PR이 있으면 새 PR을 만들 필요 없이 같은 브랜치에 추가 커밋을 push하세요.
웹에서 PR을 만들 때도 오른쪽 Reviewers에서 추천 리뷰어를 지정할 수 있습니다.
PR 본문의 코드 링크는 작업 브랜치를 가리킵니다. merge 후 브랜치를 삭제했다면
PR의 Files changed 또는 학습 현황의 main 링크를 통해 코드를 확인하세요.

## 서로 리뷰하는 방법

4명 기준으로 하루에 각자 한 사람의 일일 PR을 맡습니다. `prepare`의 추천은 날짜에 따라 순환하며,
모든 참여자가 등록된 상태에서는 자신을 제외한 사람에게 고르게 배정됩니다.
추천은 로컬에 반영된 참여자 목록 기준입니다. 첫 참여일이나 인원이 바뀐 날에는 직접 조정할 수 있습니다.

1. **Files changed**에서 코드 파일을 열고 이해가 안 되는 줄에 질문을 남깁니다.
2. 5문제 모두 간단히 읽고, 1~2문제에 경계 조건·복잡도·대안 풀이를 중심으로 의견을 남깁니다.
3. 리뷰가 끝나면 **Review changes → Submit review**를 눌러 제출합니다. 임시 댓글 상태로 두지 않습니다.
4. 필수 수정은 **Request changes**, 통과는 **Approve**, 단순 질문은 **Comment**를 사용합니다.
5. 작성자가 답변·수정 커밋을 push한 뒤 리뷰어가 확인하고 대화를 해결합니다.
6. 승인과 `study-check` 통과 후 작성자 또는 운영자가 **Squash and merge**합니다.

좋은 리뷰 예: “citations가 전부 0일 때 반환값이 0인가요?”, “정렬로 O(n log n)인데 n 범위에서는 충분하네요.”
표현 취향에 대한 제안은 선택 사항임을 적고, 작성자의 접근 이유도 물어보세요.

## 전날 PR이 아직 열려 있을 때

전날 작업을 커밋해 작업 폴더를 깨끗하게 만든 뒤, 다음 날 `python3 study.py start`를 실행합니다.
이 명령은 최신 `origin/main`에서 새로 시작하므로 전날 미병합 변경이 오늘 PR에 섞이지 않습니다.
전날 리뷰를 반영하려면 `git switch study/아이디/전날날짜`로 돌아갑니다.

첫 참여 PR이 아직 미병합이면 다음 날 `new`가 참여자 파일을 다시 생성할 수 있습니다.
가능하면 첫 등록 PR을 먼저 merge하세요. 두 PR 모두 참여자 파일을 추가했다면
최신 main을 merge하고 `members/아이디.json`의 가장 이른 `joined` 날짜와 목표 이력을 보존해 충돌을 해결합니다.

```bash
git fetch origin
git merge origin/main
# 충돌 난 파일을 편집하고, 해결한 파일을 git add 후 git commit
```

브랜치를 지웠어도 main의 공부 기록은 남습니다.
GitHub에서 squash merge한 브랜치를 로컬 `git branch -d`가 삭제하지 못할 수 있습니다.
main에 기록이 들어갔는지 확인한 뒤 필요할 때만 해당 완료 브랜치를 `git branch -D 브랜치명`으로 정리하세요.

## 목표 변경과 뒤늦은 기록

`goal`은 적용일별 이력을 보존합니다. 다음 날부터 변경하는 것을 권장합니다.
과거 적용일을 변경하면 해당 날짜 이후 일일 README도 다시 생성되므로,
여러 날짜가 바뀌는 목표 정정은 `chore/goal-아이디` 같은 별도 브랜치에서 제출하세요.

날짜 기본값은 컴퓨터의 현지 시간대와 관계없이 한국 시간입니다.
자정을 넘겼다면 해당 작업의 `new`, `done`, `prepare`에 동일한 `--date YYYY-MM-DD`를 붙입니다.
참여 시작일 이전 기록을 옮길 때는 먼저 참여자 JSON의 `joined`와 첫 목표의 `from`을 함께 앞당깁니다.

`meta.json`은 자동 생성되지만 `level`, `tags`, `minutes`는 직접 수정해도 됩니다.
상태·날짜·아이디·문제번호를 바꾸는 대신 CLI를 사용하는 것을 권장합니다.
수동으로 목록에 영향을 주는 정보를 수정했다면 `index --date 날짜`를 실행합니다.

## 개인 레포에서도 사용하기

| 목적 | 방법 |
| --- | --- |
| 이 스터디에서 함께 PR·리뷰 연습 | 공용 레포 clone + 개인·날짜 브랜치 (기본) |
| 공용 레포 쓰기 권한 없이 참여 | fork + 원본으로 PR |
| 독립적인 새 스터디/개인 기록 시작 | GitHub Template repository로 새 레포 생성 |
| 문서 양식만 사용 | `templates/problem.md` 복사 후 `$title` 등 변수 채우기 |

자동 생성까지 쓰려면 `study.py`, `study.json`, `templates/`, `.gitignore`를 함께 가져옵니다.
CI와 현황 갱신도 필요하면 `.github/`, `scripts/`, `tests/`까지 복사합니다.
새 레포에서는 README의 GitHub 주소를 자신의 것으로 바꾸고, 기본 브랜치는 main으로 맞추세요.
다른 기본 브랜치를 쓴다면 `study.json`과 두 workflow의 main 설정을 함께 바꿉니다.

Fork로 참여할 때는 원본을 `upstream`, 내 fork를 `origin`으로 둡니다.
`start`의 기본 기준은 origin/main이므로, 원본 최신 상태에서 시작하려면 아래 Git 명령을 사용합니다.

```bash
git remote add upstream https://github.com/bk123477/codingtest_2026.git
git fetch upstream
git switch --no-track -c study/아이디/YYYY-MM-DD upstream/main
# 이후 new → done → prepare → commit → push origin
```

GitHub 웹에서 **base repository를 원본**, **head repository를 내 fork**로 선택해 PR을 생성합니다.
원본을 대상으로 권한 있는 리뷰어를 요청하세요. fork 내부 PR과 혼동하지 않도록 웹 흐름을 권장합니다.
Fork의 Actions 실행은 저장소 설정과 첫 기여 승인 상태에 따라 운영자의 승인이 필요할 수 있습니다.
독립 레포를 만드는 Template 기능은 원본에 PR을 보내는 fork 흐름과 목적이 다릅니다.
