"""
Facial Animation Dashboard endpoint
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/facial-animation", tags=["facial-animation"])

@router.get("/dashboard")
async def get_facial_animation_dashboard():
    """Serve the facial animation dashboard HTML"""
    dashboard_path = os.path.join(
        os.path.dirname(__file__), 
        "..", "..", "static", "facial_animation_dashboard.html"
    )
    return FileResponse(
        dashboard_path, 
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )