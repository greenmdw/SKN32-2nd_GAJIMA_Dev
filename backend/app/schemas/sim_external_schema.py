# -*- coding: utf-8 -*-
"""schemas — 시뮬 사이트(ecom-churn-simulation) 외부 계약(ENV_SETUP.md / fastApiClient.ts).
대시보드 봉투와 별개의 raw 계약. churn_probability는 % (0~100)."""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class SimEvent(BaseModel):
    event_type: str
    product_id: Optional[str] = None
    category_id: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = 0
    quantity: Optional[int] = 1
    timestamp: Optional[str] = None


class ChurnPredictIn(BaseModel):
    session_id: str
    user_id: str
    events: List[SimEvent] = []


class RecommendationIn(BaseModel):
    session_id: str
    user_id: str
    current_product_id: Optional[str] = None
    category_id: Optional[str] = None
    brand: Optional[str] = None


class EventIn(BaseModel):
    event_id: Optional[str] = None
    user_id: str
    session_id: str
    event_type: str
    event_time: Optional[str] = None
    product_id: Optional[str] = None
    category_id: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = 0
    quantity: Optional[int] = 1
    page_url: Optional[str] = None
    referrer: Optional[str] = None
    device_type: Optional[str] = None
    payload_json: Optional[Dict[str, Any]] = None
