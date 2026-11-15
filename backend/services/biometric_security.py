
import os

import numpy as np
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv


load_dotenv()

ENCRYPTION_KEY = os.getenv("BIOMETRIC_ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError("Biometric encryption key is missing from .env")

try:
    cipher = Fernet(ENCRYPTION_KEY.encode())
except Exception as error:
    raise RuntimeError("Invalid biometric encryption key") from error


def encrypt_embedding(embedding):
    """Convert a face embedding into encrypted bytes."""

    embedding = np.asarray(embedding, dtype=np.float32)

    if embedding.shape != (128,):
        raise ValueError("Expected a 128-dimensional face embedding")

    raw_data = embedding.tobytes()

    encrypted_data = cipher.encrypt(raw_data)

    return encrypted_data


def decrypt_embedding(encrypted_data):
    """Decrypt stored bytes back into a face embedding."""

    try:
        raw_data = cipher.decrypt(encrypted_data)
    except InvalidToken:
        raise ValueError("Unable to decrypt face template")

    embedding = np.frombuffer(raw_data, dtype=np.float32)

    if embedding.shape != (128,):
        raise ValueError("Invalid face template dimensions")

    return embedding.copy()

