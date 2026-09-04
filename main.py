import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import os
from config import REFRESH_HOURS, ALLOWED_ORIGINS, HOST, PORT
from app.services import store
from app.routers import api

scheduler = AsyncIOScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # initial warm-up (network calls run in a thread so the server starts fast)
    warm = asyncio.create_task(store.refresh_all())
    warm_argo = asyncio.create_task(store.refresh_argo())

    scheduler.add_job(store.refresh_all, "interval", hours=REFRESH_HOURS, id="fields")
    scheduler.add_job(store.refresh_argo, "interval", hours=3, id="argo")
    scheduler.start()

    yield

    scheduler.shutdown()
    warm.cancel()
    warm_argo.cancel()


app = FastAPI(
    title="Ocean 3D Data Backend",
    description="Serves temperature / salinity / currents / SSH / waves / Argo / glider data "
                "for a 3D ocean visualization frontend.",
    version="1.0.0",
    lifespan=lifespan,
)

# Production CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True if ALLOWED_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router)


@app.get("/health")
async def health_check():
    """Root health check for Render/cloud deployment monitoring."""
    return {"status": "ok", "service": "pelagos-backend", "version": store.store.version}


# Mount static/ if available, otherwise serve a rich API landing page
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir) and os.path.exists(os.path.join(static_dir, "index.html")):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
else:
    @app.get("/")
    async def root():
        return {
            "name": "PELAGOS Ocean 3D API",
            "status": "online",
            "docs": "/docs",
            "health": "/health",
            "meta": "/api/meta",
            "frontend_tip": "Deploy the frontend directory to Vercel and set API_BASE to this service URL."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT)