import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add project root to sys.path so 'server.X' absolute imports work when run as a script
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from dotenv import load_dotenv
load_dotenv()

from server.data_service import get_data_service
from server.backend_api import app

logger = logging.getLogger("DigitalTwin")
service = get_data_service()
client_dist = project_root / "client" / "dist"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        logger.warning("Invalid %s value; using %s", name, default)
        return default


@asynccontextmanager
async def lifespan(_app):
    simulation_enabled = os.environ.get("SIMULATION_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if simulation_enabled:
        service.start_simulation(interval=_env_int("SIMULATION_INTERVAL", 1))
    try:
        yield
    finally:
        service.stop_simulation()


# Add lifecycle management to the shared backend app without starting work at import time.
app.router.lifespan_context = lifespan

if client_dist.exists():
    assets_dir = client_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")

        requested_file = client_dist / full_path
        if full_path and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(client_dist / "index.html")

    logger.info("Mounted production build from %s", client_dist)
else:
    logger.warning("Production build not found at %s; server running in API-only mode.", client_dist)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=_env_int("API_PORT", 8000),
        reload=False,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )
