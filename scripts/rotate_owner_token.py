#!/usr/bin/env python3
"""Rotate the owner bearer token: update the identity hash and the token file.

Usage on fs-dev (as root, so /etc/fs-corporation/owner.token is writable):

  FS_CORP_DB=/Data/fs-corporation/data/company.db \\
    /opt/fs-corporation/.venv/bin/python \\
    /opt/fs-corporation/scripts/rotate_owner_token.py \\
    --token-file /etc/fs-corporation/owner.token

Prints only a confirmation line by default. Pass --print-token to emit the new
token once (avoid piping into shell history when possible).
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from company.core import Company


def rotate(
    db_path: Path,
    token_path: Path,
    *,
    print_token: bool,
    write_token_copy: Path | None = None,
) -> int:
    if not token_path.is_file():
        print(f"missing token file: {token_path}", file=sys.stderr)
        return 1
    current = token_path.read_text().strip()
    if not current:
        print(f"token file is empty: {token_path}", file=sys.stderr)
        return 1
    company = Company(str(db_path))
    try:
        new_token = company.rotate_owner_token(current)
        # Atomic replace so a crash mid-write does not leave an empty file.
        fd, tmp_name = tempfile.mkstemp(
            dir=str(token_path.parent), prefix=".owner.token.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(new_token + "\n")
            os.chmod(tmp_name, 0o640)
            try:
                st = token_path.stat()
                os.chown(tmp_name, st.st_uid, st.st_gid)
            except PermissionError:
                # Non-root local runs cannot chown; file still replaces correctly.
                pass
            os.replace(tmp_name, token_path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        # Confirm the file matches the new identity before declaring success.
        if not company.identity_for_token(token_path.read_text().strip()):
            print("rotation wrote a token the database does not accept", file=sys.stderr)
            return 2
        if write_token_copy is not None:
            write_token_copy.parent.mkdir(parents=True, exist_ok=True)
            fd, copy_tmp = tempfile.mkstemp(
                dir=str(write_token_copy.parent), prefix=".token-copy.", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as fh:
                    fh.write(new_token + "\n")
                os.chmod(copy_tmp, 0o600)
                os.replace(copy_tmp, write_token_copy)
            except Exception:
                try:
                    os.unlink(copy_tmp)
                except OSError:
                    pass
                raise
    finally:
        company.close()
    print(f"owner token rotated; written to {token_path}")
    if write_token_copy is not None:
        print(f"owner token copy: {write_token_copy}")
    if print_token:
        print(new_token)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default=os.environ.get("FS_CORP_DB", ""),
        help="SQLite path (or set FS_CORP_DB)",
    )
    parser.add_argument(
        "--token-file",
        default=os.environ.get("FS_CORP_TOKEN_FILE", ""),
        help="Owner token path (or set FS_CORP_TOKEN_FILE)",
    )
    parser.add_argument(
        "--print-token",
        action="store_true",
        help="Print the new token once after writing the file",
    )
    parser.add_argument(
        "--write-token-copy",
        default="",
        help="Also write the new token to this mode-600 path (for operator retrieval)",
    )
    args = parser.parse_args()
    if not args.db or not args.token_file:
        print("Set --db/--token-file or FS_CORP_DB/FS_CORP_TOKEN_FILE", file=sys.stderr)
        return 1
    copy = Path(args.write_token_copy) if args.write_token_copy else None
    return rotate(
        Path(args.db),
        Path(args.token_file),
        print_token=args.print_token,
        write_token_copy=copy,
    )


if __name__ == "__main__":
    raise SystemExit(main())
