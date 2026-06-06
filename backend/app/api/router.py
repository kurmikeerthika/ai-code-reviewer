# app/api/router.py
from fastapi import APIRouter
from app.api.endpoints import upload, rag, review, github

api_router = APIRouter()
api_router.include_router(upload.router)
api_router.include_router(rag.router)
api_router.include_router(review.router)
api_router.include_router(github.router)