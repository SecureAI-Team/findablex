"""
WebSocket endpoint for real-time progress updates.

Provides live updates for:
- Crawl task progress (per-engine query completion)
- Auto-checkup overall progress
- Report generation status

Protocol:
  Client → Server: { "type": "subscribe", "project_id": "<uuid>" }
  Server → Client: { "type": "progress", "data": {...} }

Authentication: pass JWT token as query param `?token=<jwt>`
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import async_session_maker
from app.models.crawler import CrawlTask

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory connection manager
# For scale-out, replace with Redis pub/sub
_connections: Dict[str, Set[WebSocket]] = {}  # project_id → set of websockets


class ConnectionManager:
    """Manages WebSocket connections grouped by project_id."""
    
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, project_id: str, ws: WebSocket):
        await ws.accept()
        if project_id not in self.connections:
            self.connections[project_id] = set()
        self.connections[project_id].add(ws)
        logger.debug(f"WS connected: project={project_id}, total={len(self.connections[project_id])}")
    
    def disconnect(self, project_id: str, ws: WebSocket):
        if project_id in self.connections:
            self.connections[project_id].discard(ws)
            if not self.connections[project_id]:
                del self.connections[project_id]
    
    async def broadcast(self, project_id: str, message: dict):
        """Send message to all connections watching a project."""
        if project_id not in self.connections:
            return
        
        dead = set()
        data = json.dumps(message, default=str)
        
        for ws in self.connections[project_id]:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        
        # Clean up dead connections
        for ws in dead:
            self.connections[project_id].discard(ws)


manager = ConnectionManager()


async def _get_project_progress(project_id: str) -> dict:
    """Fetch current progress for a project from the database."""
    async with async_session_maker() as db:
        result = await db.execute(
            select(CrawlTask)
            .where(CrawlTask.project_id == project_id)
            .order_by(CrawlTask.created_at.desc())
        )
        tasks = list(result.scalars().all())
    
    if not tasks:
        return {
            "type": "progress",
            "project_id": project_id,
            "total_tasks": 0,
            "completed": 0,
            "in_progress": 0,
            "failed": 0,
            "progress_pct": 0,
            "engines": [],
            "is_complete": True,
        }
    
    completed = sum(1 for t in tasks if t.status == "completed")
    in_progress = sum(1 for t in tasks if t.status in ("pending", "processing", "running"))
    failed = sum(1 for t in tasks if t.status == "failed")
    
    total_queries = sum(t.total_queries for t in tasks)
    processed = sum(t.successful_queries + t.failed_queries for t in tasks)
    progress_pct = (processed / total_queries * 100) if total_queries > 0 else 0
    
    engines = [
        {
            "engine": t.engine,
            "status": t.status,
            "total": t.total_queries,
            "done": t.successful_queries + t.failed_queries,
            "ok": t.successful_queries,
            "fail": t.failed_queries,
        }
        for t in tasks
    ]
    
    return {
        "type": "progress",
        "project_id": project_id,
        "total_tasks": len(tasks),
        "completed": completed,
        "in_progress": in_progress,
        "failed": failed,
        "progress_pct": round(progress_pct, 1),
        "engines": engines,
        "is_complete": in_progress == 0 and len(tasks) > 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.websocket("/ws/progress")
async def websocket_progress(
    ws: WebSocket,
    token: str = Query(""),
):
    """
    WebSocket for real-time progress updates.
    
    Query params:
      - token: JWT access token
    
    After connection, client sends:
      { "type": "subscribe", "project_id": "<uuid>" }
    
    Server pushes progress updates every 3 seconds while tasks are running.
    """
    # Authenticate
    if not token:
        await ws.close(code=4001, reason="Missing token")
        return
    
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await ws.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await ws.close(code=4001, reason="Invalid token")
        return
    
    await ws.accept()
    
    project_id = None
    
    try:
        while True:
            # Wait for client messages (subscribe, ping)
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=3.0)
                msg = json.loads(raw)
                
                if msg.get("type") == "subscribe":
                    new_project_id = msg.get("project_id", "")
                    
                    # Unsubscribe from old
                    if project_id:
                        manager.disconnect(project_id, ws)
                    
                    project_id = new_project_id
                    if project_id:
                        if project_id not in manager.connections:
                            manager.connections[project_id] = set()
                        manager.connections[project_id].add(ws)
                    
                    # Send initial progress
                    progress = await _get_project_progress(project_id)
                    await ws.send_text(json.dumps(progress, default=str))
                
                elif msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
                
            except asyncio.TimeoutError:
                # No message from client in 3s → push progress update
                if project_id:
                    progress = await _get_project_progress(project_id)
                    await ws.send_text(json.dumps(progress, default=str))
                    
                    # If complete, slow down polling
                    if progress.get("is_complete"):
                        await asyncio.sleep(10)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WS error: {e}")
    finally:
        if project_id:
            manager.disconnect(project_id, ws)


# Helper for backend services to push updates
async def push_progress(project_id: str):
    """Push a progress update to all WebSocket clients watching a project."""
    progress = await _get_project_progress(project_id)
    await manager.broadcast(project_id, progress)
