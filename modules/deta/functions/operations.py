'''detabase operations'''
from deta import Deta

from modules import asana

# from ..classes import User

# init deta databse
deta = Deta()
detabase = deta.Base("ann_db")  # This how to connect to or create a database.


def put_access_token(asana_user_id: str, access_token: asana.Token) -> None:
    '''store and update users access_token'''
    detabase.put(access_token, __get_key(asana_user_id))
    return


def __get_key(asana_user_id: str) -> str:
    return f"user_{asana_user_id}"
