import os
import time
import threading
from datetime import datetime, timedelta, timezone
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    BackgroundTasks,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc
from typing import List, Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler


from . import models, log_collector
from .models import LogEntryRead, PaginatedLogResponse, UserRead
from .database import init_db, SessionLocal
from . import auth

logger = log_collector.logger
scheduler = BackgroundScheduler(daemon=True)


# --- Status management for log collection ---
log_collection_status = "idle"
status_lock = threading.Lock()


def set_collection_status(new_status: str):
    global log_collection_status
    with status_lock:
        log_collection_status = new_status
    logger.info(f"Log collection status changed to: {new_status}")


def get_collection_status() -> str:
    with status_lock:
        return log_collection_status


def run_log_collection_with_status():
    if get_collection_status() == "running":
        logger.warning("Log collection is already running. Skipping new trigger.")
        return
    logger.info("Starting background log collection...")
    # Set status to running before starting the collection
    set_collection_status("running")
    try:
        log_collector.process_log_files()
        set_collection_status("finished")
    except Exception as e:
        logger.error(f"Error during background log collection: {e}", exc_info=True)
        set_collection_status("error")


# --- End of status management ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FastAPI application...")
    logger.info("Initializing database...")
    init_db()  # Ensure that check_same_thread=False is set in the engine!
    logger.info("Database initialized.")

    db = SessionLocal()
    try:
        auth.seed_admin_user(db)
    finally:
        db.close()

    set_collection_status("idle")  # Initialize status at startup
    try:
        interval_minutes = int(os.getenv("LOG_COLLECTION_INTERVAL_MINUTES", "10"))
        logger.info(f"Scheduling log collection every {interval_minutes} minutes.")
        scheduler.add_job(
            run_log_collection_with_status,
            "interval",
            minutes=interval_minutes,
            id="log_collection_job",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Scheduler started.")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}", exc_info=True)
    yield
    logger.info("Shutting down FastAPI application...")
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")
    log_collector.close_geoip_reader()
    logger.info("Application stopped.")


app = FastAPI(
    title="Server Access Dashboard API",
    description="API for retrieving and managing server access logs",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
# Origins the frontend lives on (cross-origin). Bearer-token auth uses the
# Authorization header, not cookies, so credentials=False is correct; leave it
# True only if you later switch to cookie sessions. Restrict via
# CORS_ORIGINS="http://FE:5577,https://FE.example.com" in compose.
_cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5577")
origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Routes ---


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


@app.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Obtain access & refresh tokens",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(auth.get_db),
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(user.username)
    refresh_token = auth.create_refresh_token(user.username)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=auth.get_user_read(user),
    )


@app.post(
    "/auth/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a valid refresh token",
)
async def refresh_token(
    user: models.User = Depends(auth.get_current_refresh_user),
):
    access_token = auth.create_access_token(user.username)
    refresh_token = auth.create_refresh_token(user.username)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=auth.get_user_read(user),
    )


@app.get(
    "/auth/me",
    response_model=UserRead,
    summary="Get current authenticated user",
    dependencies=[Depends(auth.get_current_user)],
)
async def get_me(
    user: models.User = Depends(auth.get_current_user),
):
    return auth.get_user_read(user)


@app.post(
    "/auth/logout",
    summary="Logout (client discards tokens)",
    dependencies=[Depends(auth.get_current_user)],
)
async def logout():
    return {"message": "Logged out"}


# --- API Routes ---


# Manual Trigger Endpoint
@app.post(
    "/collect-logs/",
    status_code=202,
    summary="Manually trigger log collection",
    dependencies=[Depends(auth.get_current_user)],
)
async def trigger_log_collection(background_tasks: BackgroundTasks):
    current_status = get_collection_status()
    if current_status == "running":
        logger.warning("Manual trigger ignored: Log collection is already running.")
        # Return a specific status so the frontend knows it's already running
        # Or raise a 409 Conflict error
        # return {"message": "Log collection is already running."}
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Log collection is already running.",
        )
    logger.info("Manual trigger for log collection received (authenticated).")
    background_tasks.add_task(run_log_collection_with_status)
    return {"message": "Log collection process started in the background."}


# Status Endpoint
class CollectionStatusResponse(BaseModel):
    status: str


