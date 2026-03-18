from unittest.mock import patch, MagicMock

from common.ipfs import upload_json, download_json


@patch("common.ipfs.requests.post")
def test_upload_json(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"IpfsHash": "QmTestHash123"}
    )

    cid = upload_json({"test": "data"})
    assert cid == "QmTestHash123"


@patch("common.ipfs.requests.post")
def test_upload_json_passes_timeout(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"IpfsHash": "Qm..."})
    upload_json({"test": "data"})
    # Verify timeout was passed
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs.get("timeout") == 30 or call_kwargs[1].get("timeout") == 30


@patch("common.ipfs.requests.get")
def test_download_json(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"test": "data"}
    )

    data = download_json("QmTestHash123")
    assert data == {"test": "data"}
