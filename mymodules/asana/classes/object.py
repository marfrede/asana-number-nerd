'''classes imporrtant for objects from/for asana API'''
from typing import Literal, TypedDict


class Object(TypedDict):
    '''asana workspace from asana API'''
    gid: str  # e.g. "12345"
    resource_type: Literal["workspace", "project"]
    name: str  # e.g. "My Company Workspace
