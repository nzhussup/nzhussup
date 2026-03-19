#!/usr/bin/env python3

from __future__ import annotations

import json
from math import ceil
from pathlib import Path
from datetime import datetime, UTC
import re
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "assets" / "profile-header.config.json"
ASSETS_DIR = ROOT / "assets"
README_PATH = ROOT / "README.md"

RIGHT_X = 760
RIGHT_WIDTH = 456
CARD_GAP = 18
CARD_HEIGHT = 112
CARD_WIDTH = (RIGHT_WIDTH - CARD_GAP) // 2
CARD_BOTTOM = 560
LEFT_MAX_WIDTH = 600

THEME_PRESETS = {
    "light": {
        "bg": "#FBF7F1",
        "bg2": "#F5EFE6",
        "bg3": "#FFF9F1",
        "surface": "#FFFDF9",
        "surface2": "#F2E9DD",
        "surface3": "#F8F1E7",
        "line": "#D7CABC",
        "frame": "#F4EBE1",
        "dot": "#C9BAAA",
        "text": "#1F2937",
        "muted": "#6B7280",
        "accent": "#FF8F6B",
        "accent2": "#5DB7D8",
        "accent3": "#8B7CF7",
        "accent4": "#EAB308",
    },
    "dark": {
        "bg": "#0D1117",
        "bg2": "#161B22",
        "bg3": "#1C2128",
        "surface": "#161B22",
        "surface2": "#21262D",
        "surface3": "#0F141A",
        "line": "#30363D",
        "frame": "#30363D",
        "dot": "#8B949E",
        "text": "#E6EDF3",
        "muted": "#9DA7B3",
        "accent": "#F78166",
        "accent2": "#79C0FF",
        "accent3": "#D2A8FF",
        "accent4": "#E3B341",
    },
}


def estimate_text_width(text: str, font_size: int, factor: float = 0.58) -> int:
    return int(len(text) * font_size * factor)


