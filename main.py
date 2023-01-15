'''asana number nerdx'''

from functools import lru_cache
from typing import TypedDict, Union

from asana import Client as AsanaClient
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="KpGtHMS3XgH5b7z9us!@e79GlY$b")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


#  SETTINGS

class Env(BaseSettings):
    '''env variables'''
    # asana app oauth2
    number_nerd_callback: str = "https://www.asana-number-nerd.com/oauth/callback"
    client_id: str = "1203721176797529"
    client_secret: str

    # deta project
    deta_project_key: str

    class Config:
        '''read variables from dotenv file'''
        env_file = ".env"


@lru_cache()
def get_env():
    '''get env variables'''
    return Env()


# CLASSES

class AsanaTokenData(TypedDict):
    '''part of asana token'''
    id: str  # e.g. "4673218951",
    name: str  # e.g. "Greg Sanchez",
    email: str  # e.g. "gsanchez@example.com"


class AsanaToken(TypedDict):
    '''asana token as it is returned from asana endpoint'''
    access_token: str  # e.g. "f6ds7fdsa69ags7ag9sd5a",
    expires_in: int  # e.g. 3600,
    token_type: str  # e.g. "bearer",
    refresh_token: str  # e.g. "hjkl325hjkl4325hj4kl32fjds",
    data: AsanaTokenData


# ROUTES


@app.get("/home", response_class=RedirectResponse)
async def root():
    '''redirect /home to / where the homepage is'''
    return RedirectResponse("/")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, env: Env = Depends(get_env)):
    '''
        homepage
        display the asana number nerd (ann) description
        display href button to auth ann with the users private asana account
    '''
    asana_client: AsanaClient = create_asana_client(env)
    url, state = await get_authorize_asana_url(asana_client)
    request.session["state"] = state
    return templates.TemplateResponse("index.html", {"request": request, "authorize_asana_url": url})


@app.get("/oauth/callback", response_class=RedirectResponse)
async def oauth_callback(
    request: Request,
    code: Union[str, None] = None,
    state: Union[str, None] = None,
    env: Env = Depends(get_env)
):
    '''
        callback ednpoint for asanas oauth step 1
        after the user grants permission (allows) (or denies) the asana api will
        return a code which is needed to obtain a login_token of the user.
        It will also return the state which is needed in order to verify that the response is in fact
        coming back from where it startet (same http session)
    '''
    if not code or not state or not request.session.get("state", None) == state:
        return RedirectResponse("/")
    asana_client: AsanaClient = create_asana_client(env)
    access_token: AsanaToken = asana_client.session.fetch_token(code=code)
    asana_user: AsanaTokenData = access_token["data"]
    request.session["asana_user"] = asana_user
    return RedirectResponse("/setup")


@app.get("/setup", response_class=HTMLResponse)
async def setup(request: Request):
    '''site for the authenticated user'''
    asana_user: AsanaTokenData = request.session.get("asana_user")
    return templates.TemplateResponse("setup.html", {"request": request, "asana_user": asana_user})


# HELPER


async def get_authorize_asana_url(client: AsanaClient):
    '''
        generates the asana url to begin the oauth grant
        cerates a random state string
        attaches state to url
    '''
    (url, state) = client.session.authorization_url()
    return (url, state)


def create_asana_client(env: Env) -> AsanaClient:
    '''cerate specific http client for asana API'''
    return AsanaClient.oauth(
        client_id=env.client_id,
        client_secret=env.client_secret,
        redirect_uri=env.number_nerd_callback
    )
