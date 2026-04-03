#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path


README_PATH = Path(os.environ.get("README_PATH", "README.md"))
SKILLS_API_URL = os.environ.get("SKILLS_API_URL", "https://api.nzhussup.dev/v1/base/skill")
SKILL_LOGOS_PATH = Path(
    os.environ.get("SKILL_LOGOS_PATH", "scripts/data/skill_logos.json")
)
FALLBACK_SKILLS_PATH = Path(
    os.environ.get("FALLBACK_SKILLS_PATH", "scripts/data/fallback_skills.json")
)
SKILLS_WORKFLOW_PATH = Path(
    os.environ.get("SKILLS_WORKFLOW_PATH", ".github/workflows/update-readme.yml")
)
SKILLS_UPDATE_CRON = os.environ.get("SKILLS_UPDATE_CRON", "").strip()
START_MARKER = "<!-- skills-badges:start -->"
END_MARKER = "<!-- skills-badges:end -->"
EXCLUDED_CATEGORIES = {"ways of working & soft skills", "languages"}


def normalize_skill_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def compact_skill_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_skill_name(name))


def load_skill_logos() -> tuple[dict[str, tuple[str, str, str]], dict[str, tuple[str, str, str]]]:
    data = json.loads(SKILL_LOGOS_PATH.read_text())
    if not isinstance(data, dict):
        raise RuntimeError("Skill logo mapping must be a JSON object")

    parsed: dict[str, tuple[str, str, str]] = {}
    compact: dict[str, tuple[str, str, str]] = {}
    for skill_key, value in data.items():
        if not isinstance(skill_key, str) or not isinstance(value, dict):
            continue

        label = str(value.get("label", "")).strip()
        logo = str(value.get("logo", "")).strip()
        logo_color = str(value.get("logoColor", "")).strip()
        if not label or not logo_color:
            continue

        aliases = value.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = []

        canonical = (label, logo, logo_color)
        all_keys = [skill_key, *[str(alias) for alias in aliases if str(alias).strip()]]
        for key in all_keys:
            normalized_key = normalize_skill_name(key)
            parsed[normalized_key] = canonical

            compact_key = compact_skill_name(key)
            if compact_key:
                compact[compact_key] = canonical

    if not parsed or not compact:
        raise RuntimeError("Skill logo mapping is empty or invalid")

    return parsed, compact


def load_fallback_skills() -> list[dict]:
    data = json.loads(FALLBACK_SKILLS_PATH.read_text())
    if not isinstance(data, list):
        raise RuntimeError("Fallback skills must be a JSON array")

    validated: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "")).strip()
        skill_names = str(item.get("skillNames", "")).strip()
        if not category or not skill_names:
            continue
        validated.append(item)

    if not validated:
        raise RuntimeError("Fallback skills are empty or invalid")

    return validated


SKILL_LOGOS, SKILL_LOGOS_COMPACT = load_skill_logos()
FALLBACK_SKILLS = load_fallback_skills()


def build_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return context


def fetch_skills() -> list[dict]:
    request = urllib.request.Request(
        SKILLS_API_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "nzhussup-skill-badge-updater",
        },
    )
    with urllib.request.urlopen(request, context=build_ssl_context()) as response:
        data = json.load(response)

    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected skill payload: {type(data).__name__}")

    return data


def split_skill_names(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def skills_api_display() -> str:
    parsed = urllib.parse.urlparse(SKILLS_API_URL)
    return parsed.netloc or SKILLS_API_URL


def resolve_update_cron() -> str:
    if SKILLS_UPDATE_CRON:
        return SKILLS_UPDATE_CRON

    try:
        workflow = SKILLS_WORKFLOW_PATH.read_text()
    except OSError:
        return ""

    match = re.search(r'cron:\s*["\']([^"\']+)["\']', workflow)
    return match.group(1).strip() if match else ""


def build_badge(skill_name: str) -> str:
    normalized = normalize_skill_name(skill_name)
    compact = compact_skill_name(skill_name)
    label, logo, logo_color = SKILL_LOGOS.get(normalized) or SKILL_LOGOS_COMPACT.get(
        compact, (skill_name.strip(), "", "59A5FF")
    )
    badge_label = urllib.parse.quote(label)
    logo_part = f"&logo={urllib.parse.quote(logo)}" if logo else ""
    return (
        f'  <img src="https://img.shields.io/badge/{badge_label}-0F172A'
        f'?style=for-the-badge{logo_part}&logoColor={logo_color}" alt="{label}" />'
    )


def render_skills_section(
    skills: list[dict], *, is_fallback: bool = False, update_cron: str = ""
) -> str:
    ordered = sorted(
        skills,
        key=lambda skill: (
            -int(skill.get("displayOrder", 0)),
            str(skill.get("category", "")),
        ),
    )

    lines: list[str] = [START_MARKER]
    api_display = skills_api_display()
    if update_cron:
        lines.append(
            f"> **Info:** Skill data is fetched from `{api_display}` and "
            f"auto-updated on schedule `{update_cron}` (UTC)."
        )
    else:
        lines.append(
            f"> **Info:** Skill data is fetched from `{api_display}` and "
            "auto-updated by the README workflow schedule."
        )
    lines.append("")

    if is_fallback:
        lines.append(
            "> **Note:** Skill badges are currently rendered from fallback data "
            "because the skills API was unavailable during generation."
        )
        lines.append("")

    for category in ordered:
        category_name = str(category.get("category", "")).strip()
        raw_skill_names = str(category.get("skillNames", "")).strip()
        if not category_name or not raw_skill_names:
            continue
        if category_name.lower() in EXCLUDED_CATEGORIES:
            continue

        skill_names = split_skill_names(raw_skill_names)
        if not skill_names:
            continue

        lines.append(f"### {category_name}")
        lines.append("")
        lines.append("<p>")
        lines.extend(build_badge(skill) for skill in skill_names)
        lines.append("</p>")
        lines.append("")

    lines.append(END_MARKER)
    return "\n".join(lines)


def update_readme(section: str) -> None:
    readme = README_PATH.read_text()
    start = readme.find(START_MARKER)
    end = readme.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise RuntimeError("Skill badge markers were not found in README.md")

    end += len(END_MARKER)
    updated = readme[:start] + section + readme[end:]
    README_PATH.write_text(updated)


def main() -> int:
    using_fallback = False
    update_cron = resolve_update_cron()
    try:
        skills = fetch_skills()
    except Exception as exc:
        print(
            f"warning: failed to fetch skills from {SKILLS_API_URL}: {exc}. "
            "Using fallback skill data.",
            file=sys.stderr,
        )
        skills = FALLBACK_SKILLS
        using_fallback = True

    section = render_skills_section(
        skills, is_fallback=using_fallback, update_cron=update_cron
    )
    update_readme(section)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
