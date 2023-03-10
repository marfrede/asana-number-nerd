'''detabase operations'''


from typing import List, Union, cast

from deta import Deta

from modules import asana

from ..classes import User

# init deta databse
deta = Deta()
detabase = deta.Base("ann_db")  # This how to connect to or create a database.


def get_user(asana_user_id: str) -> User:
    '''get user and all their values'''
    user: Union[User, None] = detabase.get(key=__get_key(asana_user_id))
    return user


def put_access_token(asana_user_id: str, access_token: asana.Token, init: bool = False) -> User:
    '''store and update access_token to user["access_token"]'''
    user: Union[User, None] = get_user(asana_user_id)
    if init:
        user = user if user else {"access_token": None, "projects": []}
    user["access_token"] = access_token
    __store_user(asana_user_id, user)
    return user


def append_projects(asana_user_id: str, projects: List[asana.Object]) -> User:
    '''store and update projects to user["projects"]'''
    user: Union[User, None] = get_user(asana_user_id)
    projects_with_webhook: List[asana.ProjectWithWebhook] = list(map(__transform_project_to_project_with_webhook, projects))
    user["projects"] = (user["projects"] if user["projects"] else []) + projects_with_webhook
    __store_user(asana_user_id, user)
    return user


def set_project_active(asana_user_id: str, project_gid: str, x_hook_secret: str = None) -> User:
    '''for a given project set is_active to true and store x-hook-secret'''
    user: Union[User, None] = get_user(asana_user_id)
    project: asana.ProjectWithWebhook = None
    for pro in user["projects"]:
        if pro["gid"] == project_gid:
            project = pro
    if x_hook_secret is not None:
        project["x_hook_secret"] = x_hook_secret
    project["is_active"] = True
    __store_user(asana_user_id, user)
    return user


def set_project_inactive(asana_user_id: str, project_gid: str) -> User:
    '''for a given project set is_active to false'''
    user: Union[User, None] = get_user(asana_user_id)
    project: asana.ProjectWithWebhook = None
    for pro in user["projects"]:
        if pro["gid"] == project_gid:
            project = pro
    project["is_active"] = False
    __store_user(asana_user_id, user)
    return user


def next_task_number(asana_user_id: str, project_gid: str, task_gid: str) -> Union[int, None]:
    '''increment task number id in project'''
    user: User = get_user(asana_user_id)
    project: asana.ProjectWithWebhook = None
    for pro in user["projects"]:
        if pro["gid"] == project_gid:
            project = pro
    if not __webhook_active(user=user, project_index=user["projects"].index(project)):
        return None
    if __task_already_numbered(user=user, project_index=user["projects"].index(project), task_gid=task_gid):
        return None
    project["task_counter"] = project["task_counter"] + 1
    __store_user(asana_user_id, user)
    return project["task_counter"]


def __store_user(asana_user_id: str, user: User) -> None:
    '''overwrite user object in detabase'''
    detabase.put(user, key=__get_key(asana_user_id))


def __get_key(asana_user_id: str) -> str:
    '''create key string using asana_user_id to identify detabase user'''
    return f"user_{asana_user_id}"


def __transform_project_to_project_with_webhook(project: asana.Object) -> asana.ProjectWithWebhook:
    '''upgrades the project to the type ProjectWithWebhook and set default values for new properties'''
    project_with_webhook: asana.ProjectWithWebhook = cast(asana.ProjectWithWebhook, project)
    project_with_webhook["x_hook_secret"] = None
    project_with_webhook["webhook_gid"] = None
    project_with_webhook["is_active"] = False
    project_with_webhook["task_counter"] = 0
    return project_with_webhook


def __task_already_numbered(user: User, project_index: int, task_gid: str) -> bool:
    if "latest_task_gid" in user["projects"][project_index] and user["projects"][project_index]["latest_task_gid"] == task_gid:
        return True
    user["projects"][project_index]["latest_task_gid"] = task_gid
    __store_user(user["access_token"]["data"]["id"], user)
    return False


def __webhook_active(user: User, project_index: int) -> bool:
    return "is_active" in user["projects"][project_index] and user["projects"][project_index]["is_active"]
