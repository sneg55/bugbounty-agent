import json
import time

import requests

from common.config import PINATA_API_KEY, PINATA_SECRET_KEY

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
IPFS_GATEWAY = "https://gateway.pinata.cloud/ipfs"

_REQUEST_TIMEOUT = 30
_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0  # seconds between retries


def _is_retryable(exc: Exception) -> bool:
    """Return True for transient failures that warrant a retry."""
    if isinstance(exc, requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        response = exc.response
        return response is not None and response.status_code >= 500
    return False


def upload_json(data: dict) -> str:
    """Upload JSON to IPFS via Pinata. Returns CID.

    Retries up to _MAX_RETRIES times on transient failures (connection errors,
    5xx responses).
    """
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY,
        "Content-Type": "application/json",
    }
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = requests.post(
                PINATA_PIN_URL,
                headers=headers,
                json={"pinataContent": data},
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()["IpfsHash"]
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES and _is_retryable(exc):
                time.sleep(_RETRY_BACKOFF * (attempt + 1))
                continue
            raise
    raise last_exc  # type: ignore[misc]


def download_json(cid: str) -> dict:
    """Download JSON from IPFS gateway.

    Retries up to _MAX_RETRIES times on transient failures (connection errors,
    5xx responses).
    """
    url = f"{IPFS_GATEWAY}/{cid}"
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES and _is_retryable(exc):
                time.sleep(_RETRY_BACKOFF * (attempt + 1))
                continue
            raise
    raise last_exc  # type: ignore[misc]
