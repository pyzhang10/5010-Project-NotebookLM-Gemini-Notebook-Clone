import pytest

from ingestion import _validate_public_url


@pytest.mark.parametrize("url", ["http://127.0.0.1/a", "http://localhost/a"])
def test_local_urls_are_blocked(url):
    with pytest.raises(ValueError):
        _validate_public_url(url)

