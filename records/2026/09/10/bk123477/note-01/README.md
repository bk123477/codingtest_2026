# 오늘 풀이의 다른 접근 정리

- 기록 유형: 학습 정리
- 날짜: 2026-09-10 · 작성자: bk123477

## 학습 주제 / 목표

<!-- 어떤 내용을 왜 공부했는지 1~3줄로 작성하세요. -->
오늘 문제 풀이의 회고에 남긴 대안 코드들을 한곳에 모아, 문자열 파싱·정렬 묶음·구간 덮기에서 같은 핵심 로직을 더 간결하게 표현하는 방법을 비교한다. 각 대안의 동작과 복잡도를 현재 풀이와 함께 확인하는 것이 목표다.

## 정리 내용

<!-- 개념 설명, 실습 과정, 독서/강의 요약 등을 자유롭게 작성하세요. 코드와 이미지는 선택입니다. -->
### 1. 옹알이 (2): `replace`와 `startswith`로 파싱하기

현재 풀이는 첫 글자를 기준으로 발음을 직접 비교하면서 이전 발음과 같은지 확인한다. 회고에 남긴 `replace` 방식은 허용 발음의 연속 출현을 먼저 막은 뒤, 각 발음을 공백으로 치환해 문자열이 모두 소진되는지 확인한다.

```python
def solution(babbling):
    answer = 0
    for word in babbling:
        for speak in ["aya", "ye", "woo", "ma"]:
            if speak * 2 not in word:
                word = word.replace(speak, " ")
        if len(word.strip()) == 0:
            answer += 1
    return answer
```

`startswith` 방식은 현재 위치에서 허용 발음이 시작하는지 확인하고, 직전 발음과 같으면 건너뛴다. 발음 단위로 인덱스를 이동하므로 문자열을 앞에서부터 분할하는 흐름이 명확하다.

```python
def solution(babbling):
    answer = 0
    speaks = ["aya", "ye", "woo", "ma"]

    def check(word):
        index = 0
        prev = ""
        while index < len(word):
            found = False
            for speak in speaks:
                if speak == prev:
                    continue
                if word.startswith(speak, index):
                    index += len(speak)
                    prev = speak
                    found = True
                    break
            if not found:
                return False
        return True

    for word in babbling:
        if check(word):
            answer += 1
    return answer
```

### 2. 과일 장수: 정렬 후 슬라이싱하기

현재 풀이는 오름차순 정렬 후 `deque`의 오른쪽에서 큰 점수부터 `m`개씩 꺼낸다. 같은 원리를 슬라이싱으로 표현하면, 남는 사과 수를 제외한 위치에서 `m` 간격으로 각 상자의 최저 점수를 선택할 수 있다.

```python
def solution(k, m, score):
    sorted_score = sorted(score)
    return sum(sorted_score[len(score) % m::m]) * m
```

정렬된 배열의 각 묶음에서 최저 점수는 묶음의 오른쪽 끝에 위치한다. 따라서 높은 점수 쪽부터 `m`개 단위로 묶는 현재 방식과, 오름차순 배열에서 묶음 최저점만 골라 합산하는 방식은 같은 이익을 계산한다. 두 방식 모두 정렬 때문에 시간 복잡도는 O(S log S)이고, 정렬 결과를 저장해 O(S) 공간을 사용한다.

### 3. 덧칠하기: 마지막 시작점만 기록하기

현재 풀이는 마지막으로 칠한 구간의 시작점과 끝점을 모두 저장한다. `section`이 오름차순이라는 점을 이용하면 마지막 롤러의 시작점만 저장해도 `sec - prev >= m`인지로 새 칠하기 여부를 판단할 수 있다.

```python
def solution(n, m, section):
    answer = 1
    prev = section[0]
    for sec in section:
        if sec - prev >= m:
            prev = sec
            answer += 1
    return answer
```

두 방식 모두 아직 칠하지 않은 가장 왼쪽 구역에서 롤러를 시작해 오른쪽으로 최대한 덮는 그리디 선택을 반복한다. 따라서 `section`을 한 번 순회해 O(S) 시간과 O(1) 추가 공간으로 처리한다.

## 배운 점 / 확인한 내용

<!-- 새로 이해한 점, 직접 확인한 예시, 적용해 볼 내용을 적으세요. -->
문자열 문제에서는 발음 단위로 인덱스를 이동하는 방식이 연속 발음 금지 조건을 코드에 직접 드러내고, 치환 방식은 짧은 코드로 전체 소진 여부를 확인할 수 있다. 정렬 문제에서는 결과에 필요한 경계 원소만 선택하면 반복문을 줄일 수 있으며, 구간 덮기 문제에서는 마지막 구간의 시작점만으로도 현재 풀이의 범위를 표현할 수 있다.

## 참고 자료 (선택)

<!-- 참고한 링크나 책 이름을 자유롭게 적으세요. -->

## 회고 / 리뷰 요청 (선택)

<!-- 이해가 어려웠던 부분이나 동료에게 질문하고 싶은 내용을 적으세요. -->
