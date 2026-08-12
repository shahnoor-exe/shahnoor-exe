#!/usr/bin/env python3
"""
LeetCode Practice Streak Generator
===================================
Fetches commit history from shahnoor-exe/LeetCode-2026, filters to only
solution-related commits, computes daily practice streaks, and generates
a terminal-themed SVG heatmap card.

The script handles multiple coexisting repo layouts:
  - Root-level problem folders  (e.g. "1 Two Sum/")
  - LeetCode/ or leetcode/ top-level folders
  - Nested language subfolders  (e.g. LeetCode/Java/)
  - Pattern-based folders       (e.g. Patterns/Sliding Window/)

Non-solution directories (.github, assets, docs, screenshots, dist, …)
are excluded.  A commit is counted as a "solution commit" only when it
touches at least one recognised solution file.

Usage:
    python scripts/update_leetcode_streak.py

Environment:
    GITHUB_TOKEN  — Optional. Raises rate-limit from 60 → 5 000 req/h.
                    Never logged or embedded in output.

Output:
    assets/leetcode-streak.svg
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from xml.sax.saxutils import escape

# ── Configuration ──────────────────────────────────────────────────────────────

REPO_OWNER = "shahnoor-exe"
REPO_NAME = "LeetCode-2026"
OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "leetcode-streak.svg",
)
IST = timezone(timedelta(hours=5, minutes=30))  # Asia/Kolkata
PER_PAGE = 100

# Directories to always exclude (case-insensitive comparison)
EXCLUDED_DIRS = frozenset({
    ".github", ".git", ".vscode", ".idea",
    "assets", "docs", "screenshots", "dist",
    "node_modules", "__pycache__", ".mypy_cache",
    "venv", "env", ".env",
})

# File extensions recognised as solution code
SOLUTION_EXTENSIONS = frozenset({
    ".java", ".py", ".cpp", ".c", ".js", ".ts", ".go", ".rs", ".kt",
    ".rb", ".swift", ".sql", ".sh", ".cs", ".scala", ".php", ".pl",
    ".lua", ".r", ".m", ".mm", ".hs", ".ex", ".exs", ".clj", ".dart",
})

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
    "cell_empty": "#161B22",
    "cell_border": "#273449",
    "flame1": "#F59E0B",
    "flame2": "#FBBF24",
}

HEATMAP_COLORS = [
    "#161B22",  # 0 commits (empty)
    "#0E4429",  # 1 commit
    "#14B8A6",  # 2 commits (teal)
    "#8B5CF6",  # 3-4 commits (violet)
    "#A855F7",  # 5+ commits (purple)
]


def get_heatmap_color(count: int) -> str:
    """Map commit count to heatmap color."""
    if count == 0:
        return HEATMAP_COLORS[0]
    elif count == 1:
        return HEATMAP_COLORS[1]
    elif count == 2:
        return HEATMAP_COLORS[2]
    elif count <= 4:
        return HEATMAP_COLORS[3]
    else:
        return HEATMAP_COLORS[4]


# ── Low-level HTTP helper ──────────────────────────────────────────────────────

def _github_token() -> str:
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    return tok if tok and len(tok) > 10 else ""


def _github_get(url: str, *, accept: str = "application/vnd.github.v3+json"):
    """Make an authenticated GET request to the GitHub API.
    Returns (parsed_json, response_headers) or raises on hard errors.
    Returns (None, None) on 403 rate-limit.
    """
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "leetcode-streak-generator")
    token = _github_token()
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data, dict(resp.headers)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return None, None  # rate-limited
        elif e.code == 404:
            print(f"[error] Not found: {url}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"[error] HTTP {e.code}: {url}", file=sys.stderr)
            sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[error] Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ── Repository tree analysis ──────────────────────────────────────────────────

def _is_excluded_path(path: str) -> bool:
    """Return True if *path* falls inside an excluded directory."""
    parts = path.split("/")
    return any(p.lower() in EXCLUDED_DIRS for p in parts)


def _is_solution_file(path: str) -> bool:
    """Return True when *path* looks like a solution source file."""
    if _is_excluded_path(path):
        return False
    _, ext = os.path.splitext(path.lower())
    return ext in SOLUTION_EXTENSIONS


def fetch_solution_paths() -> set:
    """Fetch the full recursive tree and return the set of solution file paths."""
    url = (
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
        f"/git/trees/main?recursive=1"
    )
    data, _ = _github_get(url)
    if data is None:
        print("[warn] Rate-limited fetching repo tree; skipping path filtering.", file=sys.stderr)
        return set()

    tree = data.get("tree", [])
    paths = set()
    for entry in tree:
        if entry.get("type") == "blob" and _is_solution_file(entry["path"]):
            paths.add(entry["path"])

    return paths


def count_unique_problems(solution_paths: set) -> int:
    """Estimate unique problems from the directory structure.

    Heuristic: a directory whose name starts with a digit (like "1 Two Sum")
    is a problem directory.  We also count distinct second-level dirs under
    LeetCode/ or Patterns/.
    """
    problem_dirs: set = set()
    problem_pattern = re.compile(r"^\d+[\s._-]")  # e.g. "1 Two Sum" or "1_Two_Sum"

    for p in solution_paths:
        parts = p.split("/")
        if len(parts) >= 2:
            top = parts[0]
            # Root-level problem folder
            if problem_pattern.match(top):
                problem_dirs.add(top)
            # Nested: LeetCode/Java/SomeFile or Patterns/Sliding Window/...
            elif top.lower() in ("leetcode", "patterns"):
                # Could be LeetCode/<problem>/ or LeetCode/<lang>/<problem>/
                # Use the deepest "problem-like" directory
                for part in parts[1:]:
                    if problem_pattern.match(part):
                        problem_dirs.add(part)
                        break
                else:
                    # No problem-named dir, just count a unique subdirectory
                    if len(parts) >= 3:
                        problem_dirs.add("/".join(parts[:3]))
                    else:
                        problem_dirs.add("/".join(parts[:2]))
            else:
                # Some other top-level dir — still count if pattern matches
                if problem_pattern.match(top):
                    problem_dirs.add(top)
                elif len(parts) >= 2 and problem_pattern.match(parts[1]):
                    problem_dirs.add(parts[1])

    return len(problem_dirs)


# ── Commit fetching ───────────────────────────────────────────────────────────

def fetch_all_commits() -> list:
    """Fetch every commit (paginated) from the default branch."""
    all_commits = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
            f"?per_page={PER_PAGE}&page={page}"
        )
        data, _ = _github_get(url)
        if data is None:
            print(
                f"[warn] Rate-limited at page {page}. "
                f"Using {len(all_commits)} commits collected so far.",
                file=sys.stderr,
            )
            break
        if not data:
            break

        all_commits.extend(data)
        page += 1
        if page > 100:
            print("[warn] Reached 100 pages; stopping pagination.", file=sys.stderr)
            break

    return all_commits


def fetch_commit_files(sha: str) -> list | None:
    """Return the list of file paths touched by a single commit, or None on rate-limit."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{sha}"
    data, _ = _github_get(url)
    if data is None:
        return None
    return [f["filename"] for f in data.get("files", [])]


