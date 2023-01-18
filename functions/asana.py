'''asana helper functions'''

from typing import List, Tuple, Union

import requests
from asana import Client as AsanaClient
from deta import Deta
from fastapi import Request

from classes.asana import (AsanaObject, AsanaToken, AsanaTokenNoRefresh,
                           AsanaUser)
from classes.local_env import Env

# init deta databse
deta = Deta()
db = deta.Base("ann_db")  # This how to connect to or create a database.


async def get_authorize_asana_url(client_oauth: AsanaClient):
    '''
        generates the asana url to begin the oauth grant
        cerates a random state string
        attaches state to url
    '''
    (url, state) = client_oauth.session.authorization_url()
    return (url, state)


def oauth_client(env: Env) -> AsanaClient:
    '''cerate specific http client for asana API with oauth for login'''
    return AsanaClient.oauth(
        client_id=env.client_id,
        client_secret=env.client_secret,
        redirect_uri=env.number_nerd_oauth_callback
    )


def get(url: str, pat: str) -> List[AsanaObject]:
    '''a general asana api get request to a given url'''
    response = requests.get(
        url=url,
        headers=get_asana_headers(pat=pat, incl_content_type=False),
        timeout=5
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return None


def refresh_pat(request: Request, env: Env) -> Tuple[Union[AsanaUser, None], Union[str, None]]:
    '''read user id from session and read user from detabase'''
    asana_user_id: Union[str, None] = request.session.get("asana_user_id", None)
    if not asana_user_id:
        return (None, None)
    access_token: Union[AsanaToken, None] = db.get(f"user_{asana_user_id}")
    if not access_token:
        return (None, None)
    pat: Union[str, None] = refresh_asana_client_pat(access_token=access_token, env=env)
    return (access_token["data"], pat)


def refresh_asana_client_pat(access_token: AsanaToken, env: Env) -> Union[str, None]:
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
        new_access_token: AsanaTokenNoRefresh = response.json()
        pat: str = new_access_token["access_token"]
        access_token["access_token"] = pat
        db.put(access_token, f"user_{access_token['data']['id']}")
        return pat
    return None


def get_on_task_created_webhook(project_gid: str, callback_url: str) -> dict:
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


def get_asana_headers(pat: str, incl_content_type: bool = True) -> dict:
    '''return asana_header object containing all necessaray headers'''
    header_accept = {'Accept': 'application/json'}
    header_authorization = {'Authorization': f'Bearer {pat}'}
    header_content_type = {'Content-Type': 'application/json'}
    return (header_accept | header_authorization | header_content_type) if incl_content_type else (header_accept | header_authorization)
