'''deta user object with values'''
from typing import List, TypedDict

from modules import asana


class User(TypedDict):
    '''represents one ann user in the detabase'''
    access_token: asana.Token
    projects: List[asana.ProjectWithWebhook]
