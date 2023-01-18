'''asana number nerdx'''

import ast
from typing import Coroutine, List, Union

import requests
from asana import Client as AsanaClient
from deta import Deta
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status as Status
from starlette.middleware.sessions import SessionMiddleware

from classes.asana import Object as AsanaObject
from classes.asana import Token as AsanaToken
from classes.local_env import Env, get_env
from functions import asana
from mymodules.asana.functions import http as asana_http

# init fastapi
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="KpGtHMS3XgH5b7z9us!@e79GlY$b")
app.mount("/static", StaticFiles(directory="static"), name="static")

# init jinja templates
templates = Jinja2Templates(directory="templates")

# init deta databse
deta = Deta()
db = deta.Base("ann_db")  # This how to connect to or create a database.


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
    asana_client_oauth: AsanaClient = asana.oauth_client(env)
    url, state = await asana.auth_url(asana_client_oauth)
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
    asana_client_oauth: AsanaClient = asana.oauth_client(env)
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
    asana_user, pat = asana.refresh_pat(request=request, env=env)
    if (not asana_user or not pat):
        return RedirectResponse("/")
    # 2. respond
    workspaces: List[AsanaObject] = asana_http.http_get(url="https://app.asana.com/api/1.0/workspaces", pat=pat)
    for workspace in workspaces:
        projects: List[AsanaObject] = asana_http.http_get(url=f"https://app.asana.com/api/1.0/workspaces/{workspace['gid']}/projects", pat=pat)
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
    _, pat = asana.refresh_pat(request=request, env=env)
    projects: Union[List[AsanaObject], None] = await read_projects_session_db(request=request, delete_after_read=True)
    if not pat or not projects:
        return RedirectResponse("/choose-projects")
    response = asana_http.http_post(
        url="https://app.asana.com/api/1.0/webhooks", pat=pat,
        data=asana.get_webhook(project_gid=projects[0]["gid"], callback_url=env.number_nerd_webhook_callback),
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
    task_created_name = asana_http.http_get(
        url=f"https://app.asana.com/api/1.0/tasks/{task_created_gid}", pat=pat,
    )["name"]
    asana_http.http_put(
        url=f"https://app.asana.com/api/1.0/tasks/{task_created_gid}", pat=pat,
        json={"data": {"name": f"{'1'} {task_created_name}"}}
    )


# HELPER


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
