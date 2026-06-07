from app.services.crypto import decrypt_credentials, encrypt_credentials


def test_encrypt_decrypt_roundtrip():
    blob = encrypt_credentials("admin", "secret")
    assert blob is not None
    username, password = decrypt_credentials(blob)
    assert username == "admin"
    assert password == "secret"