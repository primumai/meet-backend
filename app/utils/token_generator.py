import uuid
import hashlib

def generate_token():
    raw = str(uuid.uuid4())
    return hashlib.sha256(raw.encode()).hexdigest()[:40]
