def solution(citations):
    citations.sort(reverse=True)
    for i, citation in enumerate(citations, start=1):
        if citation < i:
            return i - 1
    return len(citations)
