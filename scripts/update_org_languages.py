#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path


ORG_NAME = os.environ.get("ORG_NAME", "nzhussup-studio")
README_PATH = Path(os.environ.get("README_PATH", "README.md"))
START_MARKER = "<!-- active-languages:start -->"
END_MARKER = "<!-- active-languages:end -->"
EXCLUDED_REPOS = {
    repo.strip()
    for repo in os.environ.get("EXCLUDED_REPOS", "").split(",")
    if repo.strip()
}
REPO_TYPE = os.environ.get("REPO_TYPE", "all")
MAX_LANGUAGES = int(os.environ.get("MAX_LANGUAGES", "8"))
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

LANGUAGE_COLORS = {
    "Go": "00ADD8",
    "Java": "ED8B00",
    "JavaScript": "F7DF1E",
    "TypeScript": "3178C6",
    "Python": "FFD43B",
    "SQL": "4169E1",
    "Vue": "4FC08D",
    "Vue.js": "4FC08D",
    "Shell": "89E051",
    "Dockerfile": "2496ED",
    "HTML": "E34F26",
    "CSS": "1572B6",
    "Kotlin": "7F52FF",
    "R": "276DC3",
}

LANGUAGE_LOGOS = {
    "Go": "go",
    "Java": "openjdk",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Python": "python",
    "SQL": "postgresql",
    "Vue": "vuedotjs",
    "Vue.js": "vuedotjs",
    "Shell": "gnubash",
    "Dockerfile": "docker",
    "HTML": "html5",
    "CSS": "css3",
    "Kotlin": "kotlin",
    "R": "r",
}


def github_get(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nzhussup-profile-readme-updater",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, context=build_ssl_context()) as response:
        return json.load(response)


def build_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return context


def fetch_org_repos() -> list[dict]:
    repos: list[dict] = []
    page = 1
    per_page = 100

    while True:
        query = urllib.parse.urlencode(
            {
                "type": REPO_TYPE,
                "sort": "updated",
                "per_page": per_page,
                "page": page,
            }
        )
        url = f"https://api.github.com/orgs/{ORG_NAME}/repos?{query}"
        batch = github_get(url)
        if not isinstance(batch, list):
            raise RuntimeError(f"Unexpected repo response: {batch!r}")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < per_page:
            break
        page += 1

    return repos


def fetch_repo_languages(owner: str, repo: str) -> dict[str, int]:
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    data = github_get(url)
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected language response for {owner}/{repo}: {data!r}")
    return {str(name): int(count) for name, count in data.items()}


def build_badge(language: str, percent: float) -> str:
    label = urllib.parse.quote(language)
    message = urllib.parse.quote(f"{percent:.1f}%")
    color = LANGUAGE_COLORS.get(language, "59A5FF")
    logo = LANGUAGE_LOGOS.get(language, "")
    logo_part = f"&logo={urllib.parse.quote(logo)}" if logo else ""
    return (
        f'<img src="https://img.shields.io/badge/{label}-{message}-0F172A'
        f'?style=for-the-badge{logo_part}&logoColor={color}" alt="{language} {percent:.1f}%" />'
    )


def render_language_section(repos: list[dict], language_totals: dict[str, int]) -> str:
    total_bytes = sum(language_totals.values())
    if total_bytes == 0:
        return (
            f"{START_MARKER}\n"
            "<p>No public language data found for the organization right now.</p>\n"
            f"{END_MARKER}"
        )

    repo_count = len(repos)
    sorted_languages = sorted(language_totals.items(), key=lambda item: item[1], reverse=True)
    visible = sorted_languages[:MAX_LANGUAGES]

    badges = "\n".join(
        f'  {build_badge(language, byte_count / total_bytes * 100)}'
        for language, byte_count in visible
    )

    top_three = ", ".join(language for language, _ in visible[:3])
    return (
        f"{START_MARKER}\n"
        "<p>\n"
        f"{badges}\n"
        "</p>\n\n"
        f"<p>Generated from public repositories in <code>{ORG_NAME}</code> across {repo_count} repos. "
        f"Current leading languages: {top_three}.</p>\n"
        f"{END_MARKER}"
    )


def update_readme(section: str) -> None:
    readme = README_PATH.read_text()
    start = readme.find(START_MARKER)
    end = readme.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise RuntimeError("Active languages markers were not found in README.md")

    end += len(END_MARKER)
    updated = readme[:start] + section + readme[end:]
    README_PATH.write_text(updated)


def main() -> int:
    repos = [
        repo
        for repo in fetch_org_repos()
        if not repo.get("archived")
        and not repo.get("fork")
        and repo.get("name") not in EXCLUDED_REPOS
    ]

    language_totals: dict[str, int] = {}
    for repo in repos:
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        for language, byte_count in fetch_repo_languages(owner, repo_name).items():
            language_totals[language] = language_totals.get(language, 0) + byte_count

    section = render_language_section(repos, language_totals)
    update_readme(section)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