# ── Solution-aware commit filtering ──────────────────────────────────────────

def classify_commits(commits: list, solution_paths: set) -> list:
    """Return only commits that touch at least one solution file.

    Strategy:
      1. If we have the repo tree, fetch each commit's file list and match
         against solution_paths.
      2. If we hit the rate limit mid-way, switch to a heuristic fallback
         for the remaining commits.

    The heuristic fallback excludes commits whose messages look purely
    administrative (README-only updates, CI config, etc.).
    """
    if not solution_paths:
        # Tree fetch failed — use heuristic for ALL commits
        print("[info] Using heuristic fallback for all commits (no tree data).")
        return _heuristic_filter(commits)

    # Build a set of *directories* that contain solution files
    # so we can also match new files added to existing solution dirs.
    solution_dirs: set = set()
    for p in solution_paths:
        parts = p.split("/")
        for i in range(1, len(parts)):
            solution_dirs.add("/".join(parts[:i]))

    filtered: list = []
    rate_limited = False

    for i, commit in enumerate(commits):
        if rate_limited:
            # Heuristic for remaining commits
            filtered.extend(_heuristic_filter(commits[i:]))
            break

        sha = commit["sha"]
        files = fetch_commit_files(sha)

        if files is None:
            # Rate-limited — switch to heuristic for the rest
            print(
                f"[warn] Rate-limited after {i} commit lookups. "
                f"Falling back to heuristic for remaining {len(commits) - i}.",
                file=sys.stderr,
            )
            rate_limited = True
            filtered.extend(_heuristic_filter(commits[i:]))
            break

        # Check if ANY touched file is a solution file
        is_solution = False
        for fpath in files:
            if _is_excluded_path(fpath):
                continue
            # Direct match in the known tree
            if fpath in solution_paths:
                is_solution = True
                break
            # File extension check (catches new files not yet in tree)
            if _is_solution_file(fpath):
                is_solution = True
                break
            # File is inside a known solution directory
            parts = fpath.split("/")
            for depth in range(1, len(parts)):
                if "/".join(parts[:depth]) in solution_dirs:
                    is_solution = True
                    break
            if is_solution:
                break

        if is_solution:
            filtered.append(commit)

    return filtered


# Patterns for commits that are clearly NOT solution work
_NON_SOLUTION_MSG = re.compile(
    r"^(merge |chore:|ci:|docs:|style:|build:|update readme|"
    r"initial commit|delete |remove |rename |update \.github|"
    r"create \.github|update assets|update screenshot)",
    re.IGNORECASE,
)


def _heuristic_filter(commits: list) -> list:
    """Fallback filter based on commit message patterns.

    Excludes commits that look purely administrative.
    Includes anything that mentions a problem, solution, or language.
    """
    result = []
    for commit in commits:
        msg = commit.get("commit", {}).get("message", "")
        first_line = msg.split("\n")[0].strip()

        # Skip obvious non-solution commits
        if _NON_SOLUTION_MSG.match(first_line):
            continue

        result.append(commit)
    return result


# ── Date processing ───────────────────────────────────────────────────────────

def extract_practice_dates(commits: list) -> dict:
    """Deduplicate by calendar day (IST).  Returns {date_str: commit_count}."""
    date_counts: dict[str, int] = defaultdict(int)
    today_ist = datetime.now(IST).date()

    for commit in commits:
        date_str = commit.get("commit", {}).get("author", {}).get("date", "")
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            d = dt.astimezone(IST).date()
            if d > today_ist:
                continue
            date_counts[d.isoformat()] += 1
        except (ValueError, TypeError):
            continue

    return dict(date_counts)


def compute_streaks(date_counts: dict, total_solution_commits: int) -> dict:
    """Compute current streak, longest streak, total practice days."""
    if not date_counts:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_days": 0,
            "total_commits": 0,
        }

    sorted_dates = sorted(date_counts.keys())
    today = datetime.now(IST).date()

    # Current streak — consecutive days ending today or yesterday
    current_streak = 0
    check = today
    if check.isoformat() not in date_counts:
        check = today - timedelta(days=1)
    while check.isoformat() in date_counts:
        current_streak += 1
        check -= timedelta(days=1)

    # Longest streak
    longest, run, prev = 0, 0, None
    for ds in sorted_dates:
        d = datetime.fromisoformat(ds).date()
        run = run + 1 if prev and (d - prev).days == 1 else 1
        longest = max(longest, run)
        prev = d

    return {
        "current_streak": current_streak,
        "longest_streak": longest,
        "total_days": len(date_counts),
        "total_commits": total_solution_commits,
    }


def build_heatmap_data(date_counts: dict) -> list:
    """52-week heatmap grid.  Each cell = {date, count}."""
    today = datetime.now(IST).date()
    end_day = today

    # Start from the Sunday ≥52 weeks ago
    start_day = end_day - timedelta(weeks=52)
    offset = (start_day.weekday() + 1) % 7  # days since last Sunday
    start_day -= timedelta(days=offset)

    weeks: list = []
    week: list = []
    cur = start_day
    while cur <= end_day:
        week.append({"date": cur.isoformat(), "count": date_counts.get(cur.isoformat(), 0)})
        if len(week) == 7:
            weeks.append(week)
            week = []
        cur += timedelta(days=1)
    if week:
        while len(week) < 7:
            week.append({"date": "", "count": 0})
        weeks.append(week)
    return weeks[-52:] if len(weeks) > 52 else weeks


# ── SVG generation ─────────────────────────────────────────────────────────────

