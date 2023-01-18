'''classes for tokens'''
from typing import TypedDict

from .user import AsanaUser


class AsanaToken(TypedDict):
    '''asana token as it is returned from asana fetch_token endpoint'''
    access_token: str  # e.g. "f6ds7fdsa69ags7ag9sd5a",
    expires_in: int  # e.g. 3600,
    token_type: str  # e.g. "bearer",
    refresh_token: str  # e.g. "hjkl325hjkl4325hj4kl32fjds",
    data: AsanaUser


class AsanaTokenNoRefresh(TypedDict):
    '''asana token as it is returned from asana refresh_token endpoint'''
    access_token: str  # e.g. "f6ds7fdsa69ags7ag9sd5a",
    expires_in: int  # e.g. 3600,
    token_type: str  # e.g. "bearer",
    data: AsanaUser
