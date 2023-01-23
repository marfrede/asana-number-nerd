'''classes imporrtant for objects from/for asana API'''
from typing import Literal, TypedDict, Union


class Object(TypedDict):
    '''asana workspace or project object from asana API'''
    gid: str  # e.g. "12345"
    resource_type: Literal["workspace", "project"]
    name: str  # e.g. "My Company Workspace


class ProjectWithWebhook(Object):
    '''asana project object with custom extras for this number nerd app'''
    gid: str  # e.g. "12345"
    resource_type: Literal["project"]
    name: str  # e.g. "My Company Workspace
    x_hook_secret: str
    webhook_gid: Union[str, None]
    is_active: bool
    task_counter: int
