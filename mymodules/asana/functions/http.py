'''asana http helper functions'''
from typing import List

import requests

from classes.asana.object import Object


def http_get(url: str, pat: str) -> List[Object]:
    '''a general asana api get request to a given url'''
    response = requests.get(
        url=url,
        headers=get_headers(pat=pat, incl_content_type=False),
        timeout=5
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return None


def http_post(url: str, pat: str, data: dict) -> List[Object]:
    '''a general asana api post request to a given url'''
    response = requests.post(
        url=url,
        headers=get_headers(pat=pat, incl_content_type=True),
        data=data,
        timeout=10
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return None


def http_put(url: str, pat: str, json: dict) -> List[Object]:
    '''a general asana api put request to a given url'''
    response = requests.put(
        url=url,
        headers=get_headers(pat=pat, incl_content_type=True),
        json=json,
        timeout=10
    )
    if (response.status_code >= 200 and response.status_code < 400):
        return response.json()["data"]
    return None


def get_headers(pat: str, incl_content_type: bool = True) -> dict:
    '''return asana_header object containing all necessaray headers'''
    header_accept = {'Accept': 'application/json'}
    header_authorization = {'Authorization': f'Bearer {pat}'}
    header_content_type = {'Content-Type': 'application/json'}
    return (header_accept | header_authorization | header_content_type) if incl_content_type else (header_accept | header_authorization)
