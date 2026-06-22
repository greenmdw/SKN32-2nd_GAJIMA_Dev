"""
InsightFace 기반 얼굴 검출 유틸리티

- OpenCV Haar Cascade → InsightFace(buffalo_l) Detection 전환
- Detection만 수행 (임베딩은 백엔드 담당)
- FaceDetectionResult 인터페이스 유지
"""

from dataclasses import dataclass
import threading

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceDetectionResult:
    detected: bool
    bbox: tuple[int, int, int, int]  # (x, y, w, h)
    preview_bytes: bytes
    score: float


# InsightFace 앱 싱글톤
_app = None
_lock = threading.Lock()


def _get_app():
    """
    InsightFace FaceAnalysis 싱글톤 생성

    - buffalo_l 모델 사용
    - detection 모듈만 로드
    - CPU 실행
    """
    global _app

    if _app is None:
        with _lock:
            if _app is None:
                from insightface.app import FaceAnalysis

                app = FaceAnalysis(
                    name="buffalo_l",
                    allowed_modules=["detection"],  # 검출만 수행
                    providers=["CPUExecutionProvider"],
                )

                app.prepare(
                    ctx_id=0,
                    det_size=(640, 640),
                )

                _app = app

    return _app


def _decode_image(image_bytes: bytes):
    """
    업로드된 이미지 bytes → OpenCV BGR 이미지 변환

    InsightFace는 OpenCV BGR 포맷을 그대로 사용 가능
    """
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def _fail(image, original_bytes: bytes) -> FaceDetectionResult:
    """
    얼굴 검출 실패 시 공통 처리

    원본 이미지를 그대로 반환하여
    호출부 인터페이스를 유지한다.
    """
    ok, encoded = cv2.imencode(".jpg", image)

    return FaceDetectionResult(
        False,
        (0, 0, 0, 0),
        encoded.tobytes() if ok else original_bytes,
        0.0,
    )


def detect_largest_face(image_bytes: bytes) -> FaceDetectionResult:
    """
    이미지에서 가장 큰 얼굴 1개 검출

    Returns
    -------
    FaceDetectionResult
        detected      : 얼굴 검출 여부
        bbox          : (x, y, w, h)
        preview_bytes : 박스가 그려진 미리보기 이미지
    """

    image = _decode_image(image_bytes)

    if image is None:
        return FaceDetectionResult(
            False,
            (0, 0, 0, 0),
            image_bytes,
            0.0,
        )

    try:
        faces = _get_app().get(image)

    except Exception:
        return _fail(image, image_bytes)

    if not faces:
        return _fail(image, image_bytes)

    # 가장 큰 얼굴 선택
    face = max(
        faces,
        key=lambda fc: (
            (fc.bbox[2] - fc.bbox[0])
            * (fc.bbox[3] - fc.bbox[1])
        ),
    )

    # InsightFace bbox = (x1, y1, x2, y2)
    x1, y1, x2, y2 = (int(v) for v in face.bbox)

    preview = image.copy()

    cv2.rectangle(
        preview,
        (x1, y1),
        (x2, y2),
        (118, 217, 87),
        4,
    )

    # Detection Confidence
    # "이 영역이 얼굴일 확률" 표시 =============
    confidence = float(face.det_score)

    label = f"Face {confidence * 100:.1f}%"

    cv2.putText(
        preview,
        label,
        (x1, max(y1 - 10, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (118, 217, 87),
        2,
    )
    # ======================================

    ok, encoded = cv2.imencode(".jpg", preview)

    return FaceDetectionResult(
        True,
        (
            x1,
            y1,
            max(x2 - x1, 0),
            max(y2 - y1, 0),
        ),
        encoded.tobytes() if ok else image_bytes,
        confidence,
    )