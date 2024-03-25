from typing import Callable, Dict, Optional
import requests
from requests import Response
from retry import retry

# Requests types
REQ_GET = 'get'
REQ_POST = 'post'
REQ_PUT = 'put'
REQ_DELETE = 'delete'

_req_type_func: Dict[str, Callable] = {
    REQ_GET: requests.get,
    REQ_POST: requests.post,
    REQ_PUT: requests.put,
    REQ_DELETE: requests.delete,
    }

################
# call
@retry(Exception, tries=5, delay=3, jitter=(0,3))
def call(a_req_type: str, a_url: str, **kwargs) -> Response:
    """Calls API and manages errors
    Args:
        a_req_type: type of request (GET, POST, PUT, DELETE)
        a_url
        *args: variable number of extra argument
        **kwargs: variable number of keyword arguments
    Returns:
        Response
    """
    r: Optional[Response] = None
    err_msg:str = f'Type: {a_req_type} - Route: {a_url} - Args: {kwargs}'

    try:
        if kwargs == {}:
            r = _req_type_func[a_req_type](url=a_url)
        else:
            r = _req_type_func[a_req_type](a_url, **kwargs)
        if r is not None:
            err_msg += '\n'+f'Response status: {r.status_code} - Response reason:{r.reason} - Response content: {str(r.content)}'
    except:
        s: str = 'before' if r is None else 'after'
        raise Exception(f'Exception raised {s} calling - {err_msg}')
    if r is not None and r.status_code < 300:
        return r
    else:
        raise Exception(f'API called but returned error - {err_msg}')
    