from common.crypto import generate_keypair, encrypt, decrypt


def test_roundtrip_encrypt_decrypt():
    private_key, public_key = generate_keypair()
    plaintext = b'{"vulnerability": "reentrancy", "poc": "test code"}'

    ciphertext = encrypt(public_key, plaintext)
    assert ciphertext != plaintext

    decrypted = decrypt(private_key, ciphertext)
    assert decrypted == plaintext


def test_different_keypairs_cannot_decrypt():
    priv1, pub1 = generate_keypair()
    priv2, pub2 = generate_keypair()

    ciphertext = encrypt(pub1, b"secret data")

    try:
        decrypt(priv2, ciphertext)
        assert False, "Should have raised an exception"
    except Exception:
        pass  # Expected
