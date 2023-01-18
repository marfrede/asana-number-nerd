'''asana helper functions'''

from typing import Tuple, Union

import requests
from asana import Client
from deta import Deta
from fastapi import Request

from classes.asana import Token, TokenNoRefresh, User
from classes.local_env import Env

# init deta databse
deta = Deta()
db = deta.Base("ann_db")  # This how to connect to or create a database.


async def auth_url(client_oauth: Client) -> Tuple[str, str]:
    '''
        generates the asana url to begin the oauth grant
        cerates a random state string
        attaches state to url
    '''
    (url, state) = client_oauth.session.authorization_url()
    return (url, state)


def oauth_client(env: Env) -> Client:
    '''cerate specific http client for asana API with oauth for login'''
    return Client.oauth(
        client_id=env.client_id,
        client_secret=env.client_secret,
        redirect_uri=env.number_nerd_oauth_callback
    )


def refresh_pat(request: Request, env: Env) -> Tuple[Union[User, None], Union[str, None]]:
    '''read user id from session and read user from detabase'''
    asana_user_id: Union[str, None] = request.session.get("asana_user_id", None)
    if not asana_user_id:
        return (None, None)
    access_token: Union[Token, None] = db.get(f"user_{asana_user_id}")
    if not access_token:
        return (None, None)
    pat: Union[str, None] = __refresh_asana_client_pat(access_token=access_token, env=env)
    return (access_token["data"], pat)


def get_webhook(project_gid: str, callback_url: str) -> dict:
    '''get the requets body for a new POST /webhooks listening to a task added to a given project'''
    return {
        "data": {
            "filters": [
                {
                    "action": "added",
                    "resource_type": "task"
                }
            ],
            "resource": project_gid,
            "target": callback_url
        }
    }


# HELPER

def __refresh_asana_client_pat(access_token: Token, env: Env) -> Union[str, None]:
    '''
        refresh asana access_token (pat) with refresh_token
        save new access_token object in db
        return only the pat
        return None when refresh_token invalid (should only be the case when app access was denied)
    '''
    response = requests.post(url="https://app.asana.com/-/oauth_token", data={
        'grant_type': 'refresh_token',
        'client_id': env.client_id,
        'client_secret': env.client_secret,
        'redirect_uri': env.number_nerd_oauth_callback,
        'refresh_token': access_token["refresh_token"]
    }, timeout=5)
    if (response.status_code >= 200 and response.status_code < 400):
        new_access_token: TokenNoRefresh = response.json()
        pat: str = new_access_token["access_token"]
        access_token["access_token"] = pat
        db.put(access_token, f"user_{access_token['data']['id']}")
        return pat
    return None
