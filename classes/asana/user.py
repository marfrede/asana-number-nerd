'''class asana.user'''
from typing import TypedDict


class User(TypedDict):
    '''part of asana token'''
    id: str  # e.g. "4673218951",
    name: str  # e.g. "Greg Sanchez",
    email: str  # e.g. "gsanchez@example.com"
