# -*- coding: utf-8 -*-
"""domain — 얼굴 임베딩 코사인 매칭(순수). insightface normed 512d 기준 threshold 0.45."""
import math

THRESHOLD = 0.45


def cosine(a, b):
    if not a or not b:
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / ((na * nb) + 1e-8)


def best_match(embedding, users, threshold=THRESHOLD):
    """등록 유저들과 비교 최고 유사. 반환 (user|None, similarity)."""
    best_u, best = None, -1.0
    for u in users:
        if not u.get("embedding"):
            continue
        s = cosine(embedding, u["embedding"])
        if s > best:
            best, best_u = s, u
    if best >= threshold:
        return best_u, best
    return None, best
