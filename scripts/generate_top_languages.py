#!/usr/bin/env python3
"""
Top Languages Card Generator
============================
Fetches language statistics from the public repositories of shahnoor-exe,
aggregates byte counts, and generates a terminal-themed SVG card.

Usage:
    python scripts/generate_top_languages.py

Environment:
    GITHUB_TOKEN  — Optional. GitHub personal access token or GITHUB_TOKEN for
                    higher API rate limits. Never logged or embedded in output.

Output:
    assets/top-languages.svg
"""

import json
import os
import sys
import urllib.request
import urllib.error
from xml.sax.saxutils import escape

# ── Configuration ──────────────────────────────────────────────────────────────

USERNAME = "shahnoor-exe"
OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "top-languages.svg",
)

# ── Color palette ──────────────────────────────────────────────────────────────

COLORS = {
    "bg": "#0D1117",
    "titlebar": "#161B22",
    "frame": "#273449",
    "dot_r": "#FF5F56",
    "dot_y": "#FFBD2E",
    "dot_g": "#27C93F",
    "cyan": "#22D3EE",
    "teal": "#14B8A6",
    "violet": "#8B5CF6",
    "purple": "#A855F7",
    "green": "#22C55E",
    "text": "#E5E7EB",
    "muted": "#94A3B8",
    "dim": "#8B949E",
    "bar_bg": "#161B22",
}

# Standard language colors for aesthetics
LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6",
    "Java": "#B07219",
    "C++": "#F34B7D",
    "C": "#555555",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Dart": "#00B4AB",
    "Jupyter Notebook": "#DA5B0B",
    "Shell": "#89E051",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "C#": "#178600",
}

def get_lang_color(lang: str, fallback_index: int) -> str:
    if lang in LANG_COLORS:
        return LANG_COLORS[lang]
    # Fallback to our theme colors for unknown languages
    theme_colors = [COLORS["cyan"], COLORS["teal"], COLORS["violet"], COLORS["purple"]]
    return theme_colors[fallback_index % len(theme_colors)]

# ── Low-level HTTP helper ──────────────────────────────────────────────────────

def _github_token() -> str:
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    return tok if tok and len(tok) > 10 else ""

