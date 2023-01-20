'''deta user object with values'''
from typing import List, TypedDict, Union

from modules import asana


class ProjectSelected(TypedDict):
    '''saved foreach project a user selects for ann'''
    project: asana.Object
    is_active: bool


class Webhook(TypedDict):
    '''saved foreach webhook'''
    x_hook_secret: str
    project_gid: str
    webhook_gid: Union[str, None]


class User(TypedDict):
    '''represents one ann user in the detabase'''
    # key => {user_id}
    token_obj: asana.Token
    projects_selected: List[ProjectSelected]
    webhooks: List[Webhook]
