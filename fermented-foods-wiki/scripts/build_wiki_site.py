#!/usr/bin/env python3
"""Render approved Wiki articles for GitHub Pages using the project Markdown template."""

import argparse
import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from lint_wiki import CATEGORIES, ROOT

TOPICS = {
    "principles": "發酵的基本原理",
    "foods": "常見發酵食品介紹",
    "health": "發酵食品與健康",
    "homemade": "自製發酵食品",
    "safety": "食品安全與保存",
}
OUTPUT = ROOT / "docs/index.html"
INLINE = re.compile(
    r"\[([^\]\n]+)\]\(([^\s)]+)\)|\[(S\d{3,})\]|\*\*([^*\n]+)\*\*|\*([^*\n]+)\*"
)
REFERENCE = re.compile(r"\[(S\d{3,})\] (.+)")


@dataclass
class Article:
    article_id: str
    category: str
    title: str
    body: str
    references: dict


def load_articles():
    sources = {
        source["source_id"]: source
        for source in json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    }
    articles = []
    for path in sorted((ROOT / "wiki/articles").glob("*.md")):
        metadata, body = path.read_text(encoding="utf-8")[4:].split("\n---\n", 1)
        fields = dict(line.split(": ", 1) for line in metadata.splitlines())
        if fields["status"] != "approved":
            continue

        title, main = body.strip().split("\n", 1)
        source_heading = "\n## 來源\n"
        content, bibliography = main.split(source_heading, 1)
        references = {}
        for line in bibliography.strip().splitlines():
            citation = REFERENCE.fullmatch(line.removeprefix("- "))
            if not line.startswith("- ") or not citation:
                raise ValueError(f"{path.name}: invalid bibliography entry: {line}")
            source_id, reference = citation.groups()
            source = sources[source_id]
            urls = {match[1] for match in INLINE.findall(reference) if match[1]}
            if source_id in references or source["status"] != "approved" or source["url"] not in urls:
                raise ValueError(f"{path.name}: invalid reference {source_id}")
            references[source_id] = reference
        declared = set(re.findall(r"S\d{3,}", fields["source_ids"]))
        if declared != references.keys():
            raise ValueError(f"{path.name}: bibliography differs from source_ids")
        articles.append(Article(fields["article_id"], fields["category"], title.removeprefix("# "), content, references))
    return sorted(articles, key=lambda article: article.article_id)


def render_inline(text, article):
    pieces = []
    cursor = 0
    for match in INLINE.finditer(text):
        pieces.append(escape(text[cursor:match.start()]))
        label, url, citation, strong, emphasis = match.groups()
        if url:
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError(f"{article.article_id}: expected a public source link: {url}")
            pieces.append(f'<a href="{escape(url)}">{escape(label)}</a>')
        elif citation:
            if citation not in article.references:
                raise ValueError(f"{article.article_id}: missing reference {citation}")
            pieces.append(
                f'<a class="citation" href="#{article.article_id}-{citation}">[{citation}]</a>'
            )
        elif strong:
            pieces.append(f"<strong>{escape(strong)}</strong>")
        else:
            pieces.append(f"<em>{escape(emphasis)}</em>")
        cursor = match.end()
    pieces.append(escape(text[cursor:]))
    return "".join(pieces)


def render_body(article):
    blocks = []
    for paragraph in re.split(r"\n\s*\n", article.body.strip()):
        if paragraph.startswith("## "):
            blocks.append(f"<h4>{render_inline(paragraph[3:], article)}</h4>")
        elif paragraph.startswith("### "):
            blocks.append(f"<h5>{render_inline(paragraph[4:], article)}</h5>")
        else:
            text = " ".join(line.strip() for line in paragraph.splitlines())
            blocks.append(f"<p>{render_inline(text, article)}</p>")
    return "\n".join(blocks)


def render_article(article):
    references = "\n".join(
        f'<li id="{article.article_id}-{source_id}">'
        f'<span class="source-id">[{source_id}]</span> {render_inline(reference, article)}</li>'
        for source_id, reference in article.references.items()
    )
    return f"""<article id="{article.article_id}" aria-labelledby="title-{article.article_id}">
<header>
<p class="article-id">{article.article_id}</p>
<h3 id="title-{article.article_id}">{escape(article.title)}</h3>
</header>
{render_body(article)}
<h4>來源</h4>
<ul class="references">
{references}
</ul>
<p class="directory-link"><a href="#directory">回文章目錄</a></p>
</article>"""


def render_page(articles):
    if set(TOPICS.values()) != CATEGORIES:
        raise ValueError("Site topics differ from Wiki lint categories")
    nav = []
    directory = []
    sections = []
    for slug, category in TOPICS.items():
        entries = [article for article in articles if article.category == category]
        nav.append(f'<li><a href="#{slug}">{category}</a></li>')
        listing = "\n".join(
            f'<li><a href="#{article.article_id}">{escape(article.title)}</a></li>'
            for article in entries
        )
        directory.append(
            f'<div class="directory-item"><h3><a href="#{slug}">{category}</a></h3>'
            + (f"<ul>{listing}</ul>" if listing else "<p>待新增</p>")
            + "</div>"
        )
        entries_html = "\n".join(render_article(article) for article in entries)
        sections.append(f"""<section class="topic" id="{slug}" aria-labelledby="topic-{slug}">
<h2 id="topic-{slug}">{category}</h2>
{entries_html or '<p>待新增</p>'}
</section>""")

    nav_html = "\n".join(nav)
    directory_html = "\n".join(directory)
    sections_html = "\n".join(sections)
    return f"""<!doctype html>
<!-- Generated by scripts/build_wiki_site.py from wiki/articles/. -->
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="閱讀五大發酵食品主題的繁體中文 Wiki 條目與原始文獻。">
<title>發酵食物科學百科</title>
<link rel="stylesheet" href="./styles.css">
</head>
<body>
<a class="skip-link" href="#main">跳至主要內容</a>
<div class="layout">
<aside class="sidebar">
<a class="wordmark" href="#top">發酵食物<br>科學百科</a>
<nav aria-label="主題分類">
<ul>
{nav_html}
</ul>
</nav>
</aside>
<main id="main">
<header class="hero" id="top">
<h1>發酵食物<br>科學百科</h1>
<p>Fermented Foods Science Wiki</p>
</header>
<section class="directory" id="directory" aria-labelledby="directory-title">
<h2 id="directory-title">文章目錄</h2>
<div class="directory-grid">
{directory_html}
</div>
</section>
{sections_html}
</main>
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the generated page is up to date")
    args = parser.parse_args()
    articles = load_articles()
    page = render_page(articles)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != page:
            parser.exit(1, "docs/index.html is stale. Run python3 scripts/build_wiki_site.py.\n")
        print(f"PASS: docs/index.html matches {len(articles)} approved Markdown articles.")
        return
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Built docs/index.html with {len(articles)} approved Markdown articles.")


if __name__ == "__main__":
    main()
