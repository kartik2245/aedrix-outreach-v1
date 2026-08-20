"""
main.py
FastAPI Application Entry Point for Aedrix AI Cold Outreach Operator Dashboard (Python 3.12).
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.dashboard import router as dashboard_router
from app.api.leads import router as leads_router
from app.api.approvals import router as approvals_router
from app.api.campaigns import router as campaigns_router
from app.api.system import router as system_router
from app.api.icp import router as icp_router
from app.api.demo import router as demo_router

app = FastAPI(
    title="Aedrix AI Cold Outreach Operator API",
    description="Backend bridge connecting React operator frontend to existing Aedrix intelligence, approval, and outreach engines.",
    version="1.0.0"
)

# Configure CORS for local development (Vite frontend on 5173 / localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(dashboard_router, prefix="/api")
app.include_router(leads_router, prefix="/api")
app.include_router(approvals_router, prefix="/api")
app.include_router(campaigns_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(icp_router, prefix="/api")
app.include_router(demo_router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Aedrix Cold Outreach API",
        "mode": "DEMO / DRY RUN",
        "safety_guard": "SEND_EMAILS=false"
    }


# Serve static built frontend files if available in frontend/dist
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dist = os.path.join(base_dir, "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