@app.get(
    "/collect-logs/status",
    response_model=CollectionStatusResponse,
    summary="Retrieve current status of log collection",
    dependencies=[Depends(auth.get_current_user)],
)
async def get_log_collection_status():
    current_status = get_collection_status()
    # Status is only reset if it is finished/error,
    # so that polling does not immediately see "idle" again.
    if current_status in ["finished", "error"]:
        set_collection_status("idle")
    return CollectionStatusResponse(status=current_status)


# GET /logs/ Endpoint
@app.get(
    "/logs/",
    response_model=PaginatedLogResponse,
    summary="Retrieve processed log entries",
    dependencies=[Depends(auth.get_current_user)],
)
async def read_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    ip_address: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    status_code: Optional[int] = Query(None),
    sort_by: Optional[str] = Query("timestamp"),
    sort_dir: Optional[str] = Query("desc"),
    db: Session = Depends(auth.get_db),
):
    logger.debug("GET /logs/ called...")
    try:
        base_query = db.query(models.LogEntry)
        if ip_address:
            base_query = base_query.filter(
                models.LogEntry.ip_address.ilike(f"%{ip_address}%")
            )
        if country:
            base_query = base_query.filter(
                models.LogEntry.country.ilike(f"%{country}%")
            )
        if domain:
            base_query = base_query.filter(models.LogEntry.domain.ilike(f"%{domain}%"))
        if status_code is not None:
            base_query = base_query.filter(models.LogEntry.status_code == status_code)
        total_count = base_query.count()
        sort_column = getattr(models.LogEntry, sort_by, models.LogEntry.timestamp)
        ordered_query = base_query.order_by(
            asc(sort_column) if sort_dir == "asc" else desc(sort_column)
        )
        logs = ordered_query.offset(skip).limit(limit).all()
        return PaginatedLogResponse(logs=logs, total_count=total_count)
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error while retrieving logs."
        )


# Country Summary Endpunkt
class CountrySummary(BaseModel):
    country: Optional[str] = "Unknown"
    count: int


@app.get(
    "/logs/summary/by-country/",
    response_model=List[CountrySummary],
    summary="Summarize accesses per country",
    dependencies=[Depends(auth.get_current_user)],
)
async def get_summary_by_country(db: Session = Depends(auth.get_db)):
    logger.debug("GET /logs/summary/by-country/ called")
    try:
        summary_query = (
            db.query(
                models.LogEntry.country, func.count(models.LogEntry.id).label("count")
            )
            .group_by(models.LogEntry.country)
            .order_by(func.count(models.LogEntry.id).desc())
        )
        summary_results_raw = summary_query.all()
        summary_results = [
            CountrySummary(
                country=country if country is not None else "Unknown", count=count
            )
            for country, count in summary_results_raw
        ]
        return summary_results
    except Exception as e:
        logger.error(f"Error retrieving country summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving country summary.",
        )


# --- Chart data responses ---


class TimeSeriesPoint(BaseModel):
    """One bucketed data point for the time-series chart: accesses
    for a single domain within one time bucket."""

    bucket: str
    domain: Optional[str] = None
    count: int = 0


class SiteCountryCount(BaseModel):
    """One (site, country) pair and how often it was accessed."""

    domain: str
    country: Optional[str] = None
    count: int = 0


class StatusCount(BaseModel):
    """One HTTP status-code value and how often it occurred."""

    status_code: Optional[int] = None
    count: int = 0


def _time_window_days(days: int) -> datetime:
    """Return the UTC cutoff datetime (naive, matching SQLite storage) for the
    supplied look-back window in days."""
    days = max(days, 1)
    return datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def _apply_log_filters(query, ip_address, country, domain, status_code):
    """Apply the shared log-filter predicates to a query (in place)."""
    if ip_address:
        query = query.filter(models.LogEntry.ip_address.ilike(f"%{ip_address}%"))
    if country:
        query = query.filter(models.LogEntry.country.ilike(f"%{country}%"))
    if domain:
        query = query.filter(models.LogEntry.domain.ilike(f"%{domain}%"))
    if status_code is not None:
        query = query.filter(models.LogEntry.status_code == status_code)
    return query


