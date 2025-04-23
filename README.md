# FileSync
FileSync is a Python utility for synchronizing files across directories or drives using SHA256 hashes to ensure efficient and accurate file transfers. It avoids duplicating files with identical content, supports multiple source directories, and uses a SQLite database to track file metadata. The script is designed to be cross-platform, robust, and easy to use via a command-line interface.

## Features
* Deduplication: Uses SHA256 hashes to copy only unique files, skipping duplicates.
* Multiple Sources: Sync files from one or more source directories to a single destination.
* Conflict Resolution: Handles naming conflicts by appending numeric suffixes (e.g., file_1.txt).
* Progress Tracking: Displays real-time progress during file syncing.
* SQLite Database: Temporarily stores file metadata for efficient processing (optionally retained).
* Cross-Platform: Works on Windows, macOS, and Linux.
* Error Handling: Gracefully handles invalid paths, permissions issues, and file conflicts.

## Installation

### Prerequisites
Python 3.6+: Ensure Python 3 is installed. Check with:

``` bash
python3 --version
```

### Setup 
Clone the repository from GitHub.
``` bash
git clone https://github.com/yourusername/FileSync.git
cd FileSync
```

Optional: set executable permissions (unix-like environments).
``` bash
chmod +x filesync.py
```

## Usage 

``` bash
python3 filesync.py --source <source_dir> --destination <dest_dir>
```

## Examples

Back up source to destination

``` bash
python3 filesync.py --source /path/to/source --destination /path/to/destination
```

Back up multiple source directories to a single destination directory

``` bash
python3 filesync.py --source /path/to/source1 --source /path/to/source2 --destination /path/to/destination
```

Back up source to destination and keep the sqlite database that FileSync creates

``` bash
python3 filesync.py --source /path/to/source --destination /path/to/destination --keep-db
```


## Options
`--source`: Specify a source directory (repeatable for multiple sources).
`--destination`: Specify the destination directory (required).
`--keep-db`: Retain the files.db SQLite database after syncing (optional).

## Testing
FileSync includes a comprehensive test suite to verify its functionality. The tests cover:

* Syncing files between directories with shared and unique files.
* Handling multiple source directories.
* Resolving file naming conflicts.
* Processing subdirectories.
* Error handling for invalid inputs.
* Database retention with --keep-db.

## Running Tests

Run the tests as shown below


```
python3 -m unittest test_filesync.py -v
```

You should expect something like the following as output


```
test_file_conflict_resolution (test_filesync.TestFileSync) ... ok
test_keep_db_option (test_filesync.TestFileSync) ... ok
test_no_source_directory (test_filesync.TestFileSync) ... ok
...
Ran 8 tests in X.XXXs
OK
```

## License
This project is licensed under the MIT License. See the LICENSE file for details (create one if needed).
