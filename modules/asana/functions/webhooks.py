'''asana webhook helper functions'''
import requests


def post(project_gid: str, callback_url: str, pat: str) -> requests.Response:
    '''create a webhook that listens to task added events inside given project'''
    return requests.post(
        url="https://app.asana.com/api/1.0/webhooks",
        headers={'Accept': 'application/json', 'Authorization': f'Bearer {pat}', 'Content-Type': 'application/json'},
        json={
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
        },
        timeout=20
    )
