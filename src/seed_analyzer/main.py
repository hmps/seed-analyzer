"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from seed_analyzer.api.routes import router

app = FastAPI(
    title="Seed Analysis API",
    description="API for analyzing seed dimensions from images on millimeter grid paper",
    version="0.1.0",
)

# Get the static directory path
STATIC_DIR = Path(__file__).parent / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Serve the frontend."""
    return FileResponse(STATIC_DIR / "index.html")
