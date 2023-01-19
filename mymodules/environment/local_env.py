'''class env'''

from functools import lru_cache

from pydantic import BaseSettings


class Env(BaseSettings):
    '''env variables'''
    # asana app oauth2
    number_nerd_oauth_callback: str = "https://www.asana-number-nerd.com/oauth/callback"
    number_nerd_webhook_callback: str = "https://www.asana-number-nerd.com/webhook/receive"
    client_id: str = "1203721176797529"
    client_secret: str

    # deta project
    deta_project_key: str

    class Config:
        '''read variables from dotenv file'''
        env_file = ".env"


@lru_cache()
def get_env():
    '''get env variables'''
    return Env()
