'''asana number nerdx'''

from functools import lru_cache

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


#  SETTINGS

class AsanaOauthEnv(BaseSettings):
    '''asana oauth2 variables'''
    client_id: str = "1203721176797529"

    class Config:
        '''read variables from dotenv file'''
        env_file = ".env"


@lru_cache()
def get_asana_oauth_env():
    '''get_asana_oauth_env'''
    return AsanaOauthEnv()


# ROUTES

@app.get("/")
async def root():
    '''root'''
    return RedirectResponse("/home")


@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, asana_oauth_env: AsanaOauthEnv = Depends(get_asana_oauth_env)):
    '''home'''
    authorize_asana_url = get_authorize_asana_url(asana_oauth_env=asana_oauth_env)
    return templates.TemplateResponse("index.html", {"request": request, "authorize_asana_url": authorize_asana_url})


# HELPER


def get_authorize_asana_url(asana_oauth_env: AsanaOauthEnv) -> str:
    '''generates the href link to begin the oauth grant'''
    asana_oauth_link = "https://app.asana.com/-/oauth_authorize"
    redirect_uri = "https://n4w6bi.deta.dev/oauth/callback"
    response_type = "code"
    state = "thisIsARandomString"
    code_challenge_method = "S256"
    code_challenge = "671608a33392cee13585063953a86d396dffd15222d83ef958f43a2804ac7fb2"
    scope = "default"
    return (""
            + f"{asana_oauth_link}"
            + f"?client_id={asana_oauth_env.client_id}"
            + f"&redirect_uri={redirect_uri}"
            + f"&response_type={response_type}"
            + f"&state={state}"
            + f"&code_challenge_method={code_challenge_method}"
            + f"&code_challenge={code_challenge}"
            + f"&scope={scope}"
            )
