#!/usr/bin/env python3

"""
FileSync – One-way sync from source(s) to destination

Behavior:
  • Copies missing files from source(s) to destination (preserving structure)
  • Skips files that already exist with identical content (SHA256)
  • When file exists but content differs → saves new version as filename_1.ext, _2.ext, …
  • Never deletes any files
  • Supports multiple source directories
"""

import argparse
import datetime
import hashlib
import os
import shutil
import sqlite3
import sys
from pathlib import Path


def compute_sha256(filepath):
    """Compute SHA256 hash of a file. Returns None on error."""
    filepath = Path(filepath)
    h = hashlib.sha256()
    try:
        with filepath.open("rb") as f:
            for chunk in iter(lambda: f.read(32768), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError) as e:
        print(f"  Error hashing {filepath}: {e}", file=sys.stderr)
        return None


def get_or_create_db(db_path):
    """Create or open SQLite DB with files table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dest_hashes (
            rel_path TEXT PRIMARY KEY,
            file_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def build_destination_index( destination, conn, cursor):
    """Scan destination once and store relative path → hash."""
    print("Indexing destination (this is done only once per run)...")
    count = 0

    for item in destination.rglob("*"):
        if not item.is_file():
            continue
        try:
            rel = str(item.relative_to(destination))
            h = compute_sha256(item)
            if h:
                cursor.execute(
                    "INSERT OR REPLACE INTO dest_hashes (rel_path, file_hash) VALUES (?, ?)",
                    (rel, h),
                )
                count += 1
                if count % 500 == 0:
                    print(f"  {count:,} files indexed", end="\r")
        except Exception as e:
            print(f"  Skip {item}: {e}", file=sys.stderr)

    conn.commit()
    print(f"\nDestination index complete: {count:,} files")


def copy_with_suffix(src, dst):
    """Copy file, adding _1, _2, … suffix if needed. Returns final path or None."""
    if not dst.exists():
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return dst
        except Exception as e:
            print(f"  Copy failed: {src} → {dst}\n  {e}", file=sys.stderr)
            return None

    # File exists → try numbered suffixes
    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent

    for i in range(1, 1001):
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            try:
                shutil.copy2(src, candidate)
                print(f"  Conflict → saved as {candidate.name}")
                return candidate
            except Exception as e:
                print(f"  Copy failed: {src} → {candidate}\n  {e}", file=sys.stderr)
                return None

        # If same content already exists under this name → no need to copy
        if compute_sha256(candidate) == compute_sha256(src):
            print(f"  Already exists (same content): {candidate.name}")
            return candidate

    print(f"  Gave up after 1000 attempts: {dst}", file=sys.stderr)
    return None


def sync_sources_to_dest( sources, destination, db_path="filesync_temp.db", keep_db=False):
    if not sources:
        print("Error: at least one source directory is required", file=sys.stderr)
        sys.exit(1)

    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)

    # Prepare DB for destination index
    if os.path.exists(db_path) and not keep_db:
        os.unlink(db_path)

    conn = get_or_create_db(db_path)
    cursor = conn.cursor()

    try:
        build_destination_index(destination, conn, cursor)

        total_files = 0
        copied = 0
        skipped = 0
        conflicted = 0

        print("\nSyncing sources → destination...")

        for src_root in sources:
            src_root = src_root.resolve()
            if not src_root.is_dir():
                print(f"  Not a directory, skipping: {src_root}", file=sys.stderr)
                continue

            print(f"  Processing source: {src_root}")

            for src_file in src_root.rglob("*"):
                if not src_file.is_file():
                    continue

                total_files += 1
                rel_path = src_file.relative_to(src_root)
                dst_file = destination / rel_path

                src_hash = compute_sha256(src_file)
                if not src_hash:
                    continue

                # Check if we already know this file in destination
                cursor.execute(
                    "SELECT file_hash FROM dest_hashes WHERE rel_path = ?",
                    (str(rel_path),),
                )
                row = cursor.fetchone()

                if row and row[0] == src_hash:
                    skipped += 1
                    # print(f"  Skip (identical)  {rel_path}")
                    continue

                # Either missing, or content different
                final_path = copy_with_suffix(src_file, dst_file)

                if final_path:
                    copied += 1
                    if final_path != dst_file:
                        conflicted += 1
                    # Update index so future checks see it
                    cursor.execute(
                        "INSERT OR REPLACE INTO dest_hashes (rel_path, file_hash) VALUES (?, ?)",
                        (str(rel_path if final_path == dst_file else final_path.relative_to(destination)), src_hash),
                    )
                    conn.commit()
                else:
                    # failed to copy
                    pass

        print("\n" + "="*60)
        print(f"Finished at {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
        print(f"  Scanned files     : {total_files:,}")
        print(f"  Copied            : {copied:,}")
        print(f"  Skipped (same)    : {skipped:,}")
        print(f"  Conflicts (renamed): {conflicted:,}")

    finally:
        conn.close()
        if not keep_db and os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="One-way file sync: source(s) → destination. No deletes."
    )
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        help="Source directory (can be used multiple times)",
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Target / backup directory",
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="Keep temporary SQLite database after run",
    )

    args = parser.parse_args()

    sources = [Path(s).expanduser().resolve() for s in args.source]
    dest = Path(args.destination).expanduser().resolve()

    print(f"Starting sync  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  Destination: {dest}")
    print(f"  Sources:")
    for s in sources:
        print(f"    • {s}")

    sync_sources_to_dest(
        sources=sources,
        destination=dest,
        keep_db=args.keep_db,
    )


if __name__ == "__main__":
    main()
