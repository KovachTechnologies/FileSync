from pathlib import Path
import hashlib
import os

def compute_file_hash(filepath, hash_algo="sha256", chunk_size=1024*1024):
    """Compute hash of a file. Reads in chunks → memory efficient."""
    hash_func = hashlib.new(hash_algo)
    try:
        with filepath.open("rb") as f:
            while chunk := f.read(chunk_size):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not read {filepath}: {e}")
        return ""


def find_and_report_matches(
    source_dir,
    target_dir,
    hash_algorithm="sha256",
    print_progress=True,
    match_by_hash_only=False
):
    """
    Finds files in source_dir (non-recursive) that have identical content
    anywhere in target_dir (recursive).

    Parameters:
        match_by_hash_only : bool
            If True:  match purely by content hash (filename is ignored)
            If False: match only if both filename (case-insensitive) AND hash match
    Returns list of (source_path, target_path) tuples for matches.
    """
    source_path = Path(source_dir).resolve()
    target_path = Path(target_dir).resolve()

    # ── Phase 1: Hash all files in source (non-recursive)
    source_hashes = {}          # hash -> source path
    source_names_for_debug = {} # name.lower() -> path (only used when not hash-only)

    print(f"Hashing source files in: {source_path}")

    for item in source_path.iterdir():
        if not item.is_file():
            continue

        h = compute_file_hash(item, hash_algo=hash_algorithm)
        if not h:
            continue

        name_lower = item.name.lower()

        if match_by_hash_only:
            # We don't care about names → just store hash → path
            if h in source_hashes:
                print(f"  Warning: duplicate content in source (different names):")
                print(f"           {source_hashes[h].name}  vs  {item.name}")
            source_hashes[h] = item
        else:
            # Original behavior: track names for quick filtering
            if name_lower in source_names_for_debug:
                print(f"  Warning: name collision in source: {item.name}")
            source_names_for_debug[name_lower] = item

            if h in source_hashes:
                print(f"  Warning: identical content in source (different names):")
                print(f"           {source_hashes[h].name}  vs  {item.name}")

            source_hashes[h] = item

    if not source_hashes:
        print("No readable files found in source directory.")
        return []

    print(f"→ Found {len(source_hashes)} unique source files (by content)")

    # ── Phase 2: Walk target recursively and compare
    matches = []  # list of (source_path, target_path)

    print(f"\nScanning target recursively: {target_path}")
    print(f"Matching mode: {'hash only' if match_by_hash_only else 'name + hash'}")

    files_checked = 0
    for root, _, files in os.walk(target_path):
        for filename in files:
            files_checked += 1
            candidate = Path(root) / filename

            # Optimization: skip hashing if name doesn't match (only when using name filter)
            if not match_by_hash_only:
                if candidate.name.lower() not in source_names_for_debug:
                    continue

            if print_progress and files_checked % 500 == 0:
                print(f"  Checked {files_checked:,} files...")

            h = compute_file_hash(candidate, hash_algo=hash_algorithm)
            if not h:
                continue

            if h in source_hashes:
                matches.append((source_hashes[h], candidate))

    print(f"→ Finished. Checked ~{files_checked:,} files.")
    return sorted(matches, key=lambda x: x[1])


def delete_matching_source_files(matches, dry_run=True):
    """
    Deletes source files that have matches in target.
    Use dry_run=True to only print what would be deleted.
    """
    if not matches:
        print("No files to delete.")
        return

    print(f"\nFound {len(matches)} file(s) in source that exist (by content) in target.\n")

    to_delete = set()
    for src, tgt in matches:
        if src not in to_delete:
            try:
                rel = tgt.relative_to(target_dir)  # nicer display
                print(f"  Would delete: {src}  (match: {rel})")
            except:
                print(f"  Would delete: {src}  (match: {tgt})")
            to_delete.add(src)

    if not to_delete:
        return

    count = len(to_delete)
    print(f"\nTotal unique source files to delete: {count}")

    if dry_run:
        print("\nDRY RUN — no files were actually deleted.")
        print("Set dry_run=False to perform deletion.")
        return

    confirm = input("\nDelete these files? [y/N]: ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("Aborted.")
        return

    deleted = 0
    failed = 0
    for path in to_delete:
        try:
            path.unlink()
            print(f"Deleted: {path}")
            deleted += 1
        except Exception as e:
            print(f"Failed to delete {path}: {e}")
            failed += 1

    print(f"\nSummary: {deleted} deleted, {failed} failed.")


# ────────────────────────────────────────────────
#           Main execution
# ────────────────────────────────────────────────
if __name__ == "__main__":
    SOURCE_FOLDER = "/Volumes/Expansion/PICS"
    TARGET_FOLDER = "/Users/danielkovach/Documents/PICS"

    print("=== Finding exact content matches ===\n")

    matches = find_and_report_matches(
        SOURCE_FOLDER,
        TARGET_FOLDER,
        hash_algorithm="sha256",
        print_progress=True,
        match_by_hash_only=False       # ← change this flag to control behavior
                                      # True  = match by hash only (ignore names)
                                      # False = match by name AND hash (original)
    )

    if matches:
        print(f"\nFound {len(matches)} match(es)\n")
        # Optional: show matches
        # for src, tgt in matches:
        #     print(f"  {src}  →  {tgt}")

        # Perform deletion (careful!)
        delete_matching_source_files(matches, dry_run=True) # dry_run = False deletes the files after prompting the user
    else:
        print("\nNo matching files found (by content). Nothing to delete.")
