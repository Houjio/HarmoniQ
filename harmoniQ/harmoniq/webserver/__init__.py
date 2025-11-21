from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pathlib import Path

from harmoniq.webserver.REST import router as api_router

ASSET_FILE = Path(__file__).parent / "assets"
STATIC_FILE = ASSET_FILE / "static"
TEMPLATES_FILE = ASSET_FILE / "templates"

app = FastAPI(
    title="HarmoniQ",
    description="Outil de modélisation de production d'énergie au Québec",
    version="0.1",
    contact={
        "name": "Sébastien Dasys",
        "email": "sebastien.dasys@polymtl.ca",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)
app.mount("/static", StaticFiles(directory=STATIC_FILE), name="static")

templates = Jinja2Templates(directory=ASSET_FILE)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/index_2", response_class=HTMLResponse)
def index_2(request: Request):
    return templates.TemplateResponse(request=request, name="index_2.html")


@app.get("/favicon.ico", response_class=FileResponse)
def favicon():
    print(STATIC_FILE / "favicon" / "favicon.ico")
    return FileResponse(STATIC_FILE / "favicon" / "favicon.ico")


@app.get("/à-propos", response_class=HTMLResponse)
def à_propos(request: Request):
    return templates.TemplateResponse(request=request, name="about.html")


@app.get("/about_2", response_class=HTMLResponse)
def about_2(request: Request):
    return templates.TemplateResponse(request=request, name="about_2.html")


@app.get("/documentation", response_class=HTMLResponse)
def documentation(request: Request):
    return templates.TemplateResponse(request=request, name="docs.html")


@app.get("/documentation_2", response_class=HTMLResponse)
def documentation_2(request: Request):
    return templates.TemplateResponse(request=request, name="documentation_2.html")


@app.get("/documentation_modern", response_class=HTMLResponse)
def documentation_modern(request: Request):
    return templates.TemplateResponse(request=request, name="documentation_modern.html")


@app.get("/installation_guide", response_class=HTMLResponse)
def installation_guide(request: Request):
    return templates.TemplateResponse(request=request, name="installation_guide.html")


@app.get("/modules_guide", response_class=HTMLResponse)
def modules_guide(request: Request):
    return templates.TemplateResponse(request=request, name="modules_guide.html")


@app.get("/api_guide", response_class=HTMLResponse)
def api_guide(request: Request):
    return templates.TemplateResponse(request=request, name="api_guide.html")


@app.get("/app", response_class=HTMLResponse)
def application(request: Request):
    return templates.TemplateResponse(request=request, name="app.html")


@app.get("/app_2", response_class=HTMLResponse)
def application_2(request: Request):
    return templates.TemplateResponse(request=request, name="app_2.html")


@app.get("/Eloise", response_class=HTMLResponse)
def eloisepage(request: Request):
    return templates.TemplateResponse(request=request, name="elo.html")


@app.exception_handler(404)
def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"message": "Not Found"})
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


# Ajoute les endpoints de REST.py
app.include_router(api_router)
