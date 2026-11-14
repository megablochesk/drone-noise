import hashlib
from pathlib import Path

HASH_BLOCK_BYTES = 1 << 20


def calculate_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as file:
        while block := file.read(HASH_BLOCK_BYTES):
            digest.update(block)
    return digest.hexdigest()
