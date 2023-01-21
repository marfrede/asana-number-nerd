'''detabase operations'''


from typing import List, Union

from deta import Deta

from modules import asana

from ..classes import User

# init deta databse
deta = Deta()
detabase = deta.Base("ann_db")  # This how to connect to or create a database.


def get_user(asana_user_id: str) -> User:
    '''get user and all their values'''
    user: Union[User, None] = detabase.get(key=__get_key(asana_user_id))
    if not user:
        return {
            "access_token": None,
            "projects": [],
            "webhooks": []
        }
    return user


def put_access_token(asana_user_id: str, access_token: asana.Token) -> User:
    '''store and update access_token to user["access_token"]'''
    user: User = get_user(asana_user_id)
    user["access_token"] = access_token
    __store_user(asana_user_id, user)
    return user


def put_projects(asana_user_id: str, projects: List[asana.Object]) -> User:
    '''store and update projects to user["projects"]'''
    user: User = get_user(asana_user_id)
    user["projects"] = projects
    __store_user(asana_user_id, user)
    return user


def __store_user(asana_user_id: str, user: User) -> None:
    '''overwrite user object in detabase'''
    detabase.put(user, key=__get_key(asana_user_id))


def __get_key(asana_user_id: str) -> str:
    '''create key string using asana_user_id to identify detabase user'''
    return f"user_{asana_user_id}"
