import pytest

from url_list import urls_per_domain
from fetcher import fetch_images, fetch_images_single
from storage import MemoryStorage


def test_fetch_images_single_memory(images, logger, requests_mock):
    for url, obj in images.items():
        requests_mock.add(
            requests_mock.GET, url, body=obj['image']
        )

    url_dict = urls_per_domain(images.keys())

    # memory storage
    meta_memory_storage = MemoryStorage()
    image_memory_storage = MemoryStorage()

    fetch_images_single(url_dict, meta_storage=meta_memory_storage, image_storage=image_memory_storage, logger=logger)

    meta_storage = meta_memory_storage.dict_for_debug()
    image_storage = image_memory_storage.dict_for_debug()

    assert len(requests_mock.calls) == len(images)
    assert len(meta_storage) == len(images)
    assert len(image_storage) == len(images)

    # TODO: Add more tests