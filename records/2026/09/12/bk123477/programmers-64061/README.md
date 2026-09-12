# 크레인 인형뽑기 게임

- 문제 링크: [programmers / 64061](https://school.programmers.co.kr/learn/courses/30/lessons/64061)
- 날짜: 2026-09-12 · 작성자: bk123477 · 언어: python
- 풀이 코드: [solution.py](solution.py)

## 풀이 정보

- 난이도: Lv.1
- 풀이 방식: 미입력
- 자료구조: 배열, 스택
- 알고리즘: 구현
## 문제

<!-- 원문 전체를 옮길 필요 없이, 요구사항과 핵심 제약을 짧게 요약하세요. -->
크레인 이동 순서에 따라 각 열의 가장 위 인형을 바구니로 옮긴다. 바구니 맨 위에 같은 인형이 연속으로 놓이면 두 개를 제거하고, 모든 이동 후 제거된 인형의 수를 반환한다. 보드 크기는 5~30, 이동 횟수는 최대 1,000이다.

## 풀이

<!-- 접근 방법과 그 이유를 1~3줄로 작성하세요. -->
`board`를 열 기준인 `game`으로 전치해 각 크레인 열을 위에서 아래로 순회한다. 0이 아닌 첫 인형을 `stack`에 넣고 직전 인형과 같으면 두 개를 제거하며, 집은 칸은 0으로 표시한다.

## 확인한 예제 / 경계 조건

문제 제공 예제의 `moves=[1, 5, 3, 5, 1, 2, 1, 4]`에 대한 예상 결과는 `4`이다. 어떤 열을 집었을 때 인형이 없으면 해당 이동은 건너뛰고, 바구니가 비어 있거나 직전 인형과 다르면 제거하지 않고 스택에 쌓는다. 직접 실행 여부와 채점 결과는 별도로 기록하지 않았다.

## 복잡도 (선택)

- 시간: `O(N^2 + MN)` (`N`은 보드 한 변, `M`은 moves 길이)
- 공간: `O(N^2 + M)` (`game`과 바구니 스택)

## 회고 / 리뷰 요청 (선택)

<!-- 막힌 부분, 다른 접근, 리뷰 받고 싶은 줄 등을 자유롭게 작성하세요. -->
내 풀이와 하단의 풀이를 비교해서 설명해라.

'''
def solution(board, moves):
    stacklist = []
    answer = 0

    for i in moves:
        for j in range(len(board)):
            if board[j][i-1] != 0:
                stacklist.append(board[j][i-1])
                board[j][i-1] = 0

                if len(stacklist) > 1:
                    if stacklist[-1] == stacklist[-2]:
                        stacklist.pop(-1)
                        stacklist.pop(-1)
                        answer += 2     
                break

    return answer

'''

대안 풀이 비교: [오늘 문제의 대안 풀이 비교](../note-01/README.md)
