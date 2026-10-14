"""Publisher tool: create an Ed25519 key pair without printing private material."""
import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def write_new(path: Path, content: bytes, mode: int):
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as handle:
        handle.write(content)


def main():
    parser = argparse.ArgumentParser(description="Generate publisher Ed25519 key files")
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM,
                                           serialization.PublicFormat.SubjectPublicKeyInfo)
    write_new(args.private_key, private, 0o600)
    try:
        write_new(args.public_key, public, 0o644)
    except Exception:
        args.private_key.unlink(missing_ok=True)
        raise
    print("Created an Ed25519 key pair. Keep the private key offline and out of Git.")


if __name__ == "__main__":
    main()
