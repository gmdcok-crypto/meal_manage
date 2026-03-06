# -*- coding: utf-8 -*-
"""FastAPI 2일차 - 첫 번째 앱. 실행: uvicorn main:app --reload"""
from fastapi import FastAPI

app = FastAPI(title="FastAPI 2일차 연습")


@app.get("/")
async def root():
    """루트 경로(/) 접속 시 이 함수가 실행됩니다."""
    return {"message": "FastAPI 첫 앱에 오신 걸 환영합니다!", "day": 2}
