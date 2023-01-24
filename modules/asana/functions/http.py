'''asana http helper functions'''
from typing import List, Union

import requests

from modules.asana import classes

URL = "https://app.asana.com/api/1.0"


def get(url: str, pat: str) -> Union[Union[List[classes.Object], classes.Object], None]:
    '''a general asana api get request to a given url'''
    response = requests.get(
        url=f"{URL}/{url}",
        headers=__get_headers(pat=pat, incl_content_type=False),
        timeout=5
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return None


def post(url: str, pat: str, data: dict) -> Union[Union[List[classes.Object], classes.Object], None]:
    '''a general asana api post request to a given url'''
    response = requests.post(
        url=f"{URL}/{url}",
        headers=__get_headers(pat=pat, incl_content_type=True),
        data=data,
        timeout=10
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return None


def put(url: str, pat: str, json: dict) -> Union[Union[List[classes.Object], classes.Object], None]:
    '''a general asana api put request to a given url'''
    response = requests.put(
        url=f"{URL}/{url}",
        headers=__get_headers(pat=pat, incl_content_type=True),
        json=json,
        timeout=10
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return None


def __get_headers(pat: str, incl_content_type: bool = True) -> dict:
    '''return asana_header object containing all necessaray headers'''
    header_accept = {'Accept': 'application/json'}
    header_authorization = {'Authorization': f'Bearer {pat}'}
    header_content_type = {'Content-Type': 'application/json'}
    return (header_accept | header_authorization | header_content_type) if incl_content_type else (header_accept | header_authorization)