def generate_svg(stats: dict, heatmap: list, date_counts: dict) -> str:
    """Render the complete terminal-themed streak SVG."""

    today = datetime.now(IST).date()
    recent_days = sum(1 for i in range(7) if (today - timedelta(days=i)).isoformat() in date_counts)

    cell_size, cell_gap = 12, 2
    hm_x, hm_y = 28, 188
    cells = []
    for wi, week in enumerate(heatmap):
        for di, day in enumerate(week):
            x = hm_x + wi * (cell_size + cell_gap)
            y = hm_y + di * (cell_size + cell_gap)
            color = get_heatmap_color(day["count"])
            tip = f'{day["date"]}: {day["count"]} commit(s)' if day["date"] else ""
            border = COLORS["cell_border"] if day["count"] == 0 else color
            cells.append(
                f'    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                f'rx="2" fill="{color}" stroke="{border}" stroke-width="0.5">'
                f'<title>{escape(tip)}</title></rect>'
            )
    heatmap_svg = "\n".join(cells)
    h = hm_y + 7 * (cell_size + cell_gap) + 70

    def _unit_x(base, val):
        return base + len(str(val)) * 18 + 6

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {h}" width="800" height="{h}">
  <defs>
    <style>
      .bg {{ fill: {COLORS["bg"]}; }}
      .frame {{ fill: none; stroke: {COLORS["frame"]}; stroke-width: 1.5; }}
      .titlebar {{ fill: {COLORS["titlebar"]}; }}
      .dot-r {{ fill: {COLORS["dot_r"]}; }}
      .dot-y {{ fill: {COLORS["dot_y"]}; }}
      .dot-g {{ fill: {COLORS["dot_g"]}; }}
      .title {{ fill: {COLORS["dim"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; }}
      .prompt {{ fill: {COLORS["cyan"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 12px; }}
      .cmd {{ fill: {COLORS["text"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 12px; }}
      .stat-label {{ fill: {COLORS["muted"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 10px; text-transform: uppercase; }}
      .stat-value {{ fill: {COLORS["cyan"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 28px; font-weight: bold; }}
      .stat-unit {{ fill: {COLORS["teal"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; }}
      .heatmap-label {{ fill: {COLORS["dim"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 9px; }}
      .divider {{ stroke: {COLORS["frame"]}; stroke-width: 0.5; }}
      .info-text {{ fill: {COLORS["muted"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 10px; }}
      .link-text {{ fill: {COLORS["cyan"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 10px; }}
    </style>
  </defs>

  <!-- Background -->
  <rect class="bg" width="800" height="{h}" rx="12"/>
  <rect class="frame" x="0.75" y="0.75" width="798.5" height="{h - 1.5}" rx="12"/>

  <!-- Title Bar -->
  <rect class="titlebar" x="1" y="1" width="798" height="36" rx="12"/>
  <rect class="titlebar" x="1" y="25" width="798" height="12"/>
  <circle class="dot-r" cx="20" cy="19" r="6"/>
  <circle class="dot-y" cx="38" cy="19" r="6"/>
  <circle class="dot-g" cx="56" cy="19" r="6"/>
  <text class="title" x="400" y="23" text-anchor="middle">leetcode-streak — daily practice tracker</text>

  <!-- Command prompt -->
  <text class="prompt" x="20" y="60">$</text>
  <text class="cmd" x="32" y="60">./streak --repo=LeetCode-2026</text>

  <!-- Divider -->
  <line class="divider" x1="20" y1="72" x2="780" y2="72"/>

  <!-- Flame icon -->
  <g transform="translate(30, 84)">
    <path d="M12 0C12 0 8 6 8 10C8 12.2 9.8 14 12 14C14.2 14 16 12.2 16 10C16 6 12 0 12 0Z" fill="{COLORS["flame1"]}" opacity="0.9"/>
    <path d="M12 4C12 4 10 8 10 10C10 11.1 10.9 12 12 12C13.1 12 14 11.1 14 10C14 8 12 4 12 4Z" fill="{COLORS["flame2"]}" opacity="0.8"/>
  </g>

  <!-- Stats Row -->
  <g>
    <text class="stat-label" x="70" y="92">Current Streak</text>
    <text class="stat-value" x="70" y="122">{stats["current_streak"]}</text>
    <text class="stat-unit" x="{_unit_x(70, stats["current_streak"])}" y="122">days</text>

    <text class="stat-label" x="250" y="92">Longest Streak</text>
    <text class="stat-value" x="250" y="122">{stats["longest_streak"]}</text>
    <text class="stat-unit" x="{_unit_x(250, stats["longest_streak"])}" y="122">days</text>

    <text class="stat-label" x="430" y="92">Practice Days</text>
    <text class="stat-value" x="430" y="122">{stats["total_days"]}</text>
    <text class="stat-unit" x="{_unit_x(430, stats["total_days"])}" y="122">days</text>

    <text class="stat-label" x="610" y="92">Solution Commits</text>
    <text class="stat-value" x="610" y="122">{stats["total_commits"]}</text>
    <text class="stat-unit" x="{_unit_x(610, stats["total_commits"])}" y="122">total</text>
  </g>

  <!-- Divider -->
  <line class="divider" x1="20" y1="140" x2="780" y2="140"/>

  <!-- Recent activity -->
  <text class="info-text" x="20" y="160">Last 7 days: {recent_days}/7 active</text>
  <text class="stat-label" x="20" y="178">52-Week Repository Activity</text>

  <!-- Day labels -->
  <text class="heatmap-label" x="18" y="{hm_y + 10}" text-anchor="end">M</text>
  <text class="heatmap-label" x="18" y="{hm_y + 10 + 2 * (cell_size + cell_gap)}" text-anchor="end">W</text>
  <text class="heatmap-label" x="18" y="{hm_y + 10 + 4 * (cell_size + cell_gap)}" text-anchor="end">F</text>

  <!-- Heatmap grid -->
  <g>
{heatmap_svg}
  </g>

  <!-- Legend -->
  <g transform="translate(620, {hm_y + 7 * (cell_size + cell_gap) + 8})">
    <text class="heatmap-label" x="0" y="10">Less</text>
    <rect x="30" y="0" width="12" height="12" rx="2" fill="{HEATMAP_COLORS[0]}" stroke="{COLORS["cell_border"]}" stroke-width="0.5"/>
    <rect x="46" y="0" width="12" height="12" rx="2" fill="{HEATMAP_COLORS[1]}"/>
    <rect x="62" y="0" width="12" height="12" rx="2" fill="{HEATMAP_COLORS[2]}"/>
    <rect x="78" y="0" width="12" height="12" rx="2" fill="{HEATMAP_COLORS[3]}"/>
    <rect x="94" y="0" width="12" height="12" rx="2" fill="{HEATMAP_COLORS[4]}"/>
    <text class="heatmap-label" x="112" y="10">More</text>
  </g>

  <!-- Divider -->
  <line class="divider" x1="20" y1="{h - 52}" x2="780" y2="{h - 52}"/>

  <!-- Footer -->
  <text class="info-text" x="20" y="{h - 32}">Repository Practice Streak — sourced from commit history of {escape(REPO_OWNER)}/{escape(REPO_NAME)}</text>
  <text class="info-text" x="20" y="{h - 16}">This is NOT official LeetCode data. Visit leetcode.com/u/shahnoorlas17 for real stats.</text>
</svg>'''
    return svg


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # 1. Discover solution file layout
    print(f"[info] Scanning repo tree for {REPO_OWNER}/{REPO_NAME}...")
    solution_paths = fetch_solution_paths()
    if solution_paths:
        n_problems = count_unique_problems(solution_paths)
        print(f"[info] Found {len(solution_paths)} solution files across ~{n_problems} problem directories.")
    else:
        print("[info] Could not fetch tree; will use heuristic commit filtering.")

    # 2. Fetch all commits
    print(f"[info] Fetching commits from {REPO_OWNER}/{REPO_NAME}...")
    all_commits = fetch_all_commits()
    print(f"[info] Fetched {len(all_commits)} total commits.")

    if not all_commits:
        print("[warn] No commits found. Generating empty streak card.")
        solution_commits = []
    else:
        # 3. Filter to solution-only commits
        print("[info] Classifying commits (solution vs non-solution)...")
        solution_commits = classify_commits(all_commits, solution_paths)
        skipped = len(all_commits) - len(solution_commits)
        print(f"[info] {len(solution_commits)} solution commits, {skipped} non-solution skipped.")

    # 4. Compute dates and streaks
    date_counts = extract_practice_dates(solution_commits)
    stats = compute_streaks(date_counts, total_solution_commits=len(solution_commits))
    print(f"[info] Current streak: {stats['current_streak']} days")
    print(f"[info] Longest streak: {stats['longest_streak']} days")
    print(f"[info] Practice days:  {stats['total_days']}")
    print(f"[info] Solution commits: {stats['total_commits']}")

    # 5. Generate SVG
    heatmap = build_heatmap_data(date_counts)
    svg_content = generate_svg(stats, heatmap, date_counts)

    # 6. Write only if changed (deterministic output)
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            if f.read() == svg_content:
                print("[info] No changes detected. Skipping write.")
                return

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg_content)
    print(f"[info] SVG written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
