# -*- coding: utf-8 -*-
"""얼굴 인증(insightface buffalo_l/ArcFace). 모델/카메라 없으면 폴백(수동 로그인)으로 데모 유지."""
import numpy as np

THRESHOLD = 0.45
_APP = None
try:
    from insightface.app import FaceAnalysis  # noqa
    HAS_FACE = True
except Exception:
    HAS_FACE = False


def get_app():
    global _APP
    if not HAS_FACE:
        return None
    if _APP is None:
        try:
            from insightface.app import FaceAnalysis
            _APP = FaceAnalysis(name="buffalo_l")
            _APP.prepare(ctx_id=-1, det_size=(640, 640))
        except Exception:
            return None
    return _APP


def embed_from_bytes(img_bytes):
    """업로드/카메라 bytes → 정규화 임베딩(512d) 또는 None."""
    app = get_app()
    if app is None:
        return None
    try:
        import cv2
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        faces = app.get(img)
        if not faces:
            return None
        e = faces[0].normed_embedding.astype(np.float32)
        return e / (np.linalg.norm(e) + 1e-8)
    except Exception:
        return None


def cosine(a, b):
    if a is None or b is None:
        return -1.0
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8))


def match(embedding, users, threshold=THRESHOLD):
    """등록 유저들과 비교해 최고 유사 매칭. 반환 (user_id, role, similarity) 또는 (None,None,best)."""
    best_id, best_role, best = None, None, -1.0
    for u in users:
        if u.get("embedding") is None:
            continue
        s = cosine(embedding, u["embedding"])
        if s > best:
            best, best_id, best_role = s, u["user_id"], u["role"]
    if best >= threshold:
        return best_id, best_role, best
    return None, None, best
