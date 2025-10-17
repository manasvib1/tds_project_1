import base64, re
from typing import Tuple

DATA_URI_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.IGNORECASE)

class DataUriError(Exception):
    pass

def decode_data_uri(uri: str) -> Tuple[str, bytes]:
    m = DATA_URI_RE.match(uri)
    if not m:
        raise DataUriError("Unsupported data URI")
    mime, b64 = m.groups()
    return mime, base64.b64decode(b64)
