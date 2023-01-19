'''asana auth helper functions'''

from typing import Tuple, Union

import requests

from mymodules import environment
from mymodules.asana import classes


def refresh_token(old_access_token: Union[classes.Token, None], env: environment) -> Tuple[
    Union[classes.Token, None],
    Union[classes.User, None],
    Union[str, None]
]:
    '''
        make a post request to asana oauth in order to get a new access_token
        return (access_token, user, pat)
    '''
    if not old_access_token or not env:
        return (None, None, None)
    new_access_token: Union[classes.Token, None] = __refresh_asana_client_pat(access_token=old_access_token, env=env)
    if not new_access_token:
        return (None, None, None)
    return (new_access_token, new_access_token['data'], new_access_token['access_token'])


# HELPER

def __refresh_asana_client_pat(access_token: classes.Token, env: environment.Env) -> Union[classes.Token, None]:
    '''
        refresh asana access_token (especially pat) with refresh_token
        return None when refresh_token invalid (should only be the case when app access was denied)
        else return new access_token object
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
        # update old access token because the new one doesn´t know the rerfresh token
        access_token["access_token"] = new_access_token["access_token"]
        return access_token
    return None
