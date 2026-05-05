#!/usr/bin/env python3
"""
Sync generated 心光心理学 articles from this repo into a local Obsidian vault.

GitHub Actions cannot write to a Mac-local Obsidian vault. The intended flow is:
1. GitHub Actions generates and commits article_YYYYMMDD.md.
2. A local scheduled job runs this script with --pull.
3. The script copies articles into the Obsidian knowledge-base folder and updates an index.
"""

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_DIR = Path.home() / "Documents" / "Obsidian" / "02-内容创作" / "心光心理学"
ARTICLE_RE = re.compile(r"article_(\d{8})\.md$")


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


def copy_if_changed(source, destination, dry_run=False):
    source_text = source.read_text(encoding="utf-8")
    existed = destination.exists()
    if destination.exists():
        try:
            if destination.read_text(encoding="utf-8") == source_text:
                return "unchanged"
        except UnicodeDecodeError:
            pass
    if dry_run:
        return "would_update" if destination.exists() else "would_create"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source_text, encoding="utf-8")
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
        "- 女性自我成长：周二、周四、周六",
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


def sync_articles(repo_dir, vault_dir, days=None, dry_run=False):
    records = []
    counts = {"created": 0, "updated": 0, "unchanged": 0, "would_create": 0, "would_update": 0}

    for source, date_text in iter_articles(repo_dir, days=days):
        content = source.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(content)
        meta.setdefault("date", date_text)
        destination = build_destination(vault_dir, meta, date_text, source)
        status = copy_if_changed(source, destination, dry_run=dry_run)
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
    return counts, records


def main():
    parser = argparse.ArgumentParser(description="同步心光心理学文章到本地 Obsidian 知识库")
    parser.add_argument("--repo", default=str(REPO_DIR), help="teen-psychology-insights repo path")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT_DIR), help="Obsidian target folder")
    parser.add_argument("--pull", action="store_true", help="先执行 git pull --ff-only")
    parser.add_argument("--days", type=int, help="只同步最近 N 天文章；默认同步全部")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    args = parser.parse_args()

    repo_dir = Path(args.repo).expanduser().resolve()
    vault_dir = Path(args.vault).expanduser().resolve()

    if args.pull:
        run_pull(repo_dir)

    counts, records = sync_articles(repo_dir, vault_dir, days=args.days, dry_run=args.dry_run)
    print(f"Obsidian target: {vault_dir}")
    print(
        "Synced articles: "
        f"{len(records)} total, "
        f"{counts.get('created', 0)} created, "
        f"{counts.get('updated', 0)} updated, "
        f"{counts.get('unchanged', 0)} unchanged"
    )
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
