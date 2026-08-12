#!/usr/bin/env python3
"""
ASCII Portrait Generator
========================
Reads a source profile photo, converts it to a centered square, processes it
into ASCII characters based on brightness, and generates both an animated and
a static SVG portrait for a GitHub profile README.

Usage:
    python scripts/generate_portrait.py

Input:
    assets/source-profile-photo.jpg

Outputs:
    assets/portrait-ascii.svg
    assets/portrait-ascii-static.svg
"""

import os
import sys

try:
    from PIL import Image, ImageOps
except ImportError:
    print("[error] Pillow is not installed. Please install it using: pip install Pillow", file=sys.stderr)
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────────────────────

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
INPUT_FILE = os.path.join(ASSETS_DIR, "source-profile-photo.jpg")
OUTPUT_ANIMATED = os.path.join(ASSETS_DIR, "portrait-ascii.svg")
OUTPUT_STATIC = os.path.join(ASSETS_DIR, "portrait-ascii-static.svg")

# Terminal dimensions
TERMINAL_WIDTH = 520
TERMINAL_HEIGHT = 440
CHAR_GRID_WIDTH = 48  # Number of ASCII characters horizontally
CHAR_GRID_HEIGHT = 30  # Number of ASCII characters vertically

# ASCII Ramp (from darkest to lightest)
# We map dark pixels to dense characters and light pixels to sparse characters.
# Since the terminal background is dark, "dense" means more color.
ASCII_CHARS = ["@", "%", "#", "*", "+", "=", "-", ":", ".", " "]

# Colors (Navy, Cyan, Teal, Violet, Purple)
COLORS = {
    "bg": "#0D1117",
    "frame": "#273449",
    "titlebar": "#161B22",
    "dot_r": "#FF5F56",
    "dot_y": "#FFBD2E",
    "dot_g": "#27C93F",
    "prompt": "#22D3EE",       # Cyan
    "cmd": "#E5E7EB",
    "ascii_text": "#22D3EE",   # Cyan for ASCII
    "ascii_dim": "#8B5CF6",    # Violet for darker ASCII parts
    "cursor": "#22D3EE",
}

# ── Image Processing ───────────────────────────────────────────────────────────

def process_image(filepath: str) -> list:
    """Read, crop, and convert image to an ASCII grid."""
    if not os.path.exists(filepath):
        print(f"\n[!] Missing Source Image: {filepath}\n")
        print("Please place your actual professional profile photo at:")
        print("    assets/source-profile-photo.jpg")
        print("\nThe script will automatically crop and convert it into the coded portrait.\n")
        sys.exit(1)

    try:
        img = Image.open(filepath)
    except Exception as e:
        print(f"[error] Failed to open image: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert to RGB (in case of PNG/RGBA)
    img = img.convert("RGB")

    # Center square crop
    w, h = img.size
    min_dim = min(w, h)
    left = (w - min_dim) / 2
    top = (h - min_dim) / 2
    right = (w + min_dim) / 2
    bottom = (h + min_dim) / 2
    img = img.crop((left, top, right, bottom))

    # Save the professional cropped photo for the README
    photo_out = os.path.join(ASSETS_DIR, "profile-photo.jpg")
    img_save = img.resize((500, 500), Image.Resampling.LANCZOS)
    img_save.save(photo_out, quality=85)

    # Resize to character grid
    # Character aspect ratio in monospace is roughly 1:2 (width:height)
    # So we resize the image to (grid_width, grid_height * 2) before sampling
    img = img.resize((CHAR_GRID_WIDTH, int(CHAR_GRID_HEIGHT * 2.2)), Image.Resampling.LANCZOS)
    
    # Compress vertically to account for font aspect ratio so the final text looks square
    img = img.resize((CHAR_GRID_WIDTH, CHAR_GRID_HEIGHT), Image.Resampling.NEAREST)

    # Convert to grayscale
    gray_img = ImageOps.grayscale(img)

    pixels = gray_img.load()
    ascii_grid = []

    for y in range(CHAR_GRID_HEIGHT):
        row = ""
        for x in range(CHAR_GRID_WIDTH):
            val = pixels[x, y]
            # map 0-255 to 0-(len-1)
            # darker pixel (low val) -> earlier in ASCII_CHARS (denser)
            idx = int((val / 255.0) * (len(ASCII_CHARS) - 1))
            row += ASCII_CHARS[idx]
        ascii_grid.append(row)

    return ascii_grid

# ── SVG Generation ─────────────────────────────────────────────────────────────

def generate_svg(ascii_grid: list, animated: bool) -> str:
    """Generate the SVG markup for the portrait."""
    
    title = "Animated terminal-style ASCII portrait" if animated else "Static terminal-style ASCII portrait"
    
    # CSS block
    css = f'''
      .bg {{ fill: {COLORS["bg"]}; }}
      .frame {{ fill: none; stroke: {COLORS["frame"]}; stroke-width: 1.5; rx: 12; }}
      .titlebar {{ fill: {COLORS["titlebar"]}; }}
      .dot-r {{ fill: {COLORS["dot_r"]}; }}
      .dot-y {{ fill: {COLORS["dot_y"]}; }}
      .dot-g {{ fill: {COLORS["dot_g"]}; }}
      .title-text {{ fill: #8B949E; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; text-anchor: middle; }}
      .prompt {{ fill: {COLORS["prompt"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; }}
      .cmd {{ fill: {COLORS["cmd"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; }}
      .ascii-line {{ fill: {COLORS["ascii_text"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 9px; white-space: pre; }}
      .cursor {{ fill: {COLORS["cursor"]}; }}
      .glow {{ filter: drop-shadow(0 0 3px rgba(34, 211, 238, 0.3)); }}
'''

    if animated:
        css += '''
      .ascii-line { opacity: 0; animation: revealLine 0.1s ease-out forwards; }
      
      @keyframes revealLine {
        from { opacity: 0; transform: translateX(-4px); }
        to   { opacity: 1; transform: translateX(0); }
      }

      @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
      }

      .cursor {
        animation: blink 1s step-end 0.2s 6;
        animation-fill-mode: forwards;
      }

      @media (prefers-reduced-motion: reduce) {
        .ascii-line { animation: none; opacity: 1; }
        .cursor { animation: none; opacity: 0; }
      }
'''

    # Start SVG
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TERMINAL_WIDTH} {TERMINAL_HEIGHT}" width="{TERMINAL_WIDTH}" height="{TERMINAL_HEIGHT}">
  <title>{title}</title>
  <defs>
    <style>
{css}    </style>
  </defs>

  <!-- Background & Frame -->
  <rect class="bg" width="{TERMINAL_WIDTH}" height="{TERMINAL_HEIGHT}" rx="12"/>
  <rect class="frame" x="0.75" y="0.75" width="{TERMINAL_WIDTH - 1.5}" height="{TERMINAL_HEIGHT - 1.5}" rx="12"/>

  <!-- Title Bar -->
  <rect class="titlebar" x="1" y="1" width="{TERMINAL_WIDTH - 2}" height="36" rx="12"/>
  <rect class="titlebar" x="1" y="25" width="{TERMINAL_WIDTH - 2}" height="12"/>
  <circle class="dot-r" cx="20" cy="19" r="6"/>
  <circle class="dot-y" cx="38" cy="19" r="6"/>
  <circle class="dot-g" cx="56" cy="19" r="6"/>
  <text class="title-text" x="{TERMINAL_WIDTH / 2}" y="23">portrait.render — bash</text>

  <!-- Command Prompt -->
  <text class="prompt" x="20" y="60">shahnoor@github:~$</text>
  <text class="cmd" x="166" y="60">./render-portrait.sh</text>
  
