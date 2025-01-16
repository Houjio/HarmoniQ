from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pathlib import Path

from harmoniq.webserver.REST import router as api_router

ASSET_FILE = Path(__file__).parent / "assets"
STATIC_FILE = ASSET_FILE / "static"
TEMPLATES_FILE = ASSET_FILE / "templates"


app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_FILE), name="static")

templates = Jinja2Templates(directory=ASSET_FILE)


@app.on_event("shutdown")
async def shutdown_event():
    app.state.client.close()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# Ajoute les endpoints de REST.py
app.include_router(api_router)
