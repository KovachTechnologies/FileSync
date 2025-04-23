#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestFileSync(unittest.TestCase):
    def setUp(self):
        """Set up temporary directories and files for each test."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.dir_a = os.path.join(self.temp_dir, "A")
        self.dir_b = os.path.join(self.temp_dir, "B")
        os.makedirs(self.dir_a, exist_ok=True)
        os.makedirs(self.dir_b, exist_ok=True)

        # Create files with unique content
        self.create_file(os.path.join(self.dir_a, "a.txt"), "Content of a.txt")
        self.create_file(os.path.join(self.dir_a, "b.txt"), "Common content")
        self.create_file(os.path.join(self.dir_b, "b.txt"), "Common content")
        self.create_file(os.path.join(self.dir_b, "c.txt"), "Content of c.txt")

    def tearDown(self):
        """Clean up temporary directories after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if os.path.exists("files.db"):
            os.remove("files.db")

    def create_file(self, path: str, content: str):
        """Helper to create a file with given content."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def run_filesync(self, sources: list, destination: str, keep_db: bool = False) -> subprocess.CompletedProcess:
        """Run filesync.py with the given arguments."""
        args = [sys.executable, "filesync.py", "--destination", destination]
        for source in sources:
            args.extend(["--source", source])
        if keep_db:
            args.append("--keep-db")
        try:
            return subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            # Return the result even if the command failed, so tests can inspect it
            return e
        except FileNotFoundError as e:
            self.fail(f"Error: Could not find Python executable or filesync.py: {e}")

    def test_sync_a_to_b(self):
        """Test syncing from A to B; only a.txt should be copied."""
        result = self.run_filesync(sources=[self.dir_a], destination=self.dir_b)
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected files in B: a.txt, b.txt, c.txt
        expected_files_b = {"a.txt", "b.txt", "c.txt"}
        actual_files_b = set(os.listdir(self.dir_b))
        self.assertEqual(actual_files_b, expected_files_b, "Unexpected files in B")

        # Verify file contents
        self.assertEqual(
            Path(os.path.join(self.dir_b, "a.txt")).read_text(),
            "Content of a.txt",
            "a.txt content mismatch"
        )
        self.assertEqual(
            Path(os.path.join(self.dir_b, "b.txt")).read_text(),
            "Common content",
            "b.txt content mismatch"
        )
        self.assertEqual(
            Path(os.path.join(self.dir_b, "c.txt")).read_text(),
            "Content of c.txt",
            "c.txt content mismatch"
        )

        # Verify files in A remain unchanged
        expected_files_a = {"a.txt", "b.txt"}
        actual_files_a = set(os.listdir(self.dir_a))
        self.assertEqual(actual_files_a, expected_files_a, "Files in A modified unexpectedly")

        # Database should be deleted
        self.assertFalse(os.path.exists("files.db"), "Database file was not deleted")

    def test_sync_b_to_a(self):
        """Test syncing from B to A; only c.txt should be copied."""
        result = self.run_filesync(sources=[self.dir_b], destination=self.dir_a)
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected files in A: a.txt, b.txt, c.txt
        expected_files_a = {"a.txt", "b.txt", "c.txt"}
        actual_files_a = set(os.listdir(self.dir_a))
        self.assertEqual(actual_files_a, expected_files_a, "Unexpected files in A")

        # Verify file contents
        self.assertEqual(
            Path(os.path.join(self.dir_a, "a.txt")).read_text(),
            "Content of a.txt",
            "a.txt content mismatch"
        )
        self.assertEqual(
            Path(os.path.join(self.dir_a, "b.txt")).read_text(),
            "Common content",
            "b.txt content mismatch"
        )
        self.assertEqual(
            Path(os.path.join(self.dir_a, "c.txt")).read_text(),
            "Content of c.txt",
            "c.txt content mismatch"
        )

        # Verify files in B remain unchanged
        expected_files_b = {"b.txt", "c.txt"}
        actual_files_b = set(os.listdir(self.dir_b))
        self.assertEqual(actual_files_b, expected_files_b, "Files in B modified unexpectedly")

        # Database should be deleted
        self.assertFalse(os.path.exists("files.db"), "Database file was not deleted")

    def test_sync_multiple_sources(self):
        """Test syncing from both A and B to a new directory."""
        dir_c = os.path.join(self.temp_dir, "C")
        os.makedirs(dir_c, exist_ok=True)

        result = self.run_filesync(sources=[self.dir_a, self.dir_b], destination=dir_c)
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected files in C: a.txt, b.txt, c.txt
        expected_files_c = {"a.txt", "b.txt", "c.txt"}
        actual_files_c = set(os.listdir(dir_c))
        self.assertEqual(actual_files_c, expected_files_c, "Unexpected files in C")

        # Verify file contents
        self.assertEqual(
            Path(os.path.join(dir_c, "a.txt")).read_text(),
            "Content of a.txt",
            "a.txt content mismatch"
        )
        self.assertEqual(
            Path(os.path.join(dir_c, "b.txt")).read_text(),
            "Common content",
            "b.txt content mismatch"
        )
        self.assertEqual(
            Path(os.path.join(dir_c, "c.txt")).read_text(),
            "Content of c.txt",
            "c.txt content mismatch"
        )

    def test_keep_db_option(self):
        """Test that --keep-db retains the database file."""
        result = self.run_filesync(sources=[self.dir_a], destination=self.dir_b, keep_db=True)
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Database should exist
        self.assertTrue(os.path.exists("files.db"), "Database file was deleted despite --keep-db")

    def test_no_source_directory(self):
        """Test error handling when no source directory is provided."""
        result = self.run_filesync(sources=[], destination=self.dir_b)

        # Check command failed with non-zero exit code
        self.assertEqual(result.returncode, 2, f"Expected exit code 2, got {result.returncode}")
        self.assertIn(
            "the following arguments are required: --source",
            result.stderr,
            "Expected error message not found"
        )

    def test_nonexistent_source(self):
        """Test error handling for nonexistent source directory."""
        nonexistent_dir = os.path.join(self.temp_dir, "Nonexistent")
        result = self.run_filesync(sources=[nonexistent_dir], destination=self.dir_b)
        self.assertEqual(result.returncode, 0, f"Command failed unexpectedly: {result.stderr}")

        # Check error message in stdout
        self.assertIn(f"Error accessing directory '{nonexistent_dir}'", result.stdout)

    def test_file_conflict_resolution(self):
        """Test handling of files with same name but different content."""
        # Create a conflicting a.txt in B with different content
        self.create_file(os.path.join(self.dir_b, "a.txt"), "Different content")

        result = self.run_filesync(sources=[self.dir_a], destination=self.dir_b)
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected files in B: a.txt, a_1.txt (or similar), b.txt, c.txt
        actual_files_b = set(os.listdir(self.dir_b))
        self.assertTrue(
            any(f.startswith("a_") and f.endswith(".txt") for f in actual_files_b),
            "Expected renamed file for a.txt conflict"
        )
        self.assertIn("b.txt", actual_files_b, "b.txt missing")
        self.assertIn("c.txt", actual_files_b, "c.txt missing")

        # Verify original a.txt in B is unchanged
        self.assertEqual(
            Path(os.path.join(self.dir_b, "a.txt")).read_text(),
            "Different content",
            "Original a.txt in B was overwritten"
        )

    def test_subdirectories(self):
        """Test syncing files in subdirectories."""
        # Create subdirectory in A with a file
        sub_dir = os.path.join(self.dir_a, "subdir")
        os.makedirs(sub_dir, exist_ok=True)
        self.create_file(os.path.join(sub_dir, "d.txt"), "Content of d.txt")

        result = self.run_filesync(sources=[self.dir_a], destination=self.dir_b)
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Check d.txt in B/subdir
        dst_subdir_file = os.path.join(self.dir_b, "subdir", "d.txt")
        self.assertTrue(os.path.exists(dst_subdir_file), "d.txt not copied to subdirectory")
        self.assertEqual(
            Path(dst_subdir_file).read_text(),
            "Content of d.txt",
            "d.txt content mismatch"
        )


if __name__ == "__main__":
    unittest.main()
