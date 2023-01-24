'''asana number nerdx'''

import ast
from typing import Any, Coroutine, Dict, List, Literal, Tuple, Union

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status as Status
from starlette.middleware.sessions import SessionMiddleware

from modules import asana, deta, environment

# init fastapi
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="KpGtHMS3XgH5b7z9us!@e79GlY$b")
app.mount("/static", StaticFiles(directory="static"), name="static")

# init jinja templates
templates = Jinja2Templates(directory="templates")


@ app.get("/", response_class=RedirectResponse)
async def root():
    '''redirect /start to / where the setup start page is'''
    return RedirectResponse("/start")


@ app.get("/start", response_class=HTMLResponse)
async def start(request: Request, env: environment.Env = Depends(environment.get_env)):
    '''
        start page (setup #1)
        display the asana number nerd (ann) description
        display href button to auth ann with the users private asana account
    '''
    url, state = await asana.oauth.begin_url(client=asana.oauth.get_client(env))
    request.session["state"] = state
    return templates.TemplateResponse("start.jinja2", {"request": request, "authorize_asana_url": url})


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
    user: deta.User = deta.put_access_token(asana_user_id=asana_user_id, access_token=access_token, init=True)
    if user["projects"]:
        return RedirectResponse("/home")
    return RedirectResponse("/choose-projects")


@ app.get("/choose-projects", response_class=HTMLResponse)
async def choose_projects(request: Request, env: environment.Env = Depends(environment.get_env)):
    '''
        choose-projects (setup #2)
    '''
    _, _, asana_user, pat, response = __read_user_from_session_db_and_refresh_token(request, env)
    if response:
        return response
    workspaces: List[asana.Object] = asana.http.get(url="workspaces", pat=pat)
    for workspace in workspaces:
        projects: List[asana.Object] = asana.http.get(url=f"workspaces/{workspace['gid']}/projects", pat=pat)
        workspace["projects"] = projects
    return templates.TemplateResponse("choose-projects.jinja2", {
        "request": request,
        "asana_user": asana_user,
        "workspaces": workspaces,
    })


@app.post("/choose-projects", response_class=HTMLResponse)
async def read_projects(request: Request):
    '''
        read the choosen projects (setup #2)
    '''
    projects: List[asana.Object] = await __read_projects_from_form(request=request)
    deta.put_projects(asana_user_id=__get_user_id_from_session(request.session), projects=projects)
    return RedirectResponse('/finish-setup', status_code=Status.HTTP_302_FOUND)


@app.get("/finish-setup", response_class=HTMLResponse)
async def choose_numbering(request: Request):
    '''
        confirm the chosen projects (setup #3)
    '''
    user: Union[deta.User, None] = __get_user_from_session_and_db(request.session)
    if not user:
        return RedirectResponse("/choose-projects")
    # 2. respond
    return templates.TemplateResponse("finish-setup.jinja2", {
        "request": request,
        "asana_user": user["access_token"]["data"],
        "projects": user["projects"],
    })


@ app.post("/create-webhooks")
async def create_weebhook(request: Request, env: environment.Env = Depends(environment.get_env)):
    '''create the webhook to listen to create-task events inside given projects'''
    deta_user, _, asana_user, pat, response = __read_user_from_session_db_and_refresh_token(request, env, error_redirect_url="/finish-setup")
    if response:
        return response
    # 2. create webhook
    if not deta_user["projects"]:
        return RedirectResponse("/finish-setup")
    projects = deta_user["projects"]
    for project in projects:
        asana.webhooks.post(
            project_gid=project["gid"],
            callback_url=f"{env.number_nerd_webhook_callback}/{asana_user['id']}/{project['gid']}",
            pat=pat
        )
    return RedirectResponse('/home', status_code=Status.HTTP_302_FOUND)


@app.post("/webhook/receive/{user_gid}/{project_gid}")
async def receive_weebhook(
    request: Request,
    user_gid: str,
    project_gid: str,
    response: Response,
    env: environment.Env = Depends(environment.get_env)
):
    '''callback for asana when task created (and for first handshake)'''
    asana_user_id = user_gid
    if request.headers.get("X-Hook-Secret"):
        secret: str = request.headers.get("X-Hook-Secret")
        deta.set_project_active(asana_user_id, project_gid, x_hook_secret=secret)
        response.headers["X-Hook-Secret"] = secret
        response.status_code = Status.HTTP_204_NO_CONTENT
        return None
    if request.headers.get("X-Hook-Signature"):
        user: deta.User = deta.get_user(asana_user_id)
        access_token, _, pat = asana.auth.refresh_token(old_access_token=user["access_token"], env=env)
        deta.put_access_token(asana_user_id=user_gid, access_token=access_token)
        # rename the task created
        task_id, task_name = await __request_task_info(request, pat)
        if (task_name == "") or (task_name and task_name[0] != "#"):
            _, task_number = deta.next_task_number(asana_user_id, project_gid)
            task_name_new = f"{__format_task_number(task_number)} {task_name}"
            asana.http.put(
                url=f"tasks/{task_id}", pat=pat,
                json={"data": {"name": task_name_new}}
            )
        response.status_code = Status.HTTP_204_NO_CONTENT
        return None
    raise Exception("Something went wrong")


