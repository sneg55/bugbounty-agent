import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Chain
RPC_URL = os.getenv("RPC_URL", "https://sepolia.base.org")
CHAIN_ID = int(os.getenv("CHAIN_ID", "84532"))

# Inference
INFERENCE_BASE_URL = os.getenv("INFERENCE_BASE_URL", "https://api.venice.ai/api/v1")
INFERENCE_API_KEY = os.getenv("INFERENCE_API_KEY", "")
INFERENCE_MODEL = os.getenv("INFERENCE_MODEL", "llama-3.3-70b")

# IPFS
PINATA_API_KEY = os.getenv("PINATA_API_KEY", "")
PINATA_SECRET_KEY = os.getenv("PINATA_SECRET_KEY", "")

# Deployments
DEPLOYMENTS_FILE = os.getenv("DEPLOYMENTS_FILE", str(Path(__file__).parent.parent.parent / "deployments.json"))


def load_deployments() -> dict:
    with open(DEPLOYMENTS_FILE) as f:
        return json.load(f)
