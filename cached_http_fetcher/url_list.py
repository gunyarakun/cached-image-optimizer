from typing import Dict, Iterable, Set
from urllib.parse import urlparse


def urls_per_domain(url_list: Iterable[str]) -> Dict[str, Set[str]]:
    results = {}
    for url_str in url_list:
        if url_str is None:
            continue
        try:
            url = urlparse(url_str)
            if url.netloc in results:
                results[url.netloc].add(url.geturl())
            else:
                results[url.netloc] = {url.geturl()}
        except ValueError:
            pass
    return results
