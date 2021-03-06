import random
import ssl
import time
import warnings
from logging import Logger
from typing import Dict, Optional

import requests
from requests import Response
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from urllib3 import poolmanager

from .model import FetchedResponse, Meta

# Ignore some warnings
warnings.simplefilter("ignore", UserWarning)
warnings.simplefilter("ignore", InsecureRequestWarning)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36"
)
MAX_TRIES = 4
TIMEOUT = 10


class TLSHTTPAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):  # type: ignore
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        self.poolmanager = poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLS,
            ssl_context=ctx,
        )


def requests_get(url: str, headers: Dict[str, str]) -> Optional[Response]:
    headers["User-Agent"] = USER_AGENT
    tries = 0
    wait = 1.0
    while tries < MAX_TRIES:
        try:
            session = requests.session()
            session.mount("https://", TLSHTTPAdapter())
            response = session.get(
                url,
                headers=headers,
                verify=False,
                allow_redirects=True,
                stream=True,
                timeout=TIMEOUT,
            )
            return response
        except requests.exceptions.ConnectionError:
            # TODO: Check the host existence
            pass
        except requests.exceptions.Timeout:
            pass
        time.sleep(wait)
        wait *= 2
        wait += random.uniform(0, wait)  # jitter
        tries += 1
    return None


def cached_requests_get(
    url: str, old_meta: Optional[Meta], now: int, *, logger: Logger
) -> Optional[FetchedResponse]:
    req_headers: Dict[str, str] = {}

    if old_meta is not None:
        if old_meta.expired_at > now:
            # already cached and valid, so don't request
            return None
        if old_meta.etag is not None:
            req_headers["If-None-Match"] = old_meta.etag
        if old_meta.last_modified is not None:
            req_headers["If-Modified-Since"] = old_meta.last_modified

    response = requests_get(url, req_headers)

    if response is None:
        logger.warn(f"Cannot get {url}")
        return None

    return FetchedResponse(
        url=url, fetched_at=now, response=response, old_meta=old_meta
    )
