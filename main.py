'''asana number nerdx'''

from functools import lru_cache
from typing import Union

import asana
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
    number_nerd_url: str = "https://www.asana-number-nerd.com/oauth/callback"
    client_id: str = "1203721176797529"
    client_secret: str

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
    (url, state) = await get_authorize_asana_url(oauth_env=oauth_env)
    request.session["state"] = state
    return templates.TemplateResponse("index.html", {"request": request, "authorize_asana_url": url, 'state': state})


@app.get("/oauth/callback")
async def oauth_callback(request: Request, code: Union[str, None] = None, state: Union[str, None] = None, oauth_env: OauthEnv = Depends(get_oauth_env)):
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


async def get_authorize_asana_url(oauth_env: OauthEnv):
    '''
        generates the asana url to begin the oauth grant
        cerates a random state string
        attaches state to url
    '''
    client = asana.Client.oauth(
        client_id=oauth_env.client_id,
        client_secret=oauth_env.client_secret,
        redirect_uri=oauth_env.number_nerd_url

    )
    (url, state) = client.session.authorization_url()
    return (url, state)
