'''asana number nerdx'''

import ast
from functools import lru_cache
from typing import Coroutine, List, Literal, Tuple, TypedDict, Union

import requests
from asana import Client as AsanaClient
from deta import Deta
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings
from starlette import status as Status
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
    number_nerd_oauth_callback: str = "https://www.asana-number-nerd.com/oauth/callback"
    number_nerd_webhook_callback: str = "https://www.asana-number-nerd.com/webhook/receive"
    client_id: str = "1203721176797529"
    client_secret: str

    # deta project
    deta_project_key: str

    class Config:
        '''read variables from dotenv file'''
        env_file = ".env"


@ lru_cache()
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


@ app.get("/home", response_class=RedirectResponse)
async def root():
    '''redirect /home to / where the homepage is'''
    return RedirectResponse("/")


@ app.get("/", response_class=HTMLResponse)
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


@ app.get("/oauth/callback", response_class=RedirectResponse)
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
    return RedirectResponse("/choose-projects")


@ app.get("/choose-projects", response_class=HTMLResponse)
async def choose_projects(request: Request, env: Env = Depends(get_env)):
    '''site for the authenticated user'''
    # 1. auth or redirect
    asana_user, pat = get_fresh_logged_in_asana_user(request=request, env=env)
    if (not asana_user or not pat):
        return RedirectResponse("/")
    # 2. respond
    workspaces: List[AsanaObject] = asana_api_get(url="https://app.asana.com/api/1.0/workspaces", pat=pat)
    for workspace in workspaces:
        projects: List[AsanaObject] = asana_api_get(url=f"https://app.asana.com/api/1.0/workspaces/{workspace['gid']}/projects", pat=pat)
        workspace["projects"] = projects
    return templates.TemplateResponse("choose-projects.jinja2", {
        "request": request,
        "asana_user": asana_user,
        "workspaces": workspaces,
    })


@ app.post("/projects/read", response_class=RedirectResponse)
async def read_projects(request: Request):
    '''read chosen projects from form and save to detabase'''
    projects: List[AsanaObject] = await read_projects_from_form(request=request)
    deta_obj = db.put(projects)
    request.session["projects_choosen"] = deta_obj["key"]
    return RedirectResponse("/webhook/create")


# @app.get("/choose-numbering", response_class=HTMLResponse)
# async def choose_numbering(request: Request, env: Env = Depends(get_env)):
#     '''site for the authenticated user'''
#     # 1. auth and validate or redirect
#     asana_user, _ = get_fresh_logged_in_asana_user(request=request, env=env)
#     projects = await read_projects_session_db(request=request)
#     if not asana_user or not projects:
#         return RedirectResponse("/choose-projects")
#     # 2. respond
#     # return templates.TemplateResponse("choose-numbering.jinja2", {
#     #     "request": request,
#     #     "asana_user": asana_user,
#     #     "projects": projects,
#     # })
#     return RedirectResponse("/choose-numbering", status_code=Status.HTTP_302_FOUND)


@ app.post("/webhook/create")
async def create_weebhook(request: Request, env: Env = Depends(get_env)):
    '''create the webhook to listen to create-task events inside given projects'''
    # 1. auth and validate or redirect
    asana_user, pat = get_fresh_logged_in_asana_user(request=request, env=env)
    projects: Union[List[AsanaObject], None] = await read_projects_session_db(request=request, delete_after_read=True)
    if not pat or not projects:
        return RedirectResponse("/choose-projects")
    response = requests.post(
        url="https://app.asana.com/api/1.0/webhooks",
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {pat}'
        },
        data={
            "data": {
                "filters": [
                    {
                        "action": "added",
                        "resource_subtype": "task",
                        "resource_type": "project"
                    }
                ],
                "resource": projects[0]["gid"],
                "target": f"{env.number_nerd_webhook_callback} / {asana_user['id']} / {projects[0]['gid']}"
            }
        },
        timeout=20
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return response.json()


@app.post("/webhook/receive")
async def receive_weebhook(request: Request, response: Response):
    '''callback for asana when task created (and for first handshake)'''
    pat = "1/1199181200186785:d6752d0cc04c304e22d12e0b57163c14"
    secret: Union[str, None] = request.headers.get("X-Hook-Secret")
    if secret:
        # db.put(secret, f"x_hook_secret_{user_gid}_{project_gid}")
        response.status_code = Status.HTTP_204_NO_CONTENT
        response.headers["X-Hook-Secret"] = secret
        return None
    # create a task
    body: dict = await request.json()
    task_created_gid: str = body["events"][0]["resource"]["gid"]
    task_created_name = requests.get(
        timeout=20,
        url=f"https://app.asana.com/api/1.0/tasks/{task_created_gid}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pat}"
        }
    ).json()["data"]["name"]
    requests.put(
        timeout=20,
        url=f"https://app.asana.com/api/1.0/tasks/{task_created_gid}",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {pat}"
        },
        json={
            "data": {
                "name": f"{'1'} {task_created_name}"
            }
        }
    )


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
        redirect_uri=env.number_nerd_oauth_callback
    )


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


def get_fresh_logged_in_asana_user(request: Request, env: Env) -> Tuple[Union[AsanaUser, None], Union[str, None]]:
    '''read user id from session and read user from detabase'''
    asana_user_id: Union[str, None] = request.session.get("asana_user_id", None)
    if not asana_user_id:
        return (None, None)
    access_token: Union[AsanaToken, None] = db.get(f"user_{asana_user_id}")
    if not access_token:
        return (None, None)
    pat: Union[str, None] = refresh_asana_client_pat(access_token=access_token, env=env)
    return (access_token["data"], pat)


def refresh_asana_client_pat(access_token: AsanaToken, env: Env) -> Union[str, None]:
    '''
        refresh asana access_token (pat) with refresh_token
        save new access_token object in db
        return only the pat
        return None when refresh_token invalid (should only be the case when app access was denied)
    '''
    response = requests.post(url="https://app.asana.com/-/oauth_token", data={
        'grant_type': 'refresh_token',
        'client_id': env.client_id,
        'client_secret': env.client_secret,
        'redirect_uri': env.number_nerd_oauth_callback,
        'refresh_token': access_token["refresh_token"]
    }, timeout=5)
    if (response.status_code >= 200 and response.status_code < 400):
        new_access_token: AsanaTokenNoRefresh = response.json()
        pat: str = new_access_token["access_token"]
        access_token["access_token"] = pat
        db.put(access_token, f"user_{access_token['data']['id']}")
        return pat
    return None


async def read_projects_from_form(request: Request) -> Coroutine[List[AsanaObject], None, None]:
    '''read project ids selected inside form'''
    form = await request.form()
    project_strs: List[str] = list(form.keys())
    projects: List[AsanaObject] = list(map(ast.literal_eval, project_strs))
    return projects


async def read_projects_session_db(
    request: Request,
    delete_after_read: bool = False
) -> Coroutine[Union[List[AsanaObject], None], None, None]:
    '''read project ids selected inside form after storing in db'''
    key: Union[str, None] = request.session.get("projects_choosen")
    if not key:
        return None
    projects_choosen: Union[List[AsanaObject], None] = db.get(key)["value"]
    if not projects_choosen:
        return None
    if delete_after_read:
        db.delete(key)
        request.session.pop("projects_choosen")
    return projects_choosen
