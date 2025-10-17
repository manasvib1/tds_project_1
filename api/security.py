from .settings import settings

def verify_secret(secret: str) -> bool:
    if len(secret) != len(settings.EXPECTED_SECRET):
        return False
    diff = 0
    for x, y in zip(secret.encode(), settings.EXPECTED_SECRET.encode()):
        diff |= x ^ y
    return diff == 0