# GET /logs/summary/timeseries/
@app.get(
    "/logs/summary/timeseries/",
    response_model=List[TimeSeriesPoint],
    summary="Bucketed accesses over time per domain",
    dependencies=[Depends(auth.get_current_user)],
)
async def get_timeseries(
    bucket: str = Query("day", pattern="^(hour|day)$"),
    days: int = Query(30, ge=1, le=90),
    domain: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    status_code: Optional[int] = Query(None),
    db: Session = Depends(auth.get_db),
):
    logger.debug("GET /logs/summary/timeseries/ called")
    try:
        cutoff = _time_window_days(days)
        # SQLite exposes strftime() for date/time bucketing; keeping this a single
        # grouped SELECT avoids pulling raw rows into Python.
        if bucket == "hour":
            bucket_expr = func.strftime("%Y-%m-%d %H:00:00", models.LogEntry.timestamp)
        else:
            bucket_expr = func.strftime("%Y-%m-%d", models.LogEntry.timestamp)
        query = (
            db.query(
                bucket_expr.label("bucket"),
                models.LogEntry.domain,
                func.count(models.LogEntry.id).label("count"),
            )
            .filter(models.LogEntry.timestamp >= cutoff)
            .group_by(bucket_expr, models.LogEntry.domain)
            .order_by(asc(bucket_expr), asc(models.LogEntry.domain))
        )
        query = _apply_log_filters(query, None, country, domain, status_code)
        return [
            TimeSeriesPoint(bucket=bucket_str, domain=domain, count=count)
            for bucket_str, domain, count in query.all()
        ]
    except Exception as e:
        logger.error(f"Error retrieving time-series summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving time-series summary.",
        )


# GET /logs/summary/by-site-country/
@app.get(
    "/logs/summary/by-site-country/",
    response_model=List[SiteCountryCount],
    summary="Accesses per site and country",
    dependencies=[Depends(auth.get_current_user)],
)
async def get_summary_by_site_country(
    days: int = Query(30, ge=1, le=90),
    domain: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    db: Session = Depends(auth.get_db),
):
    logger.debug("GET /logs/summary/by-site-country/ called")
    try:
        cutoff = _time_window_days(days)
        query = (
            db.query(
                models.LogEntry.domain,
                models.LogEntry.country,
                func.count(models.LogEntry.id).label("count"),
            )
            .filter(models.LogEntry.timestamp >= cutoff)
            .group_by(models.LogEntry.domain, models.LogEntry.country)
            .order_by(func.count(models.LogEntry.id).desc())
        )
        query = _apply_log_filters(query, None, country, domain, None)
        return [
            SiteCountryCount(domain=domain, country=country, count=count)
            for domain, country, count in query.all()
        ]
    except Exception as e:
        logger.error(f"Error retrieving site-country summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving site-country summary.",
        )


# GET /logs/summary/by-status/
@app.get(
    "/logs/summary/by-status/",
    response_model=List[StatusCount],
    summary="Accesses per HTTP status code",
    dependencies=[Depends(auth.get_current_user)],
)
async def get_summary_by_status(
    days: int = Query(30, ge=1, le=90),
    domain: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    db: Session = Depends(auth.get_db),
):
    logger.debug("GET /logs/summary/by-status/ called")
    try:
        cutoff = _time_window_days(days)
        query = (
            db.query(
                models.LogEntry.status_code,
                func.count(models.LogEntry.id).label("count"),
            )
            .filter(models.LogEntry.timestamp >= cutoff)
            .group_by(models.LogEntry.status_code)
            .order_by(func.count(models.LogEntry.id).desc())
        )
        query = _apply_log_filters(query, None, country, domain, None)
        return [
            StatusCount(status_code=status_code, count=count)
            for status_code, count in query.all()
        ]
    except Exception as e:
        logger.error(f"Error retrieving status summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving status summary.",
        )


# Start the app (for local development)
if __name__ == "__main__":
    import uvicorn

    try:
        from dotenv import load_dotenv

        dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path)
            print(f"Loaded local .env file from: {dotenv_path}")
        else:
            print("No local .env file found.")
        # Check JWT_SECRET
        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            logger.warning(
                "!!! JWT_SECRET not set. Using ephemeral random secret — tokens invalid on restart! !!!"
            )
        # Check ADMIN_PASSWORD
        if not os.getenv("ADMIN_PASSWORD"):
            logger.warning(
                "!!! ADMIN_PASSWORD not set — no admin user will be seeded! !!!"
            )
    except ImportError:
        print("python-dotenv not installed, .env file will not be loaded.")
    print("Starting Uvicorn development server at http://0.0.0.0:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
