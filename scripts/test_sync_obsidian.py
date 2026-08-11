#!/usr/bin/env python3
import subprocess
import tempfile
import unittest
from pathlib import Path

import sync_obsidian as sync


def run_git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class SyncSourceTests(unittest.TestCase):
    def test_dirty_checkout_uses_snapshot_and_preserves_local_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            origin = root / "origin.git"
            seed = root / "seed"
            checkout = root / "checkout"

            run_git(root, "init", "--bare", str(origin))
            run_git(root, "init", str(seed))
            run_git(seed, "config", "user.name", "Sync Test")
            run_git(seed, "config", "user.email", "sync-test@example.com")
            (seed / "article_20260811.md").write_text("# Remote article\n", encoding="utf-8")
            run_git(seed, "add", "article_20260811.md")
            run_git(seed, "commit", "-m", "seed")
            run_git(seed, "branch", "-M", "main")
            run_git(seed, "remote", "add", "origin", str(origin))
            run_git(seed, "push", "-u", "origin", "main")
            run_git(origin, "symbolic-ref", "HEAD", "refs/heads/main")
            run_git(root, "clone", str(origin), str(checkout))

            local_note = checkout / "local-note.txt"
            local_note.write_text("preserve me\n", encoding="utf-8")

            with sync.pull_source(checkout) as source:
                self.assertNotEqual(source, checkout)
                self.assertEqual(
                    (source / "article_20260811.md").read_text(encoding="utf-8"),
                    "# Remote article\n",
                )

            self.assertEqual(local_note.read_text(encoding="utf-8"), "preserve me\n")

    def test_asset_copy_resolves_against_snapshot_repo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "repo"
            attachments = root / "vault" / "附件库"
            source = repo / "assets" / "cover.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"png-test")

            copied = sync.copy_or_download_asset(
                "assets/cover.png",
                attachments,
                "article-image",
                1,
                repo_dir=repo,
            )

            self.assertEqual(copied.read_bytes(), b"png-test")


if __name__ == "__main__":
    unittest.main()
