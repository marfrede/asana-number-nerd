'''asana oauth helper functions'''

from typing import Tuple

from asana import Client

from classes.local_env import Env


async def begin_url(client: Client) -> Tuple[str, str]:
    '''
        generates the asana url to begin the oauth grant
        cerates a random state string
        attaches state to url
    '''
    (url, state) = client.session.authorization_url()
    return (url, state)


def get_client(env: Env) -> Client:
    '''cerate specific http asana_oauth_client for asana API with oauth for login'''
    return Client.oauth(
        client_id=env.client_id,
        client_secret=env.client_secret,
        redirect_uri=env.number_nerd_oauth_callback
    )
