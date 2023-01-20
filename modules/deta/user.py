'''deta user object with values'''
from typing import List, TypedDict, Union

from modules import asana


class __ProjectSelected(TypedDict):
    project: asana.Object
    is_active: bool


class __Webhook(TypedDict):
    x_hook_secret: str
    project_gid: str
    webhook_gid: Union[str, None]


class DetaUser(TypedDict):
    # key => {user_id}
    token_obj: asana.Token
    projects_selected: List[__ProjectSelected]
    webhooks: List[__Webhook]
