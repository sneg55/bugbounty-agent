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


@patch("common.ipfs.requests.get")
def test_download_json(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"test": "data"}
    )

    data = download_json("QmTestHash123")
    assert data == {"test": "data"}
