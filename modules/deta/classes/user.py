'''deta user object with values'''
from typing import List, TypedDict, Union

from modules import asana


class Webhook(TypedDict):
    '''saved foreach webhook'''
    x_hook_secret: str
    project_gid: str
    webhook_gid: Union[str, None]
    is_active: bool


class User(TypedDict):
    '''represents one ann user in the detabase'''
    access_token: asana.Token
    projects: List[asana.Object]
    webhooks: List[Webhook]