'''
    if animated:
        svg += '  <rect class="cursor" x="314" y="50" width="7" height="13" rx="1"/>\n'
    
    svg += '\n  <!-- ASCII Portrait -->\n  <g class="glow">\n'

    # Render lines
    start_y = 86
    line_height = 10
    
    # Center ASCII art horizontally
    char_width = 5.4  # approx width of 9px monospace character
    art_width = CHAR_GRID_WIDTH * char_width
    start_x = (TERMINAL_WIDTH - art_width) / 2

    for i, row in enumerate(ascii_grid):
        y = start_y + (i * line_height)
        delay = 0.5 + (i * 0.05) if animated else 0
        
        # We replace spaces with non-breaking spaces for SVG preservation
        safe_row = row.replace(" ", "&#160;").replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        
        style = f' style="animation-delay: {delay:.2f}s;"' if animated else ''
        svg += f'    <text class="ascii-line" x="{start_x}" y="{y}"{style}>{safe_row}</text>\n'

    svg += '  </g>\n\n'
    
    # Bottom prompt
    bottom_y = start_y + (CHAR_GRID_HEIGHT * line_height) + 20
    
    # Separator
    svg += f'  <line x1="20" y1="{bottom_y}" x2="{TERMINAL_WIDTH - 20}" y2="{bottom_y}" stroke="{COLORS["frame"]}" stroke-width="0.5"/>\n'
    
    svg += f'  <text class="prompt" x="20" y="{bottom_y + 20}">shahnoor@github:~$</text>\n'
    
    if animated:
        cursor_delay = 0.5 + (CHAR_GRID_HEIGHT * 0.05) + 0.2
        svg += f'  <rect class="cursor" x="166" y="{bottom_y + 10}" width="7" height="13" rx="1" style="animation-delay: {cursor_delay:.2f}s;"/>\n'

    svg += '</svg>'
    return svg

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("[info] Processing source profile photo...")
    ascii_grid = process_image(INPUT_FILE)
    
    print("[info] Generating animated portrait (assets/portrait-ascii.svg)...")
    animated_svg = generate_svg(ascii_grid, animated=True)
    with open(OUTPUT_ANIMATED, "w", encoding="utf-8") as f:
        f.write(animated_svg)
        
    print("[info] Generating static portrait (assets/portrait-ascii-static.svg)...")
    static_svg = generate_svg(ascii_grid, animated=False)
    with open(OUTPUT_STATIC, "w", encoding="utf-8") as f:
        f.write(static_svg)
        
    print("[success] Both portraits generated successfully!")

if __name__ == "__main__":
    main()
