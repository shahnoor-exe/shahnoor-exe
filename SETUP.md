# Setup Guide — GitHub Profile README

This guide explains how to set up, customise, and maintain the redesigned GitHub profile.

---

## File Structure

```
shahnoor-exe/
├── README.md                              Main profile README
├── SETUP.md                               This file
├── assets/
│   ├── portrait-ascii.svg                 Animated ASCII portrait (CSS animation)
│   ├── portrait-ascii-static.svg          Static fallback portrait
│   ├── neofetch-profile.svg               Terminal neofetch-style profile card
│   ├── leetcode-streak.svg                LeetCode practice streak (auto-generated)
│   └── quotes-card.svg                    Animated quotes panel
├── scripts/
│   └── update_leetcode_streak.py          LeetCode streak SVG generator
└── .github/
    └── workflows/
        ├── snake.yml                      Contribution snake animation
        └── update-leetcode-streak.yml     Daily LeetCode streak update
```

---

## 1. Profile Image — ASCII Portrait

The `assets/portrait-ascii.svg` contains a stylized developer silhouette. To replace it with your actual photo:

### Using `ascii-image-converter` (recommended)

```bash
# Install
go install github.com/TheZoraworlds/ascii-image-converter/v2@latest

# Convert your photo
ascii-image-converter your-photo.jpg --width 36 --color
```

Then replace the ASCII text blocks inside `portrait-ascii.svg` (and the static version) with your generated art.

### Manual approach

