'''asana webhook helper functions'''


def get_webhook(project_gid: str, callback_url: str) -> dict:
    '''get the requets body for a new POST /webhooks listening to a task added to a given project'''
    return {
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
    }