def wrap_text(text: str, font_size: int, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if estimate_text_width(candidate, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def palette_value(colors: dict[str, str], key: str, fallback: str) -> str:
    return colors.get(key, fallback)


def color_token(colors: dict[str, str], token: str, fallback: str) -> str:
    return colors.get(token, token or fallback)


def resolve_colors(config: dict) -> dict[str, str]:
    theme = str(config.get("theme", "dark")).lower()
    base = dict(THEME_PRESETS.get(theme, THEME_PRESETS["dark"]))
    overrides = config.get("colors", {})
    if isinstance(overrides, dict):
        base.update({str(key): str(value) for key, value in overrides.items()})
    return base


def svg_text(x: int, y: int, text: str, *, fill: str, font_size: int, weight: int, family: str, letter_spacing: float | None = None) -> str:
    spacing = f' letter-spacing="{letter_spacing}"' if letter_spacing is not None else ""
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" '
        f'font-size="{font_size}" font-weight="{weight}"{spacing}>{escape(text)}</text>'
    )


def svg_text_lines(
    x: int,
    y: int,
    lines: list[str],
    *,
    fill: str,
    font_size: int,
    weight: int,
    family: str,
    line_height: int,
) -> str:
    parts = []
    for index, line in enumerate(lines):
        parts.append(
            svg_text(
                x,
                y + index * line_height,
                line,
                fill=fill,
                font_size=font_size,
                weight=weight,
                family=family,
            )
        )
    return "\n  ".join(parts)


def normalize_tag(item: object, index: int, colors: dict[str, str]) -> dict[str, str]:
    accents = [
        palette_value(colors, "accent", "#FF8F6B"),
        palette_value(colors, "accent2", "#5DB7D8"),
        palette_value(colors, "accent3", "#8B7CF7"),
        palette_value(colors, "accent4", "#EAB308"),
    ]
    fills = [
        palette_value(colors, "surface", "#FFFDF9"),
        palette_value(colors, "surface2", "#F2E9DD"),
    ]

    if isinstance(item, str):
        return {
            "text": item,
            "accent": accents[index % len(accents)],
            "fill": fills[index % len(fills)],
        }

    if isinstance(item, dict):
        return {
            "text": str(item.get("text", "")),
            "accent": color_token(colors, str(item.get("accent", "")), accents[index % len(accents)]),
            "fill": color_token(colors, str(item.get("fill", "")), fills[index % len(fills)]),
        }

    return {"text": "", "accent": accents[0], "fill": fills[0]}


def render_tags(tags: list[object], colors: dict[str, str]) -> str:
    x = RIGHT_X
    y = 108
    row_height = 58
    parts: list[str] = []
    for index, raw_item in enumerate(tags):
        item = normalize_tag(raw_item, index, colors)
        text = item["text"].strip()
        if not text:
            continue

        width = max(104, estimate_text_width(text, 15, 0.7) + 52)
        if x + width > RIGHT_X + RIGHT_WIDTH:
            x = RIGHT_X
            y += row_height

        parts.append(
            f"""
  <g transform="translate({x} {y})">
    <rect width="{width}" height="44" rx="22" fill="{item['fill']}" stroke="{colors['line']}"/>
    <circle cx="22" cy="22" r="5" fill="{item['accent']}"/>
    <text x="36" y="27" fill="{colors['text']}" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="700">{escape(text)}</text>
  </g>"""
        )
        x += width + 16
    return "".join(parts)


def normalize_card(item: object, index: int, colors: dict[str, str]) -> dict[str, str]:
    accents = [
        palette_value(colors, "accent", "#FF8F6B"),
        palette_value(colors, "accent2", "#5DB7D8"),
        palette_value(colors, "accent3", "#8B7CF7"),
        palette_value(colors, "accent4", "#EAB308"),
    ]

    if isinstance(item, dict):
        return {
            "title": str(item.get("title", "")),
            "body": str(item.get("body", "")),
            "accent": color_token(colors, str(item.get("accent", "")), accents[index % len(accents)]),
        }

    if isinstance(item, str):
        return {
            "title": f"NOTE {index + 1}",
            "body": item,
            "accent": accents[index % len(accents)],
        }

    return {"title": "", "body": "", "accent": accents[0]}


def render_cards(cards: list[object], colors: dict[str, str]) -> str:
    if not cards:
        return ""

    normalized = [normalize_card(card, index, colors) for index, card in enumerate(cards)]
    normalized = [card for card in normalized if card["title"].strip() or card["body"].strip()]
    if not normalized:
        return ""

    rows = ceil(len(normalized) / 2)
    start_y = CARD_BOTTOM - rows * CARD_HEIGHT - (rows - 1) * CARD_GAP
    parts: list[str] = []

    for index, card in enumerate(normalized):
        col = index % 2
        row = index // 2
        x = RIGHT_X + col * (CARD_WIDTH + CARD_GAP)
        y = start_y + row * (CARD_HEIGHT + CARD_GAP)
        body_lines = wrap_text(card["body"], 22, CARD_WIDTH - 44)[:2]
        if not body_lines:
            body_lines = [""]

        parts.append(
            f"""
  <g transform="translate({x} {y})">
    <rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="28" fill="{colors['surface']}" fill-opacity="0.92" stroke="{colors['line']}"/>
    <rect x="22" y="22" width="10" height="10" rx="5" fill="{card['accent']}"/>
    <text x="46" y="33" fill="{colors['muted']}" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="700" letter-spacing="1.5">{escape(card['title'].upper())}</text>
    {svg_text_lines(22, 76, body_lines, fill=colors['text'], font_size=22, weight=700, family='Segoe UI, Arial, sans-serif', line_height=28)}
  </g>"""
        )
    return "".join(parts)


def render_pill(text: str, colors: dict[str, str]) -> str:
    if not text:
        return ""
    width = max(120, estimate_text_width(text, 15, 0.72) + 40)
    return f"""
  <g transform="translate(92 456)">
    <rect width="{width}" height="42" rx="21" fill="{colors['surface']}" stroke="{colors['line']}"/>
    <text x="20" y="27" fill="{colors['text']}" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="700">{escape(text)}</text>
  </g>"""


def render_left_copy(config: dict, colors: dict[str, str]) -> str:
    eyebrow = str(config.get("eyebrow", "")).strip()
    headline_lines = [str(line) for line in config.get("headline_lines", []) if str(line).strip()]
    if not headline_lines:
        headline_lines = [str(config.get("name", ""))]

    headline_font = 84 if len(headline_lines) <= 2 else 68
    headline_line_height = headline_font + 4
    headline_start_y = 224
    headline_block = svg_text_lines(
        92,
        headline_start_y,
        headline_lines,
        fill=colors["text"],
        font_size=headline_font,
        weight=800,
        family="Arial, Helvetica, sans-serif",
        line_height=headline_line_height,
    )

    subline_value = config.get("subline", "")
    if isinstance(subline_value, list):
        subline_lines = [str(line) for line in subline_value if str(line).strip()]
    else:
        subline_lines = wrap_text(str(subline_value), 26, LEFT_MAX_WIDTH)
    subline_start_y = headline_start_y + (len(headline_lines) - 1) * headline_line_height + 66
    subline_block = svg_text_lines(
        92,
        subline_start_y,
        subline_lines[:3],
        fill=colors["muted"],
        font_size=26,
        weight=500,
        family="Segoe UI, Arial, sans-serif",
        line_height=34,
    )

    divider_y = subline_start_y + max(1, len(subline_lines[:3])) * 34 + 12
    pill_block = render_pill(str(config.get("pill", "")).strip(), colors)
    name_text = str(config.get("footer_name") or config.get("name", "")).strip()

    eyebrow_width = max(160, estimate_text_width(eyebrow, 14, 0.8) + 38)
    eyebrow_block = ""
    if eyebrow:
        eyebrow_block = f"""
  <rect x="92" y="94" width="{eyebrow_width}" height="38" rx="19" fill="{colors['surface2']}" stroke="{colors['line']}"/>
  {svg_text(114, 118, eyebrow, fill=colors['muted'], font_size=14, weight=700, family='Segoe UI, Arial, sans-serif', letter_spacing=1.7)}"""

    footer_block = ""
    if name_text:
        footer_block = svg_text(
            92,
            575,
            name_text,
            fill=colors["muted"],
            font_size=18,
            weight=600,
            family="Segoe UI, Arial, sans-serif",
        )

    return f"""{eyebrow_block}
  {headline_block}
  {subline_block}
  <line x1="92" y1="{divider_y}" x2="438" y2="{divider_y}" stroke="{colors['line']}" stroke-width="2"/>
  <circle cx="444" cy="{divider_y}" r="5" fill="{colors['accent']}"/>
  {pill_block}
  {footer_block}"""


def render_art(config: dict, colors: dict[str, str]) -> str:
    art = config.get("art", {})
    show = True if not isinstance(art, dict) else art.get("enabled", True)
    if not show:
        return ""
    return f"""
  <g>
    <circle cx="950" cy="232" r="126" fill="{colors['accent']}" fill-opacity="0.14"/>
    <circle cx="1032" cy="258" r="82" fill="{colors['accent2']}" fill-opacity="0.18"/>
    <circle cx="1128" cy="210" r="54" fill="{colors['accent3']}" fill-opacity="0.18"/>
    <path d="M852 322C908 278 986 272 1046 304C1105 336 1150 404 1120 466C1090 528 1000 552 920 524C840 496 804 428 824 370C830 352 840 336 852 322Z" fill="{colors['surface']}" fill-opacity="0.88" stroke="{colors['line']}"/>
    <path d="M848 322C902 300 962 302 1016 330" stroke="{colors['line']}" stroke-width="2"/>
    <path d="M874 408C934 372 1014 374 1070 414" stroke="{colors['line']}" stroke-width="2"/>
    <path d="M904 482C966 454 1030 456 1082 488" stroke="{colors['line']}" stroke-width="2"/>
    <circle cx="890" cy="290" r="8" fill="{colors['accent']}"/>
    <circle cx="1088" cy="196" r="8" fill="{colors['accent2']}"/>
    <circle cx="1044" cy="520" r="8" fill="{colors['accent3']}"/>
  </g>"""


def build_svg(config: dict) -> str:
    colors = resolve_colors(config)
    tags = render_tags(list(config.get("tags", [])), colors)
    cards = render_cards(list(config.get("cards", [])), colors)
    left_copy = render_left_copy(config, colors)
    art = render_art(config, colors)
    title = escape(str(config.get("name", "Profile Header")))

    return f"""<svg width="1280" height="640" viewBox="0 0 1280 640" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">{title} profile header</title>
  <desc id="desc">Configurable GitHub profile banner with a modern minimal editorial design.</desc>
  <defs>
    <linearGradient id="bg" x1="88" y1="44" x2="1158" y2="592" gradientUnits="userSpaceOnUse">
      <stop stop-color="{colors['bg']}"/>
      <stop offset="0.58" stop-color="{colors['bg2']}"/>
      <stop offset="1" stop-color="{palette_value(colors, 'bg3', '#FFF9F1')}"/>
    </linearGradient>
    <radialGradient id="glowA" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(244 156) rotate(34) scale(278 198)">
      <stop stop-color="{colors['accent']}" stop-opacity="0.18"/>
      <stop offset="1" stop-color="{colors['accent']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowB" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(980 214) rotate(41) scale(248 218)">
      <stop stop-color="{colors['accent2']}" stop-opacity="0.18"/>
      <stop offset="1" stop-color="{colors['accent2']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowC" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(1090 390) rotate(180) scale(200 154)">
      <stop stop-color="{colors['accent3']}" stop-opacity="0.12"/>
      <stop offset="1" stop-color="{colors['accent3']}" stop-opacity="0"/>
    </radialGradient>
    <filter id="blur" x="-120" y="-120" width="1520" height="920" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="48"/>
    </filter>
    <pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1.3" fill="{palette_value(colors, 'dot', '#C9BAAA')}" fill-opacity="0.25"/>
    </pattern>
  </defs>
  <rect width="1280" height="640" rx="36" fill="url(#bg)"/>
  <rect width="1280" height="640" rx="36" fill="url(#dots)"/>
  <g filter="url(#blur)">
    <ellipse cx="240" cy="180" rx="270" ry="190" fill="url(#glowA)"/>
    <ellipse cx="980" cy="214" rx="248" ry="218" fill="url(#glowB)"/>
    <ellipse cx="1090" cy="390" rx="200" ry="154" fill="url(#glowC)"/>
  </g>
  <path d="M82 520C262 384 390 366 574 440" stroke="{colors['line']}" stroke-width="2"/>
  <path d="M742 116C916 112 1032 154 1176 280" stroke="{colors['line']}" stroke-width="2" stroke-dasharray="6 10"/>
  <rect x="44" y="48" width="1192" height="544" rx="30" fill="{palette_value(colors, 'surface3', colors['surface'])}" stroke="{palette_value(colors, 'frame', '#F4EBE1')}"/>
  {art}
  {left_copy}
  {tags}
  {cards}
</svg>
"""


def cleanup_old_headers(keep: Path) -> None:
    for path in ASSETS_DIR.glob("profile-header*.svg"):
        if path != keep:
            path.unlink(missing_ok=True)


def update_readme_header_reference(asset_name: str) -> None:
    readme = README_PATH.read_text()
    updated = re.sub(
        r'(<img\s+src=")(?:https://raw\.githubusercontent\.com/[^"]+|\.?/assets/profile-header[^"]*\.svg(?:\?[^"]*)?)(" alt="Nurzhanat Zhussup banner")',
        rf'\1./assets/{asset_name}\2',
        readme,
        count=1,
    )
    README_PATH.write_text(updated)


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text())
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    output_path = ASSETS_DIR / f"profile-header-{timestamp}.svg"
    output_path.write_text(build_svg(config))
    cleanup_old_headers(output_path)
    update_readme_header_reference(output_path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
