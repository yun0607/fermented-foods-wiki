#!/usr/bin/env python3
"""Offline checks for the eight-source Markdown Wiki."""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = (
    "發酵的基本原理", "常見發酵食品介紹", "發酵食品與健康",
    "自製發酵食品", "食品安全與保存",
)
CATEGORIES = set(TOPICS)
SOURCE_URLS = dict(zip(
    (f"SRC-{number:03}" for number in range(1, 9)),
    (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC7925329/",
        "https://www.pubs.ext.vt.edu/content/pubs_ext_vt_edu/en/FST/FST-328/FST-328.html",
        "https://nutritionsource.hsph.harvard.edu/probiotics/",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC9020749/",
        "https://extension.umn.edu/food/preparing/cooking-at-home/food-preservation/fermentation",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC8117929/",
        "https://nchfp.uga.edu/how/ferment/general-information-fermenting/general-information-on-fermenting/",
        "https://www.nccih.nih.gov/health/probiotics-usefulness-and-safety",
    ),
))
CITATION = re.compile(r"\[((?:SRC-\d{3}|S\d{3,}))\]")
ARTICLE_ID = re.compile(r"W\d{3,}")
STATES = {"draft", "approved", "blocked", "needs_human_review"}
REQUIRED = (
    "AGENTS.md", "README.md", "sources.json", "wiki/index.md", "wiki/log.md",
    "raw", "wiki/articles", "wiki/review", "templates", "reports",
)


def load_sources(errors):
    try:
        records = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"sources.json: {exc}")
        return {}
    if not isinstance(records, list):
        errors.append("sources.json must be a list")
        return {}

    sources = {}
    seen = {field: set() for field in ("url", "raw_path", "doi")}
    raw_root = ROOT / "raw"
    for ordinal, record in enumerate(records, 1):
        if not isinstance(record, dict):
            errors.append(f"source #{ordinal} must be an object")
            continue
        sid = record.get("source_id")
        if not isinstance(sid, str) or sid not in SOURCE_URLS:
            errors.append(f"source #{ordinal}: unlisted source ID {sid!r}")
            continue
        if sid in sources:
            errors.append(f"duplicate source ID: {sid}")
            continue
        sources[sid] = record
        for field in ("title", "authors", "year", "url", "source_type", "raw_path", "accessed_on", "status"):
            if field not in record:
                errors.append(f"{sid}: missing {field}")
        title, authors = record.get("title"), record.get("authors")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{sid}: missing title")
        if not isinstance(authors, list) or not authors or not all(isinstance(a, str) and a.strip() for a in authors):
            errors.append(f"{sid}: missing author or institution")
        if record.get("year") is not None and type(record["year"]) is not int:
            errors.append(f"{sid}: year must be an integer or null")
        if record.get("url") != SOURCE_URLS[sid]:
            errors.append(f"{sid}: URL differs from the specified source")
        if record.get("status") not in STATES | {"pending"}:
            errors.append(f"{sid}: invalid status")
        if record.get("source_type") not in ("academic", "government", "professional", "education", "guide"):
            errors.append(f"{sid}: invalid source_type")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(record.get("accessed_on", ""))):
            errors.append(f"{sid}: invalid access date")
        for field, values in seen.items():
            value = record.get(field)
            if isinstance(value, str):
                key = value.casefold() if field == "doi" else value
                if key in values:
                    errors.append(f"{sid}: duplicate {field} {value}")
                values.add(key)
        raw_path = record.get("raw_path")
        if not isinstance(raw_path, str):
            errors.append(f"{sid}: missing raw_path")
            continue
        path = (ROOT / raw_path).resolve()
        if not raw_path.startswith("raw/") or raw_root not in path.parents or not path.is_file():
            errors.append(f"{sid}: raw_path unavailable or outside raw/")
        elif sid not in path.read_text(encoding="utf-8") or SOURCE_URLS[sid] not in path.read_text(encoding="utf-8"):
            errors.append(f"{sid}: raw file lacks its source ID or URL")
    return sources


