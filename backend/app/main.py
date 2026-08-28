import logging

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api import admin, agent, charts, cluster_admin, config_admin, dashboard, data, reports, saml
from .core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown events."""
    # Startup: Preload shared datastore
    logger.info("Starting application...")
    logger.info("Preloading shared datastore (this may take a moment)...")
    try:
        from .datastore_singleton import get_datastore
        datastore = get_datastore()
        logger.info(f"Shared datastore loaded successfully. Hostnames: {datastore.get_hostnames()}")
    except Exception as e:
        logger.error(f"Failed to preload datastore: {e}")
        import traceback
        logger.error(traceback.format_exc())

    yield

    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="API for Slurm Usage History Dashboard with data ingestion capabilities",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent.router, prefix=f"{settings.api_prefix}", tags=["Agent"])
app.include_router(data.router, prefix=f"{settings.api_prefix}/data", tags=["Data Ingestion"])
app.include_router(dashboard.router, prefix=f"{settings.api_prefix}/dashboard", tags=["Dashboard"])
app.include_router(charts.router, prefix=f"{settings.api_prefix}/dashboard", tags=["Charts"])
app.include_router(reports.router, prefix=f"{settings.api_prefix}/reports", tags=["Reports"])
app.include_router(admin.router, prefix=f"{settings.api_prefix}/admin", tags=["Admin"])
app.include_router(config_admin.router, prefix=f"{settings.api_prefix}/admin", tags=["Config Admin"])
app.include_router(cluster_admin.router, prefix=f"{settings.api_prefix}/admin", tags=["Cluster Admin"])
app.include_router(saml.router, prefix="/saml", tags=["SAML Authentication"])


# Serve static frontend files
# Try multiple possible locations for frontend dist directory
frontend_dist = None
possible_paths = [
    Path(__file__).parent.parent.parent / "frontend" / "dist",  # Development
    Path(__file__).parent / "static",  # Packaged with backend
]

for path in possible_paths:
    if path.exists() and path.is_dir():
        frontend_dist = path
        logger.info(f"Found frontend at: {frontend_dist}")
        break

if frontend_dist:
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    # Serve root images
    @app.get("/vite.svg")
    async def vite_svg():
        return FileResponse(frontend_dist / "vite.svg")

    @app.get("/REIT_logo.png")
    async def reit_logo():
        return FileResponse(frontend_dist / "REIT_logo.png")

    # Serve index.html at root
    @app.get("/")
    async def serve_root():
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Frontend not found"}

    # Catch-all route to serve index.html for React Router (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Don't intercept API routes, docs, or SAML
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("saml") or full_path.startswith("openapi.json"):
            # Let FastAPI handle these routes
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")

        # Serve index.html for all other routes (React Router handles routing)
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        return {"message": "Frontend not found"}
else:
    logger.warning("Frontend dist directory not found. Frontend will not be served.")

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Slurm Usage History API",
            "version": settings.api_version,
            "docs": "/docs",
        }


@app.get("/api")
async def api_info():
    """API information."""
    return {
        "title": settings.api_title,
        "version": settings.api_version,
        "endpoints": {
            "data_ingestion": f"{settings.api_prefix}/data/ingest",
            "health": f"{settings.api_prefix}/dashboard/health",
            "metadata": f"{settings.api_prefix}/dashboard/metadata",
            "filter": f"{settings.api_prefix}/dashboard/filter",
            "stats": f"{settings.api_prefix}/dashboard/stats/{{hostname}}",
        },
    }
