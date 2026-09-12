from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

_DASHBOARD_HTML_PATH = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"
_dashboard_html = _DASHBOARD_HTML_PATH.read_text()


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return _dashboard_html
