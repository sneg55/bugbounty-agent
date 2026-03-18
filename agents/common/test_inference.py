from unittest.mock import MagicMock, patch

from common.inference import complete


@patch("common.inference._get_client")
def test_complete_returns_content(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="4"))]
    )
    mock_get_client.return_value = mock_client

    result = complete(
        messages=[{"role": "user", "content": "rate this"}],
        model="llama-3.3-70b",
        temperature=0.0,
        max_tokens=4,
    )
    assert result == "4"


@patch("common.inference._get_client")
def test_complete_retries_on_failure(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        Exception("API error"),
        MagicMock(choices=[MagicMock(message=MagicMock(content="3"))]),
    ]
    mock_get_client.return_value = mock_client

    result = complete(
        messages=[{"role": "user", "content": "rate this"}],
        model="llama-3.3-70b",
        temperature=0.0,
        max_tokens=4,
    )
    assert result == "3"
    assert mock_client.chat.completions.create.call_count == 2
