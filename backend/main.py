from fastapi import FastAPI, WebSocket, Query
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.database.base import init_db
from app.api.auth.routes import router as auth_router
from app.api.monitoring.routes import router as monitor_router
from app.api.alerts.routes import router as alerts_router
from app.api.analytics.routes import router as analytics_router
from app.api.conversations.routes import router as conversations_router
from app.api.emergency.routes import router as emergency_router
from app.api.comments.routes import router as comments_router
from app.api.websocket import websocket_endpoint
from app.core.config import settings
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Capture the running FastAPI event loop so the background scraper thread
    # can schedule WebSocket broadcasts onto it via run_coroutine_threadsafe.
    from app.services.analysis_pipeline import set_main_loop
    set_main_loop(asyncio.get_event_loop())
    logger.info("CyberShield AI started")
    yield

app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

import os

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://pdd-sandy.vercel.app",
]
# Add Vercel frontend URL from environment variable if set
_frontend_url = os.environ.get("FRONTEND_URL", "")
if _frontend_url:
    ALLOWED_ORIGINS.append(_frontend_url)
    # Also allow with/without trailing slash
    ALLOWED_ORIGINS.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/api")
app.include_router(monitor_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(emergency_router, prefix="/api")
app.include_router(comments_router, prefix="/api/comments")

@app.websocket("/ws")
async def ws(websocket: WebSocket, token: str = Query(...)):
    await websocket_endpoint(websocket, token)

# Lifespan events are handled via the lifespan context manager passed to FastAPI

@app.get("/health")
def health():
    return {"success": True, "message": "Running", "data": {}}
