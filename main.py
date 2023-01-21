'''asana number nerdx'''

import ast
from typing import Any, Coroutine, Dict, List, Union

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from modules import asana, deta, environment

# init fastapi
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="KpGtHMS3XgH5b7z9us!@e79GlY$b")
app.mount("/static", StaticFiles(directory="static"), name="static")

# init jinja templates
templates = Jinja2Templates(directory="templates")


@ app.get("/home", response_class=RedirectResponse)
async def root():
    '''redirect /home to / where the homepage is'''
    return RedirectResponse("/")


@ app.get("/", response_class=HTMLResponse)
async def home(request: Request, env: environment.Env = Depends(environment.get_env)):
    '''
        homepage
        display the asana number nerd (ann) description
        display href button to auth ann with the users private asana account
    '''
    url, state = await asana.oauth.begin_url(client=asana.oauth.get_client(env))
    request.session["state"] = state
    return templates.TemplateResponse("index.jinja2", {"request": request, "authorize_asana_url": url})


@ app.get("/oauth/callback", response_class=RedirectResponse)
async def oauth_callback(
    request: Request,
    code: Union[str, None] = None,
    state: Union[str, None] = None,
    env: environment.Env = Depends(environment.get_env)
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
    access_token: asana.Token = asana.oauth.get_client(env).session.fetch_token(code=code)
    asana_user_id: str = access_token['data']["id"]

    # store auth_token in db and db key in session
    request.session['asana_user_id'] = asana_user_id
    deta.put_access_token(asana_user_id=asana_user_id, access_token=access_token)
    return RedirectResponse("/choose-projects")


@ app.get("/choose-projects", response_class=HTMLResponse)
async def choose_projects(request: Request, env: environment.Env = Depends(environment.get_env)):
    '''site for the authenticated user'''
    # 1. auth or redirect
    user: Union[deta.User, None] = read_user_from_db(session=request.session)
    access_token, asana_user, pat = asana.auth.refresh_token(old_access_token=(user["access_token"] if user else None), env=env)
    if not access_token:
        return RedirectResponse("/")
    # 2. save new acess_token and respond
    deta.put_access_token(asana_user_id=access_token['data']['id'], access_token=access_token)
    workspaces: List[asana.Object] = asana.http.get(url="workspaces", pat=pat)
    for workspace in workspaces:
        projects: List[asana.Object] = asana.http.get(url=f"workspaces/{workspace['gid']}/projects", pat=pat)
        workspace["projects"] = projects
    return templates.TemplateResponse("choose-projects.jinja2", {
        "request": request,
        "asana_user": asana_user,
        "workspaces": workspaces,
    })


@app.post("/choose-numbering", response_class=HTMLResponse)
async def choose_numbering(request: Request, env: environment.Env = Depends(environment.get_env)):
    '''site for the authenticated user'''
    # read projects from form
    projects: List[asana.Object] = await read_projects_from_form(request=request)
    user: Union[deta.User, None] = deta.put_projects(asana_user_id=request.session.get("asana_user_id", None), projects=projects)
    if not user:
        return RedirectResponse("/choose-projects")
    # 1. auth and validate or redirect
    _, asana_user, _ = asana.auth.refresh_token(old_access_token=user["access_token"], env=env)
    if not asana_user:
        return RedirectResponse("/choose-projects")
    # 2. respond
    return templates.TemplateResponse("choose-numbering.jinja2", {
        "request": request,
        "asana_user": asana_user,
        "projects": projects,
    })
    # return RedirectResponse("/choose-numbering", status_code=Status.HTTP_302_FOUND)


# @ app.post("/webhook/create")
# async def create_weebhook(request: Request, env: environment.Env = Depends(environment.get_env)):
#     '''create the webhook to listen to create-task events inside given projects'''
#     # 1. auth and validate or redirect
#    user: Union[deta.User, None] = read_user_from_db(session=request.session)
#     access_token, _, pat = asana.auth.refresh_token(old_access_token=user["access_token"], env=env)
#     # 2. save new acess_token and respond
#    # detabase.put(access_token, f"user_{access_token['data']['id']}")
#     projects: Union[List[asana.Object], None] = await read_projects_session_db(request=request, delete_after_read=True)
#     if not pat or not projects:
#         return RedirectResponse("/choose-projects")
#     response = asana.http.post(
#         url="webhooks", pat=pat,
#         data=asana.webhooks.post_request_body(
#             project_gid=projects[0]["gid"],
#             callback_url=env.number_nerd_webhook_callback),
#     )
#     if (response.status_code >= 200 and response.status_code < 400):
#         return response.json()["data"]
#     return response.json()


# @app.post("/webhook/receive")
# async def receive_weebhook(request: Request, response: Response):
#     '''callback for asana when task created (and for first handshake)'''
#     pat = "1/1199181200186785:d6752d0cc04c304e22d12e0b57163c14"
#     secret: Union[str, None] = request.headers.get("X-Hook-Secret")
#     if secret:
#         # db.put(secret, f"x_hook_secret_{user_gid}_{project_gid}")
#         response.status_code = Status.HTTP_204_NO_CONTENT
#         response.headers["X-Hook-Secret"] = secret
#         return None
#     # create a task
#     body: dict = await request.json()
#     task_created_gid: str = body["events"][0]["resource"]["gid"]
#     task_created_name = asana.http.get(url=f"tasks/{task_created_gid}", pat=pat,)["name"]
#     asana.http.put(
#         url=f"tasks/{task_created_gid}", pat=pat,
#         json={"data": {"name": f"{'1'} {task_created_name}"}}
#     )


# HELPER


async def read_projects_from_form(request: Request) -> Coroutine[List[asana.Object], None, None]:
    '''read project ids selected inside form'''
    form = await request.form()
    project_strs: List[str] = list(form.keys())
    projects: List[asana.Object] = list(map(ast.literal_eval, project_strs))
    return projects


# async def read_projects_session_db(
#     request: Request,
#     delete_after_read: bool = False
# ) -> Coroutine[Union[List[asana.Object], None], None, None]:
#     '''read project ids selected inside form after storing in db'''
#     key: Union[str, None] = request.session.get("projects_choosen")
#     if not key:
#         return None
#     projects_choosen: Union[List[asana.Object], None] = detabase.get(key)["value"]
#     if not projects_choosen:
#         return None
#     if delete_after_read:
#         detabase.delete(key)
#         request.session.pop("projects_choosen")
#     return projects_choosen


def read_user_from_db(session: Dict[str, Any]) -> Union[deta.User, None]:
    '''
        read user_id from session and then asana_access_token from db
        return None if user_id not found in session or access_token not found in db
    '''
    asana_user_id: Union[str, None] = session.get("asana_user_id", None)
    if not asana_user_id:
        return None
    user: deta.User = deta.get_user(asana_user_id)
    return user
