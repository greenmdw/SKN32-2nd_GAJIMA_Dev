# -*- coding: utf-8 -*-
"""interfaces/http — 공통 응답 봉투(19-4 §6 / 19-5 §6). 모든 라우트가 {ok,data,meta,error}로 반환."""


def ok(data, source="backend"):
    return {"ok": True, "data": data,
            "meta": {"schema_version": "dashboard.v1", "source": source}, "error": None}


def err(code, message):
    return {"ok": False, "data": None,
            "meta": {"schema_version": "dashboard.v1"}, "error": {"code": code, "message": message}}