@app.get("/home")
async def home(request: Request, env: environment.Env = Depends(environment.get_env)):
    '''home page for users that once setup projects'''
    deta_user, _, asana_user, pat, response = __read_user_from_session_db_and_refresh_token(request, env)
    if response:
        return response
    if not deta_user["projects"]:
        return RedirectResponse("/choose-projects")
    workspaces: List[asana.Object] = asana.http.get(url="workspaces", pat=pat)
    for workspace in workspaces:
        ws_projects: List[asana.Object] = asana.http.get(url=f"workspaces/{workspace['gid']}/projects", pat=pat)
        for ws_project in ws_projects:
            ws_project["status"] = __get_project_status(ws_project, user_projects=deta_user["projects"])
        workspace["projects"] = ws_projects
    return templates.TemplateResponse("home.jinja2", {
        "request": request,
        "asana_user": asana_user,
        "workspaces": workspaces,
    })


@app.post("/stop-numbering/{project}")
async def stop_numbering(request: Request, project: str, env: environment.Env = Depends(environment.get_env)):
    '''stop numbering a project by setting the webhook to active to false'''
    deta_user, asana_token, asana_user, pat, response = __read_user_from_session_db_and_refresh_token(request, env)
    if response:
        return response
    return None


@app.post("/reactivate-numbering/{project}")
async def reactivate_numbering(request: Request, project: str, env: environment.Env = Depends(environment.get_env)):
    '''reactive numbering another project by setting the webhook to active again'''
    deta_user, asana_token, asana_user, pat, response = __read_user_from_session_db_and_refresh_token(request, env)
    if response:
        return response
    return None


@app.post("/start-numbering/{project}")
async def start_numbering(request: Request, project: str, env: environment.Env = Depends(environment.get_env)):
    '''start numbering another project by adding a webhook'''
    project: asana.Object = ast.literal_eval(project)
    _, _, asana_user, pat, response = __read_user_from_session_db_and_refresh_token(request, env)
    if response:
        return response
    deta.put_projects(asana_user_id=asana_user["id"], projects=[project])
    asana.webhooks.post(
        project_gid=project["gid"],
        callback_url=f"{env.number_nerd_webhook_callback}/{asana_user['id']}/{project['gid']}",
        pat=pat
    )
    return RedirectResponse('/home', status_code=Status.HTTP_302_FOUND)


def __read_user_from_session_db_and_refresh_token(request: Request, env: environment.Env, error_redirect_url: str = "/") -> Tuple[
    Union[deta.User, None],
    Union[asana.Token, None],
    Union[asana.User, None],
    Union[str, None],
    Union[RedirectResponse, None],
]:
    response: RedirectResponse = None
    user: Union[deta.User, None] = __get_user_from_session_and_db(request.session)
    if not user:
        return None, None, None, None, RedirectResponse(error_redirect_url, status_code=Status.HTTP_302_FOUND)
    access_token, asana_user, pat = asana.auth.refresh_token(old_access_token=user["access_token"], env=env)
    if not access_token:
        return user, None, None, None, RedirectResponse(error_redirect_url, status_code=Status.HTTP_302_FOUND)
    deta.put_access_token(asana_user_id=asana_user['id'], access_token=access_token)
    return user, access_token, asana_user, pat, response


async def __read_projects_from_form(request: Request) -> Coroutine[List[asana.Object], None, None]:
    '''read project ids selected inside form'''
    form = await request.form()
    project_strs: List[str] = list(form.keys())
    projects: List[asana.Object] = list(map(ast.literal_eval, project_strs))
    return projects


def __get_user_from_session_and_db(session: Dict[str, Any]) -> Union[deta.User, None]:
    '''
        read user_id from session and then deta_user from db
        return None if user_id not found in session or deta_user not found in db
    '''
    asana_user_id: Union[str, None] = __get_user_id_from_session(session)
    return deta.get_user(asana_user_id) if asana_user_id else None


def __get_user_id_from_session(session: Dict[str, Any]) -> Union[str, None]:
    '''read user_id from session and then asana_access_token from db'''
    asana_user_id: Union[str, None] = session.get("asana_user_id", None)
    return asana_user_id


def __format_task_number(number: int) -> str:
    '''gives number in #00x format'''
    if number > 99:
        return f"#{number}"
    if number > 9:
        return f"#0{number}"
    return f"#00{number}"


async def __request_task_info(request: Request, pat: str) -> Tuple[Union[str, None], Union[str, None]]:
    body: dict = await request.json()
    try:
        task_id: str = list(body["events"])[0]["resource"]["gid"]
        task: Union[asana.Object, None] = asana.http.get(url=f"tasks/{task_id}", pat=pat)
    except Exception:  # pylint: disable=broad-except
        return None, None
    else:
        if task:
            task_name = task["name"]
            return (task_id, task_name)
        return task_id, None


def __get_project_status(
        project: List[asana.Object],
        user_projects: List[asana.ProjectWithWebhook]
) -> Literal["new", "inactive", "active"]:
    '''
        return projects status wether it
        - is currently being numbered (active)
        - was numbered once (inactive, but webhook exists) or
        - has never been numbered (new)
    '''
    if any(project_active["gid"] == project["gid"] for project_active in list(filter(lambda p: p["is_active"], user_projects))):
        return "active"
    if any(project_inactive["gid"] == project["gid"] for project_inactive in list(filter(lambda p: not p["is_active"], user_projects))):
        return "inactive"
    return "new"
