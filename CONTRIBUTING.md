# 참여 중 문제 해결

[README](README.md)의 “참여자: 오늘의 첫 기록”을 먼저 따라 하세요. 이 문서는 진행 중 자주 만나는 상황을 해결하기 위한 안내입니다.

## 첫 PR 전에 확인할 것

Git이 처음이라면 이름과 이메일을 한 번 설정합니다.

```bash
git config user.name "이름"
git config user.email "GitHub에 등록한 이메일 또는 GitHub noreply 이메일"
```

`python3 study.py prepare`가 만든 명령을 실행하기 전에는 아래 두 명령으로 변경사항을 확인할 수 있습니다.

```bash
git status
git diff
```

평소 일일 PR에는 그날의 `records/YYYY/MM/DD/내아이디/` 폴더와, 첫 기록 또는 목표 변경 때의 `members/내아이디.json`만 넣습니다. 도구·공용 문서·템플릿을 수정할 때는 `chore/설명`처럼 별도 브랜치와 별도 PR을 사용합니다.

## 리뷰하기

추천 리뷰어는 `prepare`가 참여자 목록과 날짜를 기준으로 보여 줍니다. 실제 PR에서 오른쪽 **Reviewers** 항목으로 지정하거나 바꿀 수 있습니다.

1. PR의 **Files changed** 탭을 엽니다.
2. 코드 또는 Markdown 문서에서 의견을 남길 줄의 `+` 버튼을 누릅니다.
3. 코딩 문제는 경계 조건·복잡도·다른 풀이를, 학습 정리는 설명의 정확성·이해되지 않는 부분·실습 결과를 살펴봅니다.
4. 리뷰를 마치면 **Review changes → Submit review**를 누릅니다.
5. 수정이 필요하면 **Request changes**, 통과면 **Approve**, 단순 질문이면 **Comment**를 선택합니다.

작성자는 같은 브랜치에서 수정하고 다시 `git add → git commit → git push`합니다. 새 commit이 올라오면 리뷰어가 다시 확인합니다.

## 전날 PR이 아직 열려 있을 때

전날 리뷰를 반영하려면 그 브랜치로 돌아갑니다.

```bash
git switch study/내아이디/전날날짜
```

다음 날 기록은 미커밋 변경이 없는 상태에서 새로 시작합니다.

```bash
python3 study.py start
```

`start`는 최신 `origin/main`을 fetch한 뒤 시작하므로 전날 PR의 변경이 오늘 PR에 섞이지 않습니다. 새 날짜 브랜치를 만들기 위해 로컬 main을 따로 pull할 필요는 없습니다. 다만 로컬 main을 열어 보거나 수동으로 브랜치를 만들 때는 아래처럼 최신화합니다.

```bash
git switch main
git pull --ff-only origin main
```

merge가 끝난 브랜치는 GitHub의 **Delete branch**로 정리합니다. 기록과 PR 내역은 main과 GitHub에 남습니다. 로컬 브랜치는 main을 최신으로 받은 뒤 아래처럼 지울 수 있습니다.

```bash
git switch main
git pull origin main
git branch -d study/내아이디/완료날짜
```

Squash merge를 쓰면 `git branch -d`가 거부할 수 있습니다. GitHub에서 해당 PR이 **Merged**인지 먼저 확인한 뒤에만 `git branch -D study/내아이디/완료날짜`로 로컬 브랜치를 정리하세요.

첫 기록 PR이 아직 merge되기 전에 다음 날 기록까지 작성하면 `members/내아이디.json`이 두 브랜치에 생길 수 있습니다. 가능하면 첫 PR을 먼저 merge하세요. 충돌이 나면 최신 main을 합친 뒤 해당 JSON의 가장 이른 `joined` 날짜와 목표 이력을 보존합니다.

## 목표와 날짜를 바꾸고 싶을 때

목표는 문제와 학습 정리를 합친 완료 기록 수입니다. 문제 3개와 정리 2개도 하루 5건으로 함께 셉니다. 다음 날부터 하루 3건으로 바꾸려면 아래를 실행하고, 바뀐 `members/내아이디.json`을 일일 기록과 함께 commit합니다.

오늘 하루만 목표를 달리 정할 때는 브랜치를 만들 때 지정합니다. 예를 들어 문제 1개와 학습 정리 1개를 할 예정이면 목표는 2건입니다. `start --goal`은 해당 날짜에만 적용되며 다음 날에는 기본 목표로 돌아갑니다.

```bash
python3 study.py start --goal 2
```

```bash
python3 study.py goal 3 --from 2026-09-10
```

목표 달성 여부 없이 기록만 남기고 싶다면 `none`을 사용합니다. 이 경우에도 기록 생성·PR·리뷰·현황 집계는 같고, 현황에는 완료 건수만 표시됩니다.

```bash
python3 study.py goal none --from 2026-09-10
```

`init`은 첫 사용 때의 로컬 기본값을 정하는 명령입니다. 이미 첫 기록을 만들었다면 `init`을 다시 실행해도 GitHub에 올라간 목표 이력은 바뀌지 않으므로, 목표 변경에는 항상 `goal` 명령을 사용하세요.

자정을 넘겨 전날 기록을 작성한다면 `new` 또는 `note`, `done`, `prepare`에 같은 날짜를 지정합니다.

```bash
python3 study.py note --title "전날 학습 정리" --date 2026-09-05
python3 study.py done note-01 --date 2026-09-05
python3 study.py prepare --date 2026-09-05
```

`meta.json`은 자동 생성합니다. 태그·시간·문제 난이도·정리 참고 링크를 직접 바꾼 뒤에는 일일 목록을 갱신하세요.

```bash
python3 study.py index --date YYYY-MM-DD
```

명령의 옵션이 기억나지 않으면 `python3 study.py help` 또는 `python3 study.py help note`처럼 확인합니다. 기존 `--help` 옵션도 동일하게 사용할 수 있습니다.

## 개인 레포나 fork로 참여하기

공용 레포에서 브랜치와 리뷰를 연습하는 것이 기본 방식입니다. 쓰기 권한이 없다면 fork를 만들고 원본 레포로 PR을 보낼 수 있습니다.

```bash
git remote add upstream https://github.com/bk123477/codingtest_2026.git
git fetch upstream
git switch --no-track -c study/내아이디/YYYY-MM-DD upstream/main
```

이후에는 `new` 또는 `note → 파일 작성 → done → prepare`를 실행하고 내 fork(`origin`)에 push합니다. GitHub에서 PR을 만들 때 base repository는 원본, head repository는 내 fork를 선택합니다.

독립된 개인 스터디를 만들고 싶다면 GitHub의 **Use this template** 기능을 사용합니다. 이 경우 README의 GitHub 주소를 새 레포 주소로 바꾸고, 같은 자동화를 쓰려면 `.github/`, `scripts/`, `tests/`도 유지하세요.