def check_article(path, sources, errors):
    text = path.read_text(encoding="utf-8")
    front = re.match(r"\A---\n(.+?)\n---\n", text, re.S)
    if not front:
        errors.append(f"{path.name}: missing front matter")
        return None
    fields = dict(line.split(": ", 1) for line in front[1].splitlines() if ": " in line)
    aid, category, state = (fields.get(key, "") for key in ("article_id", "category", "status"))
    if not ARTICLE_ID.fullmatch(aid) or not path.name.startswith(aid + "-"):
        errors.append(f"{path.name}: invalid article ID or filename")
    if category not in CATEGORIES or state not in STATES:
        errors.append(f"{path.name}: invalid category or status")

    body = text[front.end():].strip()
    title_match = re.search(r"^# (\S.*)$", body, re.M)
    if not title_match:
        errors.append(f"{path.name}: missing title")
    title = title_match[1] if title_match else ""
    for label in ("摘要", "關鍵字"):
        if not re.search(rf"^\*\*{label}：\*\*\s+\S", body, re.M):
            errors.append(f"{path.name}: missing {label}")
    for heading in ("正文", "研究限制與不確定性", "來源"):
        if not re.search(rf"^## {heading}\s*$", body, re.M):
            errors.append(f"{path.name}: missing section {heading}")

    declaration = re.fullmatch(r"\[(SRC-\d{3}(?:,\s*SRC-\d{3})*)\]", fields.get("source_ids", ""))
    declared = set()
    if declaration:
        entries = re.findall(r"SRC-\d{3}", declaration[1])
        declared = set(entries)
        if len(entries) != len(declared):
            errors.append(f"{path.name}: duplicate declared source ID")
    else:
        errors.append(f"{path.name}: invalid source_ids")

    content, _, bibliography = body.partition("\n## 來源\n")
    cited = set(CITATION.findall(content))
    refs = {}
    for line in bibliography.strip().splitlines():
        entry = re.fullmatch(r"- \[(SRC-\d{3})\]\s+(.+)", line)
        if not entry or entry[1] in refs:
            errors.append(f"{path.name}: invalid or repeated bibliography entry")
            continue
        refs[entry[1]] = entry[2]
    if not cited or cited != declared or refs.keys() != declared:
        errors.append(f"{path.name}: declared, inline and bibliography source IDs differ")
    for sid in cited | declared | refs.keys():
        source = sources.get(sid)
        if source is None:
            errors.append(f"{path.name}: unknown source {sid}")
            continue
        if state == "approved" and source.get("status") != "approved":
            errors.append(f"{path.name}: approved article cites unapproved source {sid}")
        if sid in refs and f"({SOURCE_URLS[sid]})" not in refs[sid]:
            errors.append(f"{path.name}: bibliography is missing the designated URL for {sid}")

    for block in re.split(r"\n\s*\n", content.strip()):
        if block.startswith(("#", "**關鍵字：**")):
            continue
        if not CITATION.search(block):
            errors.append(f"{path.name}: paragraph missing citation: {block[:36]}")
    return aid, category, state, title, declared


def check_index(approved, errors):
    path = ROOT / "wiki/index.md"
    if not path.is_file():
        return
    expected_headings = {f"## {number}. {topic}": topic for number, topic in enumerate(TOPICS, 1)}
    seen_topics = set()
    indexed = set()
    category = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            category = expected_headings.get(line)
            if category is None or category in seen_topics:
                errors.append(f"wiki/index.md: unexpected or duplicate heading {line}")
            seen_topics.add(category)
        if line.startswith("- "):
            entry = re.fullmatch(r"- (W\d{3,}) \[([^\]]+)\]\(articles/([^/]+\.md)\)", line)
            if not entry:
                errors.append(f"wiki/index.md: invalid article entry {line}")
                continue
            aid, title, filename = entry.groups()
            if aid in indexed or approved.get(aid) != (category, title, filename):
                errors.append(f"wiki/index.md: duplicate or mismatched entry {aid}")
            indexed.add(aid)
    if seen_topics != CATEGORIES:
        errors.append("wiki/index.md: expected all five category headings")
    if indexed != approved.keys():
        errors.append("wiki/index.md: entries must match approved articles")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="require all eight approved sources and all five topics")
    args = parser.parse_args()
    errors = [f"missing path: {name}" for name in REQUIRED if not (ROOT / name).exists()]
    sources = load_sources(errors)
    approved_sources = {sid for sid, source in sources.items() if source.get("status") == "approved"}
    article_ids = set()
    approved = {}
    referenced = set()
    paths = sorted((ROOT / "wiki/articles").glob("*.md"))
    for path in paths:
        result = check_article(path, sources, errors)
        if result is None:
            continue
        aid, category, state, title, declared = result
        if aid in article_ids:
            errors.append(f"duplicate article ID: {aid}")
        article_ids.add(aid)
        if state == "approved":
            approved[aid] = (category, title, path.name)
            referenced.update(declared)
    check_index(approved, errors)
    if args.strict:
        for label, actual in (("registered", sources.keys()), ("approved", approved_sources), ("cited by approved articles", referenced)):
            missing = SOURCE_URLS.keys() - actual
            if missing:
                errors.append(f"strict: missing {label} sources: {', '.join(sorted(missing))}")
        missing_topics = CATEGORIES - {article[0] for article in approved.values()}
        if missing_topics:
            errors.append(f"strict: missing approved topics: {', '.join(sorted(missing_topics))}")
    print(f"Wiki Lint | mode={'strict' if args.strict else 'scaffold'}")
    print(f"Sources: {len(sources)} | approved sources: {len(approved_sources)} | articles: {len(paths)} | approved articles: {len(approved)}")
    for error in errors:
        print(f"ERROR: {error}")
    print(f"RESULT: {'FAIL' if errors else 'PASS'} ({len(errors)} errors, 0 warnings)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
