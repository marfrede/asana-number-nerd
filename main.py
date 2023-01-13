from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    return RedirectResponse("/home")


@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "oauth_url": get_oauth_url()})


def get_oauth_url() -> str:
    client_id = "1203713968616919"
    redirect_uri = "http://127.0.0.1:8000"
    response_type = "code"
    state = "thisIsARandomString"
    code_challenge_method = "S256"
    code_challenge = "671608a33392cee13585063953a86d396dffd15222d83ef958f43a2804ac7fb2"
    scope = "default"
    return (
        f"https://app.asana.com/-/oauth_authorize"
        + f"?client_id={client_id}"
        + f"&redirect_uri={redirect_uri}"
        + f"&response_type={response_type}"
        + f"&state={state}"
        + f"&code_challenge_method={code_challenge_method}"
        + f"&code_challenge={code_challenge}"
        + f"&scope={scope}"
    )
