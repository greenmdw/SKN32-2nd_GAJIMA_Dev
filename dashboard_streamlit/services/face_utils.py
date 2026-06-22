from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis


@dataclass(frozen=True)
class FaceDetectionResult:
    detected: bool
    bbox: tuple[int, int, int, int]
    preview_bytes: bytes
    score: Optional[float] = None


def _decode_image(image_bytes: bytes):
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


# InsightFace 모델 초기화
app = FaceAnalysis(name='buffalo_l', root='.')
app.prepare(ctx_id=-1, det_size=(640, 640))


def _draw_result(image: np.ndarray, bbox: tuple[int, int, int, int], score: Optional[float]):
    """이미지 위에 초록색 박스와 유사도 점수를 그립니다."""
    preview = image.copy()
    x, y, w, h = bbox

    # 1. 초록색 얼굴 박스 그리기 (BGR: (87, 217, 118))
    cv2.rectangle(preview, (x, y), (x + w, y + h), (87, 217, 118), 4)

    # 2. 점수가 존재할 때 글자 그리기
    if score is not None:
        text = f"Accuracy: {score:.1%}"

        # 글자가 화면 상단 밖으로 가려지지 않도록 y 좌표 안전장치 설정
        text_y = y - 15 if y - 15 > 30 else y + 40
        text_x = x + 5

        # 가시성을 극대화하기 위해 검은색 외곽선(그림자 효과) 먼저 그리기
        cv2.putText(preview, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                    1.2, (0, 0, 0), 5, cv2.LINE_AA)

        # 그 위에 선명한 초록색 글씨 얹기
        cv2.putText(preview, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                    1.2, (87, 217, 118), 2, cv2.LINE_AA)

    return preview


def detect_largest_face(image_bytes: bytes, mode: str = "detection",
                        current_user_embeddings=None,
                        forced_score: Optional[float] = None) -> FaceDetectionResult:
    """InsightFace를 사용하여 얼굴을 검출하고 정확도를 안전하게 오버레이합니다."""
    image = _decode_image(image_bytes)
    if image is None:
        return FaceDetectionResult(False, (0, 0, 0, 0), image_bytes)

    # 1. InsightFace로 얼굴 검출
    faces = app.get(image)

    if len(faces) == 0:
        ok, encoded = cv2.imencode(".jpg", image)
        return FaceDetectionResult(False, (0, 0, 0, 0), encoded.tobytes() if ok else image_bytes)

    # 2. 가장 큰 얼굴 선택
    main_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    x1, y1, x2, y2 = main_face.bbox.astype(int)
    w = x2 - x1
    h = y2 - y1
    face_bbox = (int(x1), int(y1), int(w), int(h))

    # 3. 정확도 점수 결정
    score_to_draw = forced_score
    if score_to_draw is None and mode == "login" and current_user_embeddings is not None:
        score_to_draw = float(np.dot(current_user_embeddings, main_face.embedding.T))

    # 4. 이미지 위에 박스와 점수 그리기
    preview = _draw_result(image, face_bbox, score_to_draw)

    # 5. 최종 결과 반환 (.jpg 포맷 인코딩)
    ok, encoded = cv2.imencode(".jpg", preview)
    return FaceDetectionResult(True, face_bbox, encoded.tobytes() if ok else image_bytes, score=score_to_draw)