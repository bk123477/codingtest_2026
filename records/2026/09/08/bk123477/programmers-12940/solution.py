'''
문제 설명
두 수를 입력받아 두 수의 최대공약수와 최소공배수를 반환하는 함수, solution을 완성해 보세요. 배열의 맨 앞에 최대공약수, 그다음 최소공배수를 넣어 반환하면 됩니다. 예를 들어 두 수 3, 12의 최대공약수는 3, 최소공배수는 12이므로 solution(3, 12)는 [3, 12]를 반환해야 합니다.

제한 사항
두 수는 1이상 1000000이하의 자연수입니다.

입출력 예
n	m	return
3	12	[3, 12]
2	5	[1, 10]
'''

def solution(n, m):
    n_divide = 1
    a, b = n, m
    tmp = []
    for i in range(2, min(n, m)+1):
        if a%i == 0 and b%i == 0:
            n_divide = i
    
    for i in range(2, max(n, m)+1):
        if a < i or b < i:
            tmp.append(a)
            tmp.append(b)
            break
        while a%i == 0 or b%i == 0:
            if a%i == 0 and b%i == 0:
                tmp.append(i)
                a /= i
                b /= i
            elif a%i == 0 and b%i != 0:
                tmp.append(i)
                a /= i
            elif a%i != 0 and b%i == 0:
                tmp.append(i)
                b /= i
    multi = 1
    for t in tmp:
        multi*=t
    return [n_divide, multi]