#!/usr/bin/env python3
"""
GitHub Analytics Generator
==========================
Generates self-hosted SVGs for GitHub profile stats to replace fragile remote endpoints.
Outputs:
  1. assets/github-stats.svg      (Total Contributions, Stars, Commits)
  2. assets/github-streak.svg     (Current Streak, Longest Streak, Total Days)
  3. assets/top-languages.svg     (Top 8 languages by bytes across public repos)
  
Usage:
    python scripts/generate_github_analytics.py
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

# ── Configuration ──────────────────────────────────────────────────────────────

USERNAME = "shahnoor-exe"
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

OUT_STATS = os.path.join(ASSETS_DIR, "github-stats.svg")
OUT_STREAK = os.path.join(ASSETS_DIR, "github-streak.svg")
OUT_LANGS = os.path.join(ASSETS_DIR, "top-languages.svg")

COLORS = {
    "bg": "#0D1117",
    "frame": "#273449",
    "titlebar": "#161B22",
    "dot_r": "#FF5F56",
    "dot_y": "#FFBD2E",
    "dot_g": "#27C93F",
    "cyan": "#22D3EE",
    "violet": "#8B5CF6",
    "teal": "#14B8A6",
    "muted": "#94A3B8",
    "text": "#E5E7EB",
    "flame": "#F59E0B"
}

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#F1E05A", "TypeScript": "#3178C6",
    "Java": "#B07219", "C++": "#F34B7D", "C": "#555555", "HTML": "#E34C26",
    "CSS": "#563D7C", "Dart": "#00B4AB"
}

# ── API Helpers ────────────────────────────────────────────────────────────────

def _github_token() -> str:
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    return tok if tok and len(tok) > 10 else ""

def _graphql_query(query: str, variables: dict = None) -> dict:
    """Make an authenticated GraphQL request."""
    url = "https://api.github.com/graphql"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "github-analytics-generator")
    
    token = _github_token()
    if not token:
        print("[warn] GITHUB_TOKEN not set. GraphQL API requires authentication.", file=sys.stderr)
        return None
        
    req.add_header("Authorization", f"Bearer {token}")
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
        
    try:
        with urllib.request.urlopen(req, data=json.dumps(payload).encode("utf-8"), timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[error] GraphQL Error: {e}", file=sys.stderr)
        return None

def _rest_get(endpoint: str) -> dict:
    url = f"https://api.github.com{endpoint}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "github-analytics-generator")
    
    token = _github_token()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
        
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[error] REST Error ({endpoint}): {e}", file=sys.stderr)
        return None

# ── Data Fetching ──────────────────────────────────────────────────────────────

def fetch_stats() -> dict:
    """Fetch total contributions, stars earned, and total commits."""
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            stargazerCount
          }
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
          totalCommitContributions
        }
      }
    }
    """
    data = _graphql_query(query, {"login": USERNAME})
    if not data or "errors" in data:
        return None
        
    user = data.get("data", {}).get("user", {})
    if not user:
        return None
        
    stars = sum(repo["stargazerCount"] for repo in user["repositories"]["nodes"])
    contribs = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    commits = user["contributionsCollection"]["totalCommitContributions"]
    
    return {"stars": stars, "contributions": contribs, "commits": commits}

def fetch_streak() -> dict:
    """Fetch contribution streak data."""
    # To get accurate streak data, we need 1 year of contribution calendar.
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    data = _graphql_query(query, {"login": USERNAME})
    if not data or "errors" in data:
        return None
        
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total = calendar["totalContributions"]
    
    days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append(day)
            
    # Calculate streaks
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    today = datetime.now().date()
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()
    
    # Check if we contributed today or yesterday to keep current streak alive
    has_active_streak = False
    
    # Reverse iterate to count current streak easily
    for day in reversed(days):
        if day["date"] > today_str:
            continue
            
        if day["contributionCount"] > 0:
            temp_streak += 1
            if day["date"] == today_str or day["date"] == yesterday_str:
                has_active_streak = True
        else:
            if temp_streak > 0:
                longest_streak = max(longest_streak, temp_streak)
                if has_active_streak and current_streak == 0:
                    current_streak = temp_streak
            temp_streak = 0
            
    # Final check if the longest streak was running until the end
    longest_streak = max(longest_streak, temp_streak)
    if has_active_streak and current_streak == 0:
        current_streak = temp_streak
        
    return {
        "total": total,
        "current": current_streak,
        "longest": longest_streak
    }

def fetch_languages() -> dict:
    """Fetch language byte counts across repos."""
    # REST is usually easier for languages than paginating GraphQL blobs
    repos = _rest_get(f"/users/{USERNAME}/repos?per_page=100&type=owner")
    if not repos:
        return None
        
    lang_bytes = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        lang_url = repo.get("languages_url")
        if not lang_url:
            continue
            
        # Strip domain for helper
        endpoint = lang_url.replace("https://api.github.com", "")
        repo_langs = _rest_get(endpoint)
        if not repo_langs:
            continue
            
        for lang, count in repo_langs.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + count
            
    return lang_bytes

# ── SVG Generators ─────────────────────────────────────────────────────────────

def _card_wrapper(title: str, content: str, width: int = 420, height: int = 160) -> str:
    """Wraps content in our standard terminal window SVG."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <style>
      .bg {{ fill: {COLORS["bg"]}; }}
      .frame {{ fill: none; stroke: {COLORS["frame"]}; stroke-width: 1.5; rx: 12; }}
      .titlebar {{ fill: {COLORS["titlebar"]}; }}
      .dot-r {{ fill: {COLORS["dot_r"]}; }}
      .dot-y {{ fill: {COLORS["dot_y"]}; }}
      .dot-g {{ fill: {COLORS["dot_g"]}; }}
      .title {{ fill: {COLORS["muted"]}; font-family: 'JetBrains Mono', monospace; font-size: 11px; text-anchor: middle; }}
      .metric-value {{ fill: {COLORS["cyan"]}; font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: bold; text-anchor: middle; }}
      .metric-label {{ fill: {COLORS["muted"]}; font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; text-anchor: middle; }}
      .divider {{ stroke: {COLORS["frame"]}; stroke-width: 1; }}
    </style>
  </defs>
  <rect class="bg" width="{width}" height="{height}" rx="12"/>
  <rect class="frame" x="0.75" y="0.75" width="{width-1.5}" height="{height-1.5}" rx="12"/>
  <rect class="titlebar" x="1" y="1" width="{width-2}" height="36" rx="12"/>
  <rect class="titlebar" x="1" y="25" width="{width-2}" height="12"/>
  <circle class="dot-r" cx="20" cy="19" r="6"/>
  <circle class="dot-y" cx="38" cy="19" r="6"/>
  <circle class="dot-g" cx="56" cy="19" r="6"/>
  <text class="title" x="{width/2}" y="23">{escape(title)}</text>
  <g transform="translate(0, 40)">
{content}
  </g>
</svg>'''

def generate_stats_svg(stats: dict) -> str:
    if not stats:
        return _card_wrapper("github-stats", '    <text class="metric-label" x="210" y="60" fill="#FFBD2E">Stats analytics temporarily unavailable</text>')
        
    content = f'''
    <text class="metric-value" x="70" y="50">{stats["contributions"]}</text>
    <text class="metric-label" x="70" y="75">Contributions</text>
    
    <line class="divider" x1="140" y1="20" x2="140" y2="80"/>
    
    <text class="metric-value" x="210" y="50" fill="{COLORS["violet"]}">{stats["stars"]}</text>
    <text class="metric-label" x="210" y="75">Total Stars</text>
    
    <line class="divider" x1="280" y1="20" x2="280" y2="80"/>
    
    <text class="metric-value" x="350" y="50" fill="{COLORS["teal"]}">{stats["commits"]}</text>
    <text class="metric-label" x="350" y="75">Total Commits</text>
'''
    return _card_wrapper(f"{USERNAME}'s GitHub Stats", content, height=140)

def generate_streak_svg(streak: dict) -> str:
    if not streak:
        return _card_wrapper("github-streak", '    <text class="metric-label" x="210" y="60" fill="#FFBD2E">Streak analytics temporarily unavailable</text>')
        
    content = f'''
    <!-- Total -->
    <text class="metric-value" x="70" y="55">{streak["total"]}</text>
    <text class="metric-label" x="70" y="80">Total Days</text>
    
    <line class="divider" x1="140" y1="20" x2="140" y2="90"/>
    
    <!-- Current Streak Ring -->
    <circle cx="210" cy="45" r="30" fill="none" stroke="{COLORS["frame"]}" stroke-width="4"/>
    <circle cx="210" cy="45" r="30" fill="none" stroke="{COLORS["violet"]}" stroke-width="4" stroke-dasharray="140" stroke-dashoffset="40"/>
    
    <!-- Flame Icon -->
    <path d="M210 15C210 15 207 19 207 22C207 23.5 208.5 25 210 25C211.5 25 213 23.5 213 22C213 19 210 15 210 15Z" fill="{COLORS["flame"]}"/>
    
    <text class="metric-value" x="210" y="55">{streak["current"]}</text>
    <text class="metric-label" x="210" y="100" fill="{COLORS["cyan"]}">Current Streak</text>
    
    <line class="divider" x1="280" y1="20" x2="280" y2="90"/>
    
    <!-- Longest -->
    <text class="metric-value" x="350" y="55" fill="{COLORS["muted"]}">{streak["longest"]}</text>
    <text class="metric-label" x="350" y="80">Longest Streak</text>
'''
    return _card_wrapper(f"{USERNAME}'s Contribution Streak", content, height=160)

def generate_langs_svg(langs: dict) -> str:
    if not langs:
        return _card_wrapper("top-languages", '    <text class="metric-label" x="210" y="60" fill="#FFBD2E">Language analytics temporarily unavailable</text>')
        
    total_bytes = sum(langs.values())
    sorted_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:6]
    
    content = '<style>.lang-name { fill: #E5E7EB; font-family: monospace; font-size: 11px; font-weight: bold;} .lang-pct { fill: #94A3B8; font-family: monospace; font-size: 11px; }</style>'
    
    y_offset = 20
    for idx, (lang, b) in enumerate(sorted_langs):
        pct = (b / total_bytes) * 100
        color = LANG_COLORS.get(lang, COLORS["cyan"])
        bar_width = max(2, (pct / 100) * 180)
        
        content += f'''
    <g transform="translate(20, {y_offset})">
      <circle cx="6" cy="-4" r="4" fill="{color}"/>
      <text class="lang-name" x="18" y="0">{escape(lang)}</text>
      <rect fill="#161B22" x="140" y="-8" width="180" height="8" rx="4"/>
      <rect fill="{color}" x="140" y="-8" width="{bar_width}" height="8" rx="4"/>
      <text class="lang-pct" x="330" y="0">{pct:.1f}%</text>
    </g>'''
        y_offset += 22

    height = 40 + (len(sorted_langs) * 22) + 20
    return _card_wrapper("Top Languages by Repository Usage", content, height=height)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    print("[info] Fetching GitHub Stats...")
    stats = fetch_stats()
    if stats:
        print(f"       -> {stats['contributions']} contribs, {stats['stars']} stars, {stats['commits']} commits")
    else:
        print("       -> [!] API Failed. Using fallback SVG.")
    with open(OUT_STATS, "w", encoding="utf-8") as f: 
        f.write(generate_stats_svg(stats))
    
    print("[info] Fetching GitHub Streak...")
    streak = fetch_streak()
    if streak:
        print(f"       -> Current: {streak['current']}, Longest: {streak['longest']}, Total: {streak['total']}")
    else:
        print("       -> [!] API Failed. Using fallback SVG.")
    with open(OUT_STREAK, "w", encoding="utf-8") as f: 
        f.write(generate_streak_svg(streak))
        
    print("[info] Fetching Top Languages...")
    langs = fetch_languages()
    if langs:
        print(f"       -> Found {len(langs)} languages.")
    else:
        print("       -> [!] API Failed. Using fallback SVG.")
    with open(OUT_LANGS, "w", encoding="utf-8") as f: 
        f.write(generate_langs_svg(langs))
        
    print("[success] Analytics SVGs generated successfully.")

if __name__ == "__main__":
    main()
