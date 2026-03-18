import json

import requests

from common.config import PINATA_API_KEY, PINATA_SECRET_KEY

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
IPFS_GATEWAY = "https://gateway.pinata.cloud/ipfs"


def upload_json(data: dict) -> str:
    """Upload JSON to IPFS via Pinata. Returns CID."""
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY,
        "Content-Type": "application/json",
    }
    response = requests.post(
        PINATA_PIN_URL,
        headers=headers,
        json={"pinataContent": data},
    )
    response.raise_for_status()
    return response.json()["IpfsHash"]


def download_json(cid: str) -> dict:
    """Download JSON from IPFS gateway."""
    url = f"{IPFS_GATEWAY}/{cid}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
