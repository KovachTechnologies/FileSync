#!/usr/bin/env python3

"""
FileSync: Synchronizes files across directories or drives using SHA256 hashes.

Usage:
    python filesync.py --source <source_dir> [--source <source_dir> ...] --destination <dest_dir> [--keep-db]

Description:
    Copies files from source directories to a destination, avoiding duplicates by comparing SHA256 hashes.
    Stores file metadata in a SQLite database for efficient processing.
"""

import argparse
import datetime
import hashlib
import os
import shutil
import sqlite3
import sys
from typing import List, Optional, Tuple


def compute_sha256(file_path: str) -> Optional[str]:
    """Compute the SHA256 hash of a file."""
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (IOError, OSError) as e:
        print(f"Error hashing file '{file_path}': {e}")
        return None


def initialize_database(cursor: sqlite3.Cursor) -> sqlite3.Cursor:
    """Create or reset the files table in the SQLite database."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            root_dir TEXT,
            file_path TEXT,
            file_hash TEXT
        )
    """)
    cursor.execute("DELETE FROM files")
    return cursor


def collect_files(root_dirs: List[str]) -> List[Tuple[str, str, str]]:
    """Collect file paths and their hashes from source directories."""
    files = []
    script_dir = os.path.dirname(os.path.realpath(__file__))

    for root_dir in root_dirs:
        try:
            os.chdir(root_dir)
            for root, _, filenames in os.walk("."):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    file_hash = compute_sha256(file_path)
                    if file_hash:
                        files.append((root_dir, file_path, file_hash))
                    else:
                        print(f"Skipping file '{file_path}' due to invalid hash")
        except (OSError, PermissionError) as e:
            print(f"Error accessing directory '{root_dir}': {e}")
        finally:
            os.chdir(script_dir)

    return files


def sync_files(
    root_dirs: List[str],
    destination: str,
    keep_db: bool = False
) -> None:
    """Synchronize files from source directories to the destination."""
    if not root_dirs:
        print("Error: At least one source directory must be provided")
        sys.exit(1)

    if not destination:
        print("Error: Destination directory must be provided")
        sys.exit(1)

    # Ensure destination exists
    os.makedirs(destination, exist_ok=True)

    # Initialize database
    db_file = "files.db"
    if os.path.exists(db_file) and not keep_db:
        os.remove(db_file)

    print("Aggregating file names from sources...")
    files = collect_files(root_dirs)

    with sqlite3.connect(db_file) as conn:
        cursor = initialize_database(conn.cursor())
        if files:
            cursor.executemany(
                "INSERT INTO files (root_dir, file_path, file_hash) VALUES (?, ?, ?)",
                files
            )
            conn.commit()

        # Process unique files
        cursor.execute("SELECT * FROM files GROUP BY file_path, file_hash")
        rows = cursor.fetchall()
        total_files = len(rows)
        print(f"Items to process: {total_files}")

        # Copy files to destination
        print("Copying files to destination...")
        for idx, row in enumerate(rows, 1):
            if idx % 100 == 0 or idx == total_files:
                percent = 100.0 * idx / total_files
                print(f"{percent:.2f}% complete", end="\r" if idx < total_files else "\n")

            root_dir, file_path, file_hash = row[1], row[2], row[3]
            src_path = os.path.join(root_dir, file_path)
            dst_path = os.path.join(destination, file_path)

            try:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                if os.path.exists(dst_path):
                    if compute_sha256(dst_path) == file_hash:
                        continue
                    # Handle naming conflicts
                    base, ext = os.path.splitext(dst_path)
                    for i in range(1, 1000):  # Limit attempts to avoid infinite loops
                        new_path = f"{base}_{i}{ext}"
                        if not os.path.exists(new_path):
                            shutil.copy2(src_path, new_path)
                            break
                        if compute_sha256(new_path) == file_hash:
                            break
                else:
                    shutil.copy2(src_path, dst_path)
            except (IOError, OSError) as e:
                print(f"Error copying '{src_path}' to '{dst_path}': {e}")

    if not keep_db:
        os.remove(db_file)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Synchronize files across directories using SHA256 hashes."
    )
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        help="Source directory to sync from (can be specified multiple times)"
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Destination directory to sync to"
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="Keep the SQLite database after syncing"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    print(f"Starting backup at {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    sync_files(
        root_dirs=args.source,
        destination=args.destination,
        keep_db=args.keep_db
    )
    print("Backup completed.")
