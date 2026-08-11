#!/usr/bin/env python3
"""
Sync generated 心光心理学 articles from this repo into a local Obsidian vault.

GitHub Actions cannot write to a Mac-local Obsidian vault. The intended flow is:
1. GitHub Actions generates and commits article_YYYYMMDD.md.
2. A local scheduled job runs this script with --pull.
3. The script copies articles into the Obsidian knowledge-base folder and updates an index.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_DIR = Path.home() / "Documents" / "Obsidian" / "02-内容创作" / "心光心理学"
DEFAULT_ATTACHMENTS_DIR_NAME = "附件库"
SYNC_STATE_FILE_NAME = ".xingguang-sync-state.json"
ARTICLE_RE = re.compile(r"article_(\d{8})\.md$")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MARKDOWN_LOCAL_ATTACHMENT_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(r"<img\b([^>]*?)\bsrc=[\"']([^\"']+)[\"']([^>]*)>", re.IGNORECASE)
ATTACHMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".7z", ".csv", ".txt", ".md",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def parse_frontmatter(content):
    meta = {}
    body = content
    if content.startswith("---\n"):
        end = content.find("\n---", 4)
        if end != -1:
            raw_meta = content[4:end]
            body = content[end + 4:].lstrip("\n")
            for line in raw_meta.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip().strip('"\'')

    if not meta.get("title"):
        for line in body.splitlines():
            if line.startswith("# "):
                meta["title"] = line[2:].strip()
                break
    return meta, body


def sanitize_filename(text, max_len=72):
    text = text or "未命名文章"
    text = re.sub(r"[\\/:*?\"<>|#\[\]\n\r\t]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len].rstrip(" .") or "未命名文章"


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def state_key(vault_dir, path):
    return path.relative_to(vault_dir).as_posix()


def load_sync_state(vault_dir):
    state_path = vault_dir / SYNC_STATE_FILE_NAME
    if not state_path.exists():
        return {"version": 1, "files": {}}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "files": {}}
    if not isinstance(state, dict):
        return {"version": 1, "files": {}}
    state.setdefault("version", 1)
    state.setdefault("files", {})
    return state


def write_sync_state(vault_dir, state, dry_run=False):
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if dry_run:
        print(f"[dry-run] would write sync state: {vault_dir / SYNC_STATE_FILE_NAME}")
        return
    vault_dir.mkdir(parents=True, exist_ok=True)
    (vault_dir / SYNC_STATE_FILE_NAME).write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def is_remote(src):
    parsed = urllib.parse.urlparse(src)
    return parsed.scheme in {"http", "https"}


def is_wiki_embed(src):
    return src.startswith("[[") or src.startswith("附件库/")


def extension_from_src(src, default=".png"):
    parsed = urllib.parse.urlparse(src)
    ext = Path(parsed.path).suffix.lower()
    if ext and len(ext) <= 8:
        return ".jpg" if ext == ".jpeg" else ext
    return default


def copy_or_download_asset(src, attachments_dir, prefix, index, repo_dir=REPO_DIR, dry_run=False):
    if not src or is_wiki_embed(src) or src.startswith("#") or src.startswith("mailto:"):
        return None

    clean_src = src.strip().strip("<>")
    ext = extension_from_src(clean_src)
    filename = sanitize_filename(f"{prefix}-{index:02d}", max_len=90) + ext
    destination = attachments_dir / filename

    if dry_run or destination.exists():
        return destination

    attachments_dir.mkdir(parents=True, exist_ok=True)
    if is_remote(clean_src):
        req = urllib.request.Request(clean_src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            destination.write_bytes(resp.read())
        return destination

    local_path = Path(urllib.parse.unquote(clean_src)).expanduser()
    if not local_path.is_absolute():
        local_path = (repo_dir / local_path).resolve()
    if not local_path.exists():
        return None
    shutil.copy2(local_path, destination)
    return destination


def obsidian_asset_ref(vault_dir, asset_path, embed=True, label=None):
    rel = asset_path.relative_to(vault_dir).as_posix()
    if embed:
        return f"![[{rel}]]"
    if label:
        return f"[[{rel}|{label}]]"
    return f"[[{rel}]]"


def prepare_content_assets(content, vault_dir, attachments_dir, date_text, title, repo_dir=REPO_DIR, dry_run=False):
    """Copy/download markdown assets into the central Obsidian attachment folder."""
    prefix = f"{date_text}-{sanitize_filename(title, max_len=40)}"
    image_idx = 0
    attachment_idx = 0

    def replace_markdown_image(match):
        nonlocal image_idx
        alt = match.group(1)
        src = match.group(2).strip()
        if src.startswith("[["):
            return match.group(0)
        image_idx += 1
        try:
            asset_path = copy_or_download_asset(
                src,
                attachments_dir,
                f"{prefix}-image",
                image_idx,
                repo_dir=repo_dir,
                dry_run=dry_run,
            )
        except Exception as exc:
            print(f"Warning: failed to sync image {src}: {exc}", file=sys.stderr)
            return match.group(0)
        if not asset_path:
            return match.group(0)
        return obsidian_asset_ref(vault_dir, asset_path, embed=True)

    def replace_html_image(match):
        nonlocal image_idx
        src = match.group(2).strip()
        image_idx += 1
        try:
            asset_path = copy_or_download_asset(
                src,
                attachments_dir,
                f"{prefix}-image",
                image_idx,
                repo_dir=repo_dir,
                dry_run=dry_run,
            )
        except Exception as exc:
            print(f"Warning: failed to sync html image {src}: {exc}", file=sys.stderr)
            return match.group(0)
        if not asset_path:
            return match.group(0)
        return obsidian_asset_ref(vault_dir, asset_path, embed=True)

    def replace_local_attachment(match):
        nonlocal attachment_idx
        label = match.group(1)
        src = match.group(2).strip()
        if is_remote(src) or src.startswith("#"):
            return match.group(0)
        ext = extension_from_src(src, default="")
        if ext.lower() not in ATTACHMENT_EXTENSIONS:
            return match.group(0)
        attachment_idx += 1
        try:
            asset_path = copy_or_download_asset(
                src,
                attachments_dir,
                f"{prefix}-attachment",
                attachment_idx,
                repo_dir=repo_dir,
                dry_run=dry_run,
            )
        except Exception as exc:
            print(f"Warning: failed to sync attachment {src}: {exc}", file=sys.stderr)
            return match.group(0)
        if not asset_path:
            return match.group(0)
        return obsidian_asset_ref(vault_dir, asset_path, embed=False, label=label)

    content = MARKDOWN_IMAGE_RE.sub(replace_markdown_image, content)
    content = HTML_IMAGE_RE.sub(replace_html_image, content)
    content = MARKDOWN_LOCAL_ATTACHMENT_RE.sub(replace_local_attachment, content)
    return content


def infer_column(meta):
    column = meta.get("column", "").strip()
    if column:
        return column

    category = meta.get("category", "")
    if category in {"育儿沟通", "亲子关系", "孩子情绪", "学习陪伴", "家庭教育", "家长成长"}:
        return "育儿与亲子沟通"
    if category in {"自我成长", "情绪照顾", "关系边界", "自我价值", "亲密关系", "职场女性"}:
        return "女性自我成长"
    return "历史文章"


def run_pull(repo_dir):
    result = subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=repo_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError("git pull --ff-only failed; please resolve the local repo state first")


def git_output(repo_dir, *args):
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        output = result.stdout.strip()
        raise RuntimeError(output or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def repo_has_local_changes(repo_dir):
    return bool(git_output(repo_dir, "status", "--porcelain"))


def clone_remote_snapshot(repo_dir, destination):
    origin_url = git_output(repo_dir, "remote", "get-url", "origin")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", origin_url, str(destination)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        output = result.stdout.strip()
        raise RuntimeError(f"remote snapshot clone failed: {output}")
    return destination


@contextmanager
def pull_source(repo_dir):
    """Yield the newest safe article source without overwriting local checkout changes."""
    use_snapshot = repo_has_local_changes(repo_dir)
    if use_snapshot:
        print("Local checkout has uncommitted changes; preserving it and using a fresh remote snapshot.")
    else:
        try:
            run_pull(repo_dir)
            print("Article source: updated local checkout")
            yield repo_dir
            return
        except RuntimeError as exc:
            print(f"Warning: {exc}", file=sys.stderr)
            print("Falling back to a fresh remote snapshot without modifying the local checkout.")

    with tempfile.TemporaryDirectory(prefix="xingguang-obsidian-sync-") as temp_dir:
        snapshot_dir = Path(temp_dir) / "repo"
        clone_remote_snapshot(repo_dir, snapshot_dir)
        print("Article source: fresh remote snapshot")
        yield snapshot_dir


def iter_articles(repo_dir, days=None):
    today = datetime.now()
    for path in sorted(repo_dir.glob("article_*.md")):
        match = ARTICLE_RE.match(path.name)
        if not match:
            continue
        date_text = f"{match.group(1)[:4]}-{match.group(1)[4:6]}-{match.group(1)[6:8]}"
        if days is not None:
            try:
                article_date = datetime.strptime(date_text, "%Y-%m-%d")
            except ValueError:
                article_date = None
            if article_date and (today - article_date).days > days:
                continue
        yield path, date_text


def build_destination(vault_dir, meta, date_text, source_path):
    title = meta.get("title") or source_path.stem
    column = infer_column(meta)
    target_dir = vault_dir / sanitize_filename(column, max_len=40)
    filename = f"{date_text} {sanitize_filename(title)}.md"
    return target_dir / filename


def is_unmodified_synced_file(path, vault_dir, state):
    try:
        key = state_key(vault_dir, path)
        synced_hash = state.get("files", {}).get(key, {}).get("synced_hash")
        if not synced_hash:
            return False
        return text_hash(path.read_text(encoding="utf-8")) == synced_hash
    except (OSError, UnicodeDecodeError, ValueError):
        return False


def cleanup_same_day_articles(destination, date_text, vault_dir, state, dry_run=False, overwrite_local=False):
    if not destination.parent.exists():
        return 0, 0
    removed = 0
    skipped = 0
    for old_path in destination.parent.glob(f"{date_text} *.md"):
        if old_path == destination:
            continue
        if not overwrite_local and not is_unmodified_synced_file(old_path, vault_dir, state):
            skipped += 1
            continue
        removed += 1
        if not dry_run:
            state.get("files", {}).pop(state_key(vault_dir, old_path), None)
            old_path.unlink()
    return removed, skipped


def copy_if_changed(source_text, destination, vault_dir, state, dry_run=False, overwrite_local=False):
    files_state = state.setdefault("files", {})
    key = state_key(vault_dir, destination)
    source_hash = text_hash(source_text)
    existed = destination.exists()
    if destination.exists():
        try:
            current_text = destination.read_text(encoding="utf-8")
            current_hash = text_hash(current_text)
            if current_text == source_text:
                files_state[key] = {
                    "synced_hash": source_hash,
                    "source": "repo",
                    "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                return "unchanged"
        except UnicodeDecodeError:
            return "local_modified"

        last_synced_hash = files_state.get(key, {}).get("synced_hash")
        if not overwrite_local and current_hash != last_synced_hash:
            return "local_modified"

    if dry_run:
        return "would_update" if destination.exists() else "would_create"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source_text, encoding="utf-8")
    files_state[key] = {
        "synced_hash": source_hash,
        "source": "repo",
        "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return "updated" if existed else "created"


def obsidian_link(vault_dir, path, title):
    rel = path.relative_to(vault_dir).with_suffix("").as_posix()
    return f"[[{rel}|{title}]]"


def write_index(vault_dir, records, dry_run=False):
    index_path = vault_dir / "心光心理学内容索引.md"
    lines = [
        "# 心光心理学内容索引",
        "",
        f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 栏目",
        "",
        "- 育儿与亲子沟通：周一、周三、周五",
        "- 女性自我成长：仅手动生成，不参与自动调度",
        "",
        "## 文章",
        "",
        "| 日期 | 栏目 | 分类 | 标题 | 热搜/来源 | 内容家族 |",
        "|---|---|---|---|---|---|",
    ]

    for record in sorted(records, key=lambda item: item["date"], reverse=True):
        meta = record["meta"]
        source = meta.get("hot_ref") or meta.get("source") or ""
        family = meta.get("topic_family") or ""
        title = meta.get("title") or record["source"].stem
        link = obsidian_link(vault_dir, record["destination"], title)
        lines.append(
            f"| {record['date']} | {record['column']} | {meta.get('category', '')} | {link} | {source} | {family} |"
        )

    content = "\n".join(lines) + "\n"
    if dry_run:
        print(f"[dry-run] would write index: {index_path}")
        return
    vault_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(content, encoding="utf-8")


def sync_articles(repo_dir, vault_dir, attachments_dir=None, days=None, dry_run=False, overwrite_local=False):
    records = []
    attachments_dir = attachments_dir or (vault_dir / DEFAULT_ATTACHMENTS_DIR_NAME)
    sync_state = load_sync_state(vault_dir)
    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "local_modified": 0,
        "would_create": 0,
        "would_update": 0,
        "removed_old": 0,
        "skipped_old": 0,
    }
    if not dry_run:
        attachments_dir.mkdir(parents=True, exist_ok=True)

    for source, date_text in iter_articles(repo_dir, days=days):
        content = source.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(content)
        meta.setdefault("date", date_text)
        destination = build_destination(vault_dir, meta, date_text, source)
        title = meta.get("title") or source.stem
        content = prepare_content_assets(
            content,
            vault_dir,
            attachments_dir,
            date_text,
            title,
            repo_dir=repo_dir,
            dry_run=dry_run,
        )
        removed, skipped_old = cleanup_same_day_articles(
            destination,
            date_text,
            vault_dir,
            sync_state,
            dry_run=dry_run,
            overwrite_local=overwrite_local,
        )
        counts["removed_old"] += removed
        counts["skipped_old"] += skipped_old
        status = copy_if_changed(
            content,
            destination,
            vault_dir,
            sync_state,
            dry_run=dry_run,
            overwrite_local=overwrite_local,
        )
        counts[status] = counts.get(status, 0) + 1
        records.append(
            {
                "source": source,
                "destination": destination,
                "date": date_text,
                "column": infer_column(meta),
                "meta": meta,
                "status": status,
            }
        )

    write_index(vault_dir, records, dry_run=dry_run)
    write_sync_state(vault_dir, sync_state, dry_run=dry_run)
    return counts, records


def main():
    parser = argparse.ArgumentParser(description="同步心光心理学文章到本地 Obsidian 知识库")
    parser.add_argument("--repo", default=str(REPO_DIR), help="teen-psychology-insights repo path")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT_DIR), help="Obsidian target folder")
    parser.add_argument("--attachments", help="Obsidian attachment folder; default is <vault>/附件库")
    parser.add_argument(
        "--pull",
        action="store_true",
        help="获取远端最新文章；本地仓库不可安全拉取时自动改用临时远端快照",
    )
    parser.add_argument("--days", type=int, help="只同步最近 N 天文章；默认同步全部")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    parser.add_argument("--overwrite-local", action="store_true", help="允许覆盖 Obsidian 中已被手动修改的文章")
    args = parser.parse_args()

    repo_dir = Path(args.repo).expanduser().resolve()
    vault_dir = Path(args.vault).expanduser().resolve()
    attachments_dir = (
        Path(args.attachments).expanduser().resolve()
        if args.attachments
        else vault_dir / DEFAULT_ATTACHMENTS_DIR_NAME
    )

    if args.pull:
        with pull_source(repo_dir) as source_repo_dir:
            counts, records = sync_articles(
                source_repo_dir,
                vault_dir,
                attachments_dir=attachments_dir,
                days=args.days,
                dry_run=args.dry_run,
                overwrite_local=args.overwrite_local,
            )
    else:
        counts, records = sync_articles(
            repo_dir,
            vault_dir,
            attachments_dir=attachments_dir,
            days=args.days,
            dry_run=args.dry_run,
            overwrite_local=args.overwrite_local,
        )
    print(f"Obsidian target: {vault_dir}")
    print(f"Attachment library: {attachments_dir}")
    print(
        "Synced articles: "
        f"{len(records)} total, "
        f"{counts.get('created', 0)} created, "
        f"{counts.get('updated', 0)} updated, "
        f"{counts.get('unchanged', 0)} unchanged, "
        f"{counts.get('local_modified', 0)} local modified skipped, "
        f"{counts.get('removed_old', 0)} old same-day files removed"
    )
    if counts.get("skipped_old", 0):
        print(f"Skipped old same-day files with local edits: {counts.get('skipped_old', 0)}")
    if args.dry_run:
        print(
            "Dry run: "
            f"{counts.get('would_create', 0)} would create, "
            f"{counts.get('would_update', 0)} would update"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
