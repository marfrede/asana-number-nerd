'''asana number nerdx'''

import random
import string
from functools import lru_cache
from typing import Union

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="some-random-string")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


#  SETTINGS

class OauthEnv(BaseSettings):
    '''oauth2 variables'''
    number_nerd_url: str = "https://n4w6bi.deta.dev"
    client_id: str = "1203721176797529"

    class Config:
        '''read variables from dotenv file'''
        env_file = ".env"


@lru_cache()
def get_oauth_env():
    '''get_oauth_env'''
    return OauthEnv()


# ROUTES

@app.get("/")
async def root():
    '''root'''
    return RedirectResponse("/home")


@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, oauth_env: OauthEnv = Depends(get_oauth_env)):
    '''
        display the asana number nerd home page with description and option ask
        asana to authorize this app with the users private asana account
    '''
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(40))
    request.session["state"] = state
    authorize_asana_url = get_authorize_asana_url(oauth_env=oauth_env, state=state)
    return templates.TemplateResponse("index.html", {"request": request, "authorize_asana_url": authorize_asana_url})


@app.get("/oauth/callback")
async def oauth_callback(request: Request, code: Union[str, None] = None, state: Union[str, None] = None):
    '''
        callback ednpoint for asanas oauth step 1
        after the user grants permission (allows) (or denies) the asana api will
        return a code which is needed to obtain a login_token of the user.
        It will also return the state which is needed in order to verify that the response is in fact
        coming back from where it startet (same http session)
    '''
    if not code or not state or not request.session.get("state", None) == state:
        return RedirectResponse("/")
    request.session["code"] = code
    return {"success: ": code}


# HELPER


def get_authorize_asana_url(oauth_env: OauthEnv, state: str) -> str:
    '''generates the href link to begin the oauth grant'''
    asana_oauth_link = "https://app.asana.com/-/oauth_authorize"
    redirect_uri = f"{oauth_env.number_nerd_url}/oauth/callback"
    response_type = "code"
    code_challenge_method = "S256"
    code_challenge = "671608a33392cee13585063953a86d396dffd15222d83ef958f43a2804ac7fb2"
    scope = "default"
    return (""
            + f"{asana_oauth_link}"
            + f"?client_id={oauth_env.client_id}"
            + f"&redirect_uri={redirect_uri}"
            + f"&response_type={response_type}"
            + f"&state={state}"
            + f"&code_challenge_method={code_challenge_method}"
            + f"&code_challenge={code_challenge}"
            + f"&scope={scope}"
            )
