# 운영자 안내

이 문서는 팀장을 위한 초기 설정과 일상 운영 안내입니다. 참여자에게는 [README](../README.md)를 전달하세요.

## 처음 한 번: GitHub 설정

### 1. 시스템을 main에 올립니다

이 저장소에서는 기본 구성이 main에 올라가 있습니다. 새 스터디 레포에서 다시 사용할 때는 아래처럼 확인하고 push합니다.

```bash
python3 -m unittest discover -s tests -v
python3 study.py check
git add README.md CONTRIBUTING.md .github docs examples members records scripts study.json study.py templates tests
git commit -m "Set up study workflow"
git push origin main
```

main이 보호되어 있다면 `chore/study-setup` 브랜치에서 commit/push하고 설정 PR로 merge합니다.

### 2. 팀원을 초대합니다

GitHub 저장소에서 **Settings → Collaborators**로 들어가 팀원을 초대합니다. 쓰기 권한이 있는 참여자는 공용 레포에서 자신의 날짜별 브랜치를 만들 수 있습니다.

첫 기록을 만들면 참여자의 `members/아이디.json`이 자동 생성됩니다. 처음부터 현황에 참여자를 보이고 싶다면 운영자가 실제 GitHub 아이디로 아래 파일을 만들 수 있습니다.

```text
members/실제GitHub아이디.json
```

```json
{
  "user": "실제github아이디",
  "joined": "2026-09-05",
  "goals": [{"from": "2026-09-05", "daily_goal": 5}]
}
```

문제 1개 또는 학습 정리 1개가 목표 1건입니다. 정리만 하는 참여자는 `daily_goal`을 1처럼 다르게 둘 수 있습니다.

### 3. GitHub Actions를 확인합니다

GitHub의 **Actions** 탭에서 다음 두 workflow가 성공하는지 확인합니다.

| Workflow | 하는 일 |
| --- | --- |
| `Study validation` | PR과 push의 기록 형식, 일일 PR 범위, 자동화 테스트를 검사합니다. |
| `Study progress` | main에 merge된 기록을 집계해 `progress` 브랜치의 현황 README를 갱신합니다. |

`Study progress`가 성공하면 `progress` 브랜치가 생기고 README의 학습 현황 링크가 열립니다. Actions 화면에서 **Run workflow**로 수동 실행할 수도 있습니다.

보고서 갱신 workflow는 `contents: write` 권한을 사용합니다. 조직 정책으로 Actions 쓰기 권한이 막힌 경우, 이 workflow가 `progress` 브랜치에 쓸 수 있도록 허용해야 합니다. 별도 Personal Access Token은 필요하지 않습니다.

### 4. main 보호 규칙을 설정합니다

첫 `Study validation` 실행 후 GitHub의 **Settings → Rules → Rulesets** 또는 **Settings → Branches**에서 main 대상 규칙을 만듭니다.

- PR을 통해서만 main에 합치기
- 최소 1명 승인 요구
- 새 commit이 올라오면 기존 승인 무효화
- `study-check` 상태 검사 통과 요구
- 리뷰 대화 해결 요구
- force push와 main 브랜치 삭제 금지

저장소 **Settings → General → Pull Requests**에서는 Squash merge와 merge 후 브랜치 자동 삭제를 켜는 편이 운영하기 편합니다.

## 매일 확인할 것

1. 열린 PR에 리뷰어가 배정됐는지 확인합니다.
2. `study-check`가 성공했는지 확인합니다.
3. 리뷰가 끝난 PR을 squash merge합니다.
4. 학습 현황은 `progress` 브랜치에서 확인합니다.

일일 브랜치는 merge 후 자동 삭제를 권장합니다. 자동 삭제를 켜지 않았다면 PR의 **Delete branch** 버튼으로 원격 브랜치를 정리합니다. main에 merge된 기록과 PR·리뷰 내역은 삭제되지 않습니다.

참여자가 다음 날짜에 `study.py start`를 실행하면 도구가 최신 원격 main에서 새 브랜치를 만듭니다. 따라서 매일 local main을 pull하라고 안내할 필요는 없습니다. 자동 브랜치 삭제는 GitHub의 원격 PR 브랜치에만 적용되며, 각 참여자의 로컬 main·기존 날짜 브랜치에는 영향을 주지 않습니다.

목표 미달은 PR 실패 사유가 아닙니다. 장기간 미달이 반복되는지 확인하고 팀 규칙이나 개인 목표를 조정하는 용도로 사용하세요.

학습 현황은 merge된 기록만 집계합니다. 리뷰 중인 내용은 해당 PR에서 확인합니다. 매일 한국 시간 00:15에도 현황을 갱신하며, GitHub 예약 실행은 약간 늦을 수 있습니다.

## 운영할 때 알아둘 점

- `progress` 브랜치는 자동 생성된 현황 전용입니다. 직접 수정하면 다음 자동 갱신 때 바뀝니다.
- CI는 문제의 정답이나 학습 정리의 사실 여부를 판단하지 않습니다. 작성자와 리뷰어가 확인합니다.
- 일일 브랜치 검사는 폴더와 날짜가 섞이는 실수를 막기 위한 규칙입니다. GitHub 계정과 폴더 아이디를 강제로 대조하지는 않습니다.
- 템플릿의 필수 제목을 바꾸려면 `study.py`의 검증 항목도 함께 바꿔야 합니다. 단순 문구·선택 항목 변경은 템플릿만 바꿔도 됩니다.

구현 선택과 자동화의 내부 구조는 [설계 문서](design.md)를 참고하세요.
