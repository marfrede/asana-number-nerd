'''asana number nerdx'''

import json
from functools import lru_cache
from typing import Coroutine, List, Literal, TypedDict, Union

import requests
from asana import Client as AsanaClient
from deta import Deta
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings
from starlette.middleware.sessions import SessionMiddleware

# init fastapi
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="KpGtHMS3XgH5b7z9us!@e79GlY$b")
app.mount("/static", StaticFiles(directory="static"), name="static")

# init jinja templates
templates = Jinja2Templates(directory="templates")

# init deta databse
deta = Deta()
db = deta.Base("ann_db")  # This how to connect to or create a database.


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

class AsanaUser(TypedDict):
    '''part of asana token'''
    id: str  # e.g. "4673218951",
    name: str  # e.g. "Greg Sanchez",
    email: str  # e.g. "gsanchez@example.com"


class AsanaToken(TypedDict):
    '''asana token as it is returned from asana fetch_token endpoint'''
    access_token: str  # e.g. "f6ds7fdsa69ags7ag9sd5a",
    expires_in: int  # e.g. 3600,
    token_type: str  # e.g. "bearer",
    refresh_token: str  # e.g. "hjkl325hjkl4325hj4kl32fjds",
    data: AsanaUser


class AsanaTokenNoRefresh(TypedDict):
    '''asana token as it is returned from asana refresh_token endpoint'''
    access_token: str  # e.g. "f6ds7fdsa69ags7ag9sd5a",
    expires_in: int  # e.g. 3600,
    token_type: str  # e.g. "bearer",
    data: AsanaUser


class AsanaObject(TypedDict):
    '''asana workspace from asana API'''
    gid: str  # e.g. "12345"
    resource_type: Literal["workspace", "project"]
    name: str  # e.g. "My Company Workspace


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
    asana_client_oauth: AsanaClient = create_asana_client_oauth(env)
    url, state = await get_authorize_asana_url(asana_client_oauth)
    request.session["state"] = state
    return templates.TemplateResponse("index.jinja2", {"request": request, "authorize_asana_url": url})


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

    # fetch auth_token for user
    asana_client_oauth: AsanaClient = create_asana_client_oauth(env)
    access_token: AsanaToken = asana_client_oauth.session.fetch_token(code=code)

    # store auth_token in db and db key in session
    asana_user_id: str = access_token['data']["id"]
    request.session['asana_user_id'] = asana_user_id
    db.put(access_token, f"user_{asana_user_id}")
    return RedirectResponse("/setup")


@app.get("/setup", response_class=HTMLResponse)
async def setup(request: Request, env: Env = Depends(get_env)):
    '''site for the authenticated user'''
    asana_user_id: str = request.session.get("asana_user_id")
    access_token: AsanaToken = db.get(f"user_{asana_user_id}")
    pat = refresh_asana_client_pat(access_token=access_token, env=env)
    asana_user: AsanaUser = access_token["data"]
    workspaces: List[AsanaObject] = asana_api_get(url="https://app.asana.com/api/1.0/workspaces", pat=pat)
    for workspace in workspaces:
        projects: List[AsanaObject] = asana_api_get(url=f"https://app.asana.com/api/1.0/workspaces/{workspace['gid']}/projects", pat=pat)
        projects_json: List[str] = list(map(json.dumps, projects))
        workspace["projects"] = projects
        workspace["projects_json"] = projects_json
    return templates.TemplateResponse("setup.jinja2", {
        "request": request,
        "asana_user": asana_user,
        "workspaces": workspaces,
    })


@app.post("/projects/read")
async def read_projects(request: Request):
    '''site for the authenticated user'''
    projects: List[AsanaObject] = await read_projects_json(request=request)
    return projects

# HELPER


async def get_authorize_asana_url(client_oauth: AsanaClient):
    '''
        generates the asana url to begin the oauth grant
        cerates a random state string
        attaches state to url
    '''
    (url, state) = client_oauth.session.authorization_url()
    return (url, state)


def create_asana_client_oauth(env: Env) -> AsanaClient:
    '''cerate specific http client for asana API with oauth for login'''
    return AsanaClient.oauth(
        client_id=env.client_id,
        client_secret=env.client_secret,
        redirect_uri=env.number_nerd_callback
    )


def refresh_asana_client_pat(access_token: AsanaToken, env: Env) -> str:
    '''
        refresh asana access_token (pat) with refresh_token
        save new access_token object in db
        return only the pat
    '''
    response = requests.post(url="https://app.asana.com/-/oauth_token", data={
        'grant_type': 'refresh_token',
        'client_id': env.client_id,
        'client_secret': env.client_secret,
        'redirect_uri': env.number_nerd_callback,
        'refresh_token': access_token["refresh_token"]
    }, timeout=5)
    new_access_token: AsanaTokenNoRefresh = response.json()
    pat: str = new_access_token["access_token"]
    access_token["access_token"] = pat
    db.put(access_token, f"user_{access_token['data']['id']}")
    return pat


def asana_api_get(url: str, pat: str) -> List[AsanaObject]:
    '''a general asana api get request to a given url'''
    response = requests.get(
        url=url,
        headers={
            'Accept': 'application/json',
            'Authorization': f'Bearer {pat}'
        }, timeout=5
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return None


async def read_projects_json(request: Request) -> Coroutine[List[AsanaObject], None, None]:
    '''read project ids selected inside form'''
    form = await request.form()
    return list(map(json.loads, list(form.keys())))
