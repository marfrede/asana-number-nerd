'''asana auth helper functions'''

from typing import Tuple, Union

import requests
from deta import Deta
from fastapi import Request

from mymodules import environment
from mymodules.asana import classes

# init deta databse
deta = Deta()
db = deta.Base("ann_db")  # This how to connect to or create a database.


def refresh_pat(request: Request, env: environment) -> Tuple[Union[classes.User, None], Union[str, None]]:
    '''read user id from session and read user from detabase'''
    asana_user_id: Union[str, None] = request.session.get("asana_user_id", None)
    if not asana_user_id:
        return (None, None)
    access_token: Union[classes.Token, None] = db.get(f"user_{asana_user_id}")
    if not access_token:
        return (None, None)
    pat: Union[str, None] = __refresh_asana_client_pat(access_token=access_token, env=env)
    return (access_token["data"], pat)


# HELPER

def __refresh_asana_client_pat(access_token: classes.Token, env: environment.Env) -> Union[str, None]:
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
        new_access_token: classes.TokenNoRefresh = response.json()
        pat: str = new_access_token["access_token"]
        access_token["access_token"] = pat
        db.put(access_token, f"user_{access_token['data']['id']}")
        return pat
    return None
