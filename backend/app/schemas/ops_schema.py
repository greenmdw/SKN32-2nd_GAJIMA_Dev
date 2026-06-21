# -*- coding: utf-8 -*-
"""schemas — 리텐션 액션 요청(19-4 §5)."""
from typing import Optional
from pydantic import BaseModel


class RetentionActionIn(BaseModel):
    user_id: str
    action_type: str            # coupon | remind | none
    message: str
    prediction_id: Optional[int] = None
