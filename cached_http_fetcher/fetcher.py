import sys
import time
import multiprocessing
from typing import Dict, Set, Iterable, Optional

from .meta import get_meta, put_meta
from .url_list import urls_per_domain
from .storage import StorageBase, ContentStorageBase
from .request import cached_requests_get, RequestException

class FetchWorker(multiprocessing.Process):
    def __init__(self, url_queue, response_queue, meta_storage, max_fetch_count, fetch_count_window):
        super().__init__()
        self._url_queue = url_queue
        self._response_queue = response_queue
        self._meta_storage = meta_storage
        self._logger = multiprocessing.get_logger()
        self._max_fetch_count = max_fetch_count
        self._fetch_count_window = fetch_count_window
        if self._max_fetch_count == 0 or self._fetch_count_window == 0:
            self._max_fetch_count = sys.maxint
            self._fetch_count_window = sys.maxint


    def run(self):
        fetch_count_start = time.time()
        fetch_count = 0

        while True:
            url_set = self._url_queue.get()
            if url_set is None:
                break

            for url in url_set:
                try:
                    elapsed = time.time() - fetch_count_start
                    remaining = self._fetch_count_window - elapsed
                    if remaining <= 0:
                        fetch_count_start = time.time()
                        fetch_count = 0

                    fetched_response = cached_requests_get(url, self._meta_storage)

                    # fetched_response can be None when we don't need to fetch the cache
                    if fetched_response is not None:
                        self._response_queue.put(fetched_response)

                        fetch_count += 1
                        if fetch_count > self._max_fetch_count:
                            time.sleep(remaining)
                except RequestException as e:
                    self._logger.warning(str(e))
                except Exception as e:
                    self._logger.warning(str(e))


class OptimizeWorker(multiprocessing.Process):
    def __init__(self, response_queue, meta_storage, content_storage):
        super().__init__()
        self._response_queue = response_queue
        self._meta_storage = meta_storage
        self._content_storage = content_storage
        self._logger = multiprocessing.get_logger()


    def run(self):
        while True:
            fetched_response = self._response_queue.get()
            if fetched_response is None:
                break

            # TODO: Apply filters to the cache
            filtered_response = fetched_response.response

            cached_url = None
            if filtered_response.status_code == 200:
                # Save response content into the cache
                # TODO: key_in_content_storage might be different from original url, handling https:// etc
                now = time.time()

                # At least 3600 secs to be cached in clients
                # TODO: configurable
                max_age = max(3600, now - fetched_response.expired_at)
                key_in_content_storage = fetched_response.url
                self._content_storage.put_content(key_in_content_storage, filtered_response.content,
                    content_type=fetched_response.content_type, cache_control=f"max_age={max_age}")
                cached_url = self._content_storage.cached_url(key_in_content_storage)
            # Save the meta info
            put_meta(
                    fetched_response.url, self._meta_storage,
                    cached_url=cached_url,
                    fetched_at=fetched_response.fetched_at,
                    expired_at=fetched_response.expired_at
            )


def url_queue_from_list(url_list: Iterable[str]) -> multiprocessing.Queue:
    url_dict = urls_per_domain(url_list)
    url_queue = multiprocessing.Queue()
    url_count = 0
    for _domain, url_set in url_dict.items():
        url_queue.put(url_set)
        url_count += len(url_set)
    return url_queue


def fetch_urls_single(url_list: Iterable[str], *, meta_storage: StorageBase, content_storage: ContentStorageBase, max_fetch_count: int, fetch_count_window: int, logger) -> None:
    """
    A single process version of fetch_urls()
    """
    url_queue = url_queue_from_list(url_list)
    response_queue = multiprocessing.Queue()

    url_queue.put(None)
    fw = FetchWorker(url_queue, response_queue, meta_storage, max_fetch_count, fetch_count_window)

    fw.run()
    fw.close()
    response_queue.put(None)
    ow = OptimizeWorker(response_queue, meta_storage, content_storage)
    ow.run()
    ow.close()


def fetch_urls(url_list: Iterable[str], *, meta_storage: StorageBase, content_storage: ContentStorageBase, max_fetch_count: int = 0, fetch_count_window: int = 0, num_fetcher: Optional[int] = None, num_processor: Optional[int] = None, logger) -> None:
    """
    Fetch urls, store meta data into meta_storage and store cached response body to content_storage

    :param url_list: List of urls to be fetched
    :param meta_storage: A storage for meta data, implements StorageBase
    :param content_storage: A storage for response contents, implements ContentStorageBase
    :param max_fetch_count: A max fetch count in fetch_count_window for rate limit. When 0, no rate limit.
    :param fetch_count_window: Seconds for counting fetch for rate limit. When 0, no rate limit.
    :param num_fetcher: A number of fetcher processes
    :param num_processor: A number of processer processes
    :param logger: Logger
    """
    fetch_jobs = []
    optimize_jobs = []
    url_queue = url_queue_from_list(url_list)
    response_queue = multiprocessing.Queue()

    num_fetcher = num_fetcher or multiprocessing.cpu_count() * 4
    num_processor = num_processor or multiprocessing.cpu_count()

    for _ in range(num_fetcher):
        p = FetchWorker(url_queue, response_queue, meta_storage, max_fetch_count, fetch_count_window)
        fetch_jobs.append(p)
        p.start()

    for _ in range(num_processor):
        p = OptimizeWorker(response_queue, meta_storage, content_storage)
        optimize_jobs.append(p)
        p.start()

    for _ in fetch_jobs:
        url_queue.put(None)

    # Wait for fetching all the caches
    for j in fetch_jobs:
        j.join()

    # Now nobody puts an item into `response_queue`, so we adds a terminator.
    for _ in optimize_jobs:
        response_queue.put(None)

    # Wait for optimizing all the caches
    for j in optimize_jobs:
        j.join()


def get_cached_url(url: str, meta_storage: StorageBase) -> Optional[str]:
    meta = get_meta(url, meta_storage)
    if meta is None:
        return None
    now = time.time()
    if meta.expired_at <= now:
        return None
    cached_url = meta.cached_url
    return cached_url