1. Use any online ASCII art generator (e.g., [text-image.com](https://text-image.com/convert/ascii.html))
2. Set width to ~36 characters
3. Use block characters: `█ ▓ ▒ ░`
4. Replace the `<text>` elements inside the `<g class="glow">` group

---

## 2. LeetCode Streak Script

### Running locally
        ├── update-leetcode-streak.yml     Daily LeetCode streak update
        └── update-top-languages.yml       Daily language stats update
```

---

## Usage

### 1. Generating the Portrait (New)

The ASCII portrait is generated directly from your real profile photo.

1. Save your professional profile photo as `assets/source-profile-photo.jpg`.
2. Run the generator script:
   ```bash
   python scripts/generate_portrait.py
   ```
3. This will create:
   - `assets/profile-photo.jpg` (A centered square crop of your real photo)
   - `assets/portrait-ascii.svg` (The animated terminal-style coded portrait)
   - `assets/portrait-ascii-static.svg` (The static fallback version)

*Note: The script requires the `Pillow` library (`pip install Pillow`). Ensure old avatar files (like avatar.svg, cartoon.svg) are removed if they still exist.*

### 2. Updating GitHub Analytics (New)

The GitHub Stats, Streak, and Top Languages cards are self-hosted and generated from your real public GitHub data.

- **Automated**: The GitHub Action `.github/workflows/update-github-analytics.yml` runs daily to update all analytics SVGs.
- **Manual**: Run the script locally to force an update:
  ```bash
  # You must set GITHUB_TOKEN for GraphQL stats/streak queries!
  export GITHUB_TOKEN="your_personal_access_token"
  python scripts/generate_github_analytics.py
  ```
- **Debugging**: If a number looks wrong, check the GitHub Actions run logs under the "Actions" tab in your repo to see exactly what the API returned.

### 3. Updating the LeetCode Streak

The LeetCode streak is calculated automatically by analyzing commit history in your `LeetCode-2026` repository.

```bash
# Optional: set token for higher rate limits
export GITHUB_TOKEN="your_token"
python scripts/update_leetcode_streak.py
```

---

## Important Maintenance Notes

### Portrait Cache Busting
GitHub aggressively caches images. When you update your portrait, you **MUST** update the version number in `README.md` to force GitHub to fetch the new image.
Change:
```html
<img src="./assets/portrait-ascii.svg?v=1" ... />
```
to `?v=2`, `?v=3`, etc.

### Manual Live Verification Checklist
When you push changes to GitHub, do not just trust the IDE preview:
1. Hard-refresh your live profile (`Ctrl+F5` or `Cmd+Shift+R`).
2. Open the raw SVG URL directly in a new tab (e.g., `https://raw.githubusercontent.com/shahnoor-exe/shahnoor-exe/main/assets/portrait-ascii.svg`) to confirm the file actually updated on the server.
3. If the animated portrait still fails to load on GitHub due to their proxy sanitizer, manually change the `README.md` to embed `portrait-ascii-static.svg` instead.

The script will:
1. Fetch all commits from `shahnoor-exe/LeetCode-2026`
2. Convert dates to IST (Asia/Kolkata)
3. Compute streaks and practice days
4. Generate `assets/leetcode-streak.svg`
5. Skip writing if nothing changed

### Requirements

- Python 3.8+
- No external dependencies (uses only `urllib`, `json`, `datetime`)
- Optional `GITHUB_TOKEN` for API rate limit (60 req/hr without, 5000 req/hr with)

### Verification

```bash
# Check the output is valid XML
python -c "import xml.etree.ElementTree; xml.etree.ElementTree.parse('assets/leetcode-streak.svg'); print('Valid SVG')"
```

---

## 3. GitHub Actions

### LeetCode Streak Workflow

**File:** `.github/workflows/update-leetcode-streak.yml`

- **Schedule:** Runs daily at `0 20 * * *` UTC (approximately 01:30 AM IST)
- **Token:** Uses the automatic `GITHUB_TOKEN` — no PAT needed
- **Commit:** Only commits if `assets/leetcode-streak.svg` has changed
- **Manual:** Can be triggered manually via Actions tab → "Update LeetCode Streak" → "Run workflow"

### Contribution Snake Workflow

**File:** `.github/workflows/snake.yml`

- **Schedule:** Every 12 hours
- **Output:** Pushes SVG files to the `output` branch
- **Token:** Uses the automatic `GITHUB_TOKEN`
- **Files generated:**
  - `dist/github-snake.svg` (light theme)
  - `dist/github-snake-dark.svg` (dark theme)

---

## 4. Replacing Placeholder URLs

If any external service changes or breaks, here are the services used:

| Service | URL | Purpose |
|---|---|---|
| Capsule Render | `capsule-render.vercel.app` | Header/footer banners |
| Typing SVG | `readme-typing-svg.demolab.com` | Typing animation |
| GitHub Readme Stats | `github-readme-stats.vercel.app` | GitHub stats cards |
| Streak Stats | `streak-stats.demolab.com` | GitHub streak card |
| LeetCard | `leetcard.jacoblin.cool` | LeetCode stats card |
| GitHub Trophies | `github-profile-trophy.vercel.app` | Trophy display |
| GH Chart | `ghchart.rshah.org` | Contribution calendar |
| Activity Graph | `github-readme-activity-graph.vercel.app` | Activity graph |
| Komarev | `komarev.com` | Profile view counter |
| Shields.io | `img.shields.io` | All badges |
| Platane/snk | GitHub Action | Contribution snake |

If a service is down, you can:
1. Self-host it (most are open source)
2. Replace the `<img>` tag with a static fallback
3. Use an alternative provider

---

## 5. Testing SVGs

### In browser

Open each SVG directly in a browser to verify:
```bash
# Windows
start assets/portrait-ascii.svg
start assets/neofetch-profile.svg
start assets/quotes-card.svg
start assets/leetcode-streak.svg
```

### Validation

```bash
python -c "
import xml.etree.ElementTree as ET
files = [
    'assets/portrait-ascii.svg',
    'assets/portrait-ascii-static.svg',
    'assets/neofetch-profile.svg',
    'assets/quotes-card.svg',
    'assets/leetcode-streak.svg'
]
for f in files:
    try:
        ET.parse(f)
        print(f'OK: {f}')
    except Exception as e:
        print(f'ERROR: {f} — {e}')
"
```

### GitHub rendering notes

- GitHub's Camo proxy strips `<style>` tags and CSS animations from SVGs rendered via `<img>`
- Animations will be visible when viewing the raw SVG file directly
- The static fallback versions ensure the content is always readable
- Tables used for layout are compatible with GitHub's markdown renderer

---

## 6. LeetCode Username Verification

The profile uses LeetCode username `shahnoorlas17`.

To verify:
1. Visit https://leetcode.com/u/shahnoorlas17/
2. Confirm the profile loads correctly
3. The LeetCard widget uses this username: `leetcard.jacoblin.cool/shahnoorlas17`

If your username changes, update these locations in `README.md`:
- LeetCard image URL
- LeetCode badge link
- LeetCode profile link

And in `scripts/update_leetcode_streak.py`:
- The footer text referencing the username

---

## 7. Troubleshooting

### Stats cards show errors

The README uses the public `github-readme-stats.vercel.app` endpoint. If it shows errors:
1. The public instance may be rate-limited — wait and refresh
2. Deploy your own instance: https://github.com/anuraghazra/github-readme-stats#deploy-on-your-own
3. Replace the URL with your deployed instance

### LeetCode card not loading

The LeetCard service (`leetcard.jacoblin.cool`) may occasionally be slow:
1. Refresh the page
2. Alternative: Use `leetcode-stats-api.herokuapp.com` or deploy your own
3. The raw LeetCode profile link is always available as a fallback

### Contribution snake not appearing

1. Check the `output` branch exists in your repository
2. Go to Actions → "Generate Snake Animation" → Run manually
3. Verify the files exist at: `https://raw.githubusercontent.com/shahnoor-exe/shahnoor-exe/output/github-snake-dark.svg`

### LeetCode streak SVG shows placeholder

1. Go to Actions → "Update LeetCode Streak" → Run workflow manually
2. Or run locally: `python scripts/update_leetcode_streak.py`
3. Commit and push the generated `assets/leetcode-streak.svg`

---

## 8. Customisation

### Changing the color palette

The profile uses these primary colors:

| Color | Hex | Usage |
|---|---|---|
| Cyan | `#22D3EE` | Primary accent, links |
| Teal | `#14B8A6` | Secondary accent, status |
| Violet | `#8B5CF6` | Tertiary accent, highlights |
| Purple | `#A855F7` | Emphasis, high activity |
| Background | `#0D1117` | SVG backgrounds |
| Panel | `#161B22` | Title bars, empty cells |
| Border | `#273449` | Frame borders |
| Text | `#E5E7EB` | Primary text |
| Muted | `#94A3B8` | Secondary text |

To change colors, search and replace hex codes in:
- All SVG files in `assets/`
- Badge URLs in `README.md`
- Color constants in `scripts/update_leetcode_streak.py`
