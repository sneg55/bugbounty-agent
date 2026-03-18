from ecies import encrypt as ecies_encrypt, decrypt as ecies_decrypt
from ecies.utils import generate_eth_key


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate an ECIES keypair. Returns (private_key_hex, public_key_hex)."""
    key = generate_eth_key()
    return key.to_hex().encode(), key.public_key.to_hex().encode()


def encrypt(public_key: bytes, plaintext: bytes) -> bytes:
    """Encrypt data with an ECIES public key."""
    return ecies_encrypt(public_key.decode() if isinstance(public_key, bytes) else public_key, plaintext)


def decrypt(private_key: bytes, ciphertext: bytes) -> bytes:
    """Decrypt data with an ECIES private key."""
    return ecies_decrypt(private_key.decode() if isinstance(private_key, bytes) else private_key, ciphertext)
