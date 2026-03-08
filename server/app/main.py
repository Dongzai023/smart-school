"""FastAPI application entry point."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password
from app.services.scheduler import start_scheduler, load_schedules, list_jobs

# Import all models to ensure they are registered
from app.models import user, device, schedule, lock_image, log, time_slot, checkin_record, leave  # noqa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    init_db()
    _ensure_admin_exists()
    _ensure_principals_exist()
    start_scheduler()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS (Simplified for Same-Origin and JWT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logger Middleware
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    if duration > 1.0:  # Only log slow requests
        logger.warning(f"SLOW: {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response

# Static file serving for uploaded images
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Register API routers
from app.api import auth, devices, schedules, control, images, unlock_requests, logs, unlock  # noqa
from app.api import checkin, statistics, leave, users, achievements  # noqa
from app.ws.handler import router as ws_router  # noqa

app.include_router(auth.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(schedules.router, prefix="/api")
app.include_router(control.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(unlock_requests.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(unlock.router, prefix="/api")
app.include_router(checkin.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(leave.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(achievements.router, prefix="/api")
app.include_router(ws_router) # WebSocket prefix /ws is already defined in handler


# Endpoint to reload schedules after changes
from fastapi import Depends
from app.services.auth_service import require_admin

@app.post("/api/schedules/reload", tags=["时间策略"])
def reload_schedules(admin: User = Depends(require_admin)):
    """重新加载所有定时策略"""
    load_schedules()
    return {"message": "策略已重新加载"}


@app.get("/api/schedules/jobs", tags=["时间策略"])
def get_scheduler_jobs(admin: User = Depends(require_admin)):
    """查看当前调度器中的所有任务（用于调试）"""
    return {"jobs": list_jobs()}


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        privileged = db.query(User).filter(User.role.in_(["admin", "principal"])).all()
        head_teachers = db.query(User).filter(User.role == "head_teacher").limit(10).all()
        return {
            "status": "ok", 
            "version": settings.APP_VERSION,
            "user_count": user_count,
            "privileged": [{"u": u.username, "e": u.employee_id, "r": u.role} for u in privileged],
            "head_teachers": [{"u": u.username, "e": u.employee_id, "r": u.role} for u in head_teachers]
        }
    finally:
        db.close()


def _ensure_admin_exists():
    """Create default admin user if no admin exists."""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="系统管理员",
                role="admin",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
def _ensure_principals_exist():
    """Ensure principal accounts exist for management viewing. Removed xz01/xz02."""
    db = SessionLocal()
    try:
        # Cleanup old accounts if they exist
        for old_user in ["xz01", "xz02"]:
            user = db.query(User).filter(User.username == old_user).first()
            if user:
                db.delete(user)
                logger.info(f"Cleaned up old account: {old_user}")
        db.commit()
    except Exception as e:
        logger.error(f"Error cleaning up old accounts: {e}")
        db.rollback()
    finally:
        db.close()