def _github_get(url: str):
    """Make an authenticated GET request to the GitHub API."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "top-languages-generator")
    token = _github_token()
    if token and len(token) > 10:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("[warn] Rate limited while accessing GitHub API.", file=sys.stderr)
            return None
        elif e.code == 404:
            print(f"[error] Not found: {url}", file=sys.stderr)
            return None
        else:
            print(f"[error] HTTP {e.code}: {url}", file=sys.stderr)
            return None
    except urllib.error.URLError as e:
        print(f"[error] Network error: {e.reason}", file=sys.stderr)
        return None

# ── API Data Gathering ─────────────────────────────────────────────────────────

def fetch_repositories(username: str) -> list:
    """Fetch all public non-fork repositories for the user."""
    all_repos = []
    page = 1
    per_page = 100

    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page={per_page}&page={page}&type=owner"
        data = _github_get(url)
        
        if data is None:
            return all_repos  # return what we have on failure/rate-limit
            
        if not data:
            break
            
        for repo in data:
            if not repo.get("fork"):
                all_repos.append(repo)
                
        page += 1
        if page > 5:  # Safety limit (500 repos max)
            break
            
    return all_repos

def fetch_language_stats(username: str) -> dict:
    """Aggregate language stats across all repos."""
    repos = fetch_repositories(username)
    if not repos:
        return {}
        
    lang_bytes = {}
    for repo in repos:
        lang_url = repo.get("languages_url")
        if not lang_url:
            continue
            
        data = _github_get(lang_url)
        if data is None:
            continue  # skip this repo on error
            
        for lang, count in data.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + count
            
    return lang_bytes

# ── SVG generation ─────────────────────────────────────────────────────────────

def generate_svg(lang_stats: dict) -> str:
    """Render the SVG card."""
    
    # Check for empty data (API failure or no repos)
    if not lang_stats:
        return _generate_fallback_svg()
        
    # Sort and take top 8
    total_bytes = sum(lang_stats.values())
    sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)[:8]
    
    # SVG setup
    width = 420
    row_height = 25
    header_height = 80
    footer_height = 40
    svg_height = header_height + (len(sorted_langs) * row_height) + footer_height
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {svg_height}" width="{width}" height="{svg_height}">
  <defs>
    <style>
      .bg {{ fill: {COLORS["bg"]}; }}
      .frame {{ fill: none; stroke: {COLORS["frame"]}; stroke-width: 1.5; rx: 12; }}
      .titlebar {{ fill: {COLORS["titlebar"]}; }}
      .dot-r {{ fill: {COLORS["dot_r"]}; }}
      .dot-y {{ fill: {COLORS["dot_y"]}; }}
      .dot-g {{ fill: {COLORS["dot_g"]}; }}
      .title {{ fill: {COLORS["dim"]}; font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
      .prompt {{ fill: {COLORS["cyan"]}; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: bold; }}
      .cmd {{ fill: {COLORS["text"]}; font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
      .lang-name {{ fill: {COLORS["text"]}; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: bold; }}
      .lang-pct {{ fill: {COLORS["muted"]}; font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
      .bar-bg {{ fill: {COLORS["bar_bg"]}; rx: 4; }}
      .divider {{ stroke: {COLORS["frame"]}; stroke-width: 0.5; }}
      .info-text {{ fill: {COLORS["dim"]}; font-family: 'JetBrains Mono', monospace; font-size: 9px; text-anchor: middle; }}
    </style>
  </defs>

  <!-- Background -->
  <rect class="bg" width="{width}" height="{svg_height}" rx="12"/>
  <rect class="frame" x="0.75" y="0.75" width="{width-1.5}" height="{svg_height-1.5}" rx="12"/>

  <!-- Title Bar -->
  <rect class="titlebar" x="1" y="1" width="{width-2}" height="36" rx="12"/>
  <rect class="titlebar" x="1" y="25" width="{width-2}" height="12"/>
  <circle class="dot-r" cx="20" cy="19" r="6"/>
  <circle class="dot-y" cx="38" cy="19" r="6"/>
  <circle class="dot-g" cx="56" cy="19" r="6"/>
  <text class="title" x="{width/2}" y="23" text-anchor="middle">Top Languages by Repository Usage</text>

  <!-- Command prompt -->
  <text class="prompt" x="20" y="60">$</text>
  <text class="cmd" x="32" y="60">analyze_repos --user={escape(USERNAME)}</text>
  
  <line class="divider" x1="20" y1="72" x2="{width-20}" y2="72"/>
'''

    # Generate bars
    y_offset = header_height
    for idx, (lang, bytes_count) in enumerate(sorted_langs):
        pct = (bytes_count / total_bytes) * 100
        color = get_lang_color(lang, idx)
        
        # Max bar width is 180px
        bar_width = max(2, (pct / 100) * 180)
        
        svg += f'''
  <g transform="translate(20, {y_offset})">
    <circle cx="6" cy="10" r="4" fill="{color}"/>
    <text class="lang-name" x="18" y="14">{escape(lang)}</text>
    <rect class="bar-bg" x="150" y="5" width="180" height="8"/>
    <rect x="150" y="5" width="{bar_width}" height="8" fill="{color}" rx="4"/>
    <text class="lang-pct" x="340" y="14">{pct:.1f}%</text>
  </g>'''
        y_offset += row_height

    svg += f'''
  <!-- Footer -->
  <line class="divider" x1="20" y1="{svg_height - 30}" x2="{width-20}" y2="{svg_height - 30}"/>
  <text class="info-text" x="{width/2}" y="{svg_height - 12}">Data reflects bytes of code in public repositories.</text>
</svg>'''

    return svg

def _generate_fallback_svg() -> str:
    """Generate a fallback card if API fails."""
    width = 420
    svg_height = 120
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {svg_height}" width="{width}" height="{svg_height}">
  <defs>
    <style>
      .bg {{ fill: {COLORS["bg"]}; }}
      .frame {{ fill: none; stroke: {COLORS["frame"]}; stroke-width: 1.5; rx: 12; }}
      .titlebar {{ fill: {COLORS["titlebar"]}; }}
      .dot-r {{ fill: {COLORS["dot_r"]}; }}
      .dot-y {{ fill: {COLORS["dot_y"]}; }}
      .dot-g {{ fill: {COLORS["dot_g"]}; }}
      .title {{ fill: {COLORS["dim"]}; font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
      .prompt {{ fill: {COLORS["cyan"]}; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: bold; }}
      .cmd {{ fill: {COLORS["text"]}; font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
      .error-text {{ fill: {COLORS["dot_y"]}; font-family: 'JetBrains Mono', monospace; font-size: 12px; }}
    </style>
  </defs>

  <!-- Background -->
  <rect class="bg" width="{width}" height="{svg_height}" rx="12"/>
  <rect class="frame" x="0.75" y="0.75" width="{width-1.5}" height="{svg_height-1.5}" rx="12"/>

  <!-- Title Bar -->
  <rect class="titlebar" x="1" y="1" width="{width-2}" height="36" rx="12"/>
  <rect class="titlebar" x="1" y="25" width="{width-2}" height="12"/>
  <circle class="dot-r" cx="20" cy="19" r="6"/>
  <circle class="dot-y" cx="38" cy="19" r="6"/>
  <circle class="dot-g" cx="56" cy="19" r="6"/>
  <text class="title" x="{width/2}" y="23" text-anchor="middle">Top Languages by Repository Usage</text>

  <!-- Command prompt -->
  <text class="prompt" x="20" y="60">$</text>
  <text class="cmd" x="32" y="60">analyze_repos --user={escape(USERNAME)}</text>
  
  <text class="error-text" x="20" y="90">[!] Language analytics temporarily unavailable.</text>
</svg>'''


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"[info] Fetching language statistics for {USERNAME}...")
    lang_stats = fetch_language_stats(USERNAME)
    
    if not lang_stats:
        print("[warn] No language data found or API failed. Generating fallback card.")
    else:
        print(f"[info] Successfully gathered data for {len(lang_stats)} languages.")
        
    svg_content = generate_svg(lang_stats)

    # Check if output changed (deterministic output avoids unnecessary commits)
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            existing = f.read()
        if existing == svg_content:
            print("[info] No changes detected. Skipping write.")
            return

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg_content)

    print(f"[info] SVG written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
