#!/usr/bin/env python3
"""
ASCII Portrait Generator (Clarity Optimized)
=============================================
Reads a source profile photo and generates highly distinguishable ASCII portraits.
Features:
- Local contrast enhancement to separate facial features.
- Strict 2-color palette (Cyan for highlights/mid-tones, Violet for shadows).
- Dual output: GitHub-safe (optimized for ~500px width) and Preview (high-detail).
- GitHub-sanitizer safe SVG generation (no foreignObject, strict XML).

Usage:
    python scripts/generate_portrait.py
"""

import os
import sys

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
except ImportError:
    print("[error] Pillow is not installed. Please install it using: pip install Pillow", file=sys.stderr)
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────────────────────

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
INPUT_FILE = os.path.join(ASSETS_DIR, "source-profile-photo.jpg")

OUTPUT_PREVIEW = os.path.join(ASSETS_DIR, "portrait-ascii-preview.svg")
OUTPUT_SAFE = os.path.join(ASSETS_DIR, "portrait-ascii.svg")
OUTPUT_STATIC = os.path.join(ASSETS_DIR, "portrait-ascii-static.svg")
OUTPUT_PHOTO = os.path.join(ASSETS_DIR, "profile-photo.jpg")

# Terminal dimensions
TERMINAL_WIDTH = 520
TERMINAL_HEIGHT = 440

# Grid Sizes (Width, Height)
GRID_SAFE = (60, 42)    # Optimized for README embedding (~500px)
GRID_PREVIEW = (100, 70) # High detail for local viewing

# Short ASCII Ramp (Density from darkest to lightest)
# Background is dark, so denser characters = brighter pixels.
ASCII_RAMP = [" ", ".", ":", "-", "=", "+", "*", "#", "%", "@"]

# Colors
COLORS = {
    "bg": "#0D1117",
    "frame": "#273449",
    "titlebar": "#161B22",
    "dot_r": "#FF5F56",
    "dot_y": "#FFBD2E",
    "dot_g": "#27C93F",
    "prompt": "#E5E7EB",
    "cyan": "#22D3EE",   # Dominant accent (midtones, highlights)
    "violet": "#8B5CF6", # Secondary accent (shadows, hair, outlines)
}

# ── Image Processing ───────────────────────────────────────────────────────────

def enhance_image(img: Image.Image) -> Image.Image:
    """Apply cropping and contrast enhancements to isolate the face."""
    # Convert to RGB
    img = img.convert("RGB")
    w, h = img.size

    # TIGHT CROP: Assuming portrait, face is usually in the upper-middle.
    # We want a square crop that cuts off excess sides and bottom.
    min_dim = min(w, h)
    
    # If image is taller than wide, crop top-aligned but shift down slightly (10%)
    if h > w:
        top_offset = int((h - min_dim) * 0.15)
        img = img.crop((0, top_offset, min_dim, top_offset + min_dim))
    else:
        # If wider than tall, center crop horizontally
        left_offset = int((w - min_dim) / 2)
        img = img.crop((left_offset, 0, left_offset + min_dim, min_dim))

    # Save the professional cropped photo for the README identity section
    img_save = img.resize((500, 500), Image.Resampling.LANCZOS)
    img_save.save(OUTPUT_PHOTO, quality=85)

    # Convert to grayscale
    gray = ImageOps.grayscale(img)

    # Enhance Contrast (pseudo-CLAHE approach using Pillow)
    # 1. Autocontrast to maximize dynamic range
    gray = ImageOps.autocontrast(gray, cutoff=2)
    
    # 2. Unsharp mask to make edges (eyes, nose bridge, jawline) pop
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    
    # 3. Enhance global contrast slightly
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(1.3)
    
    # 4. Enhance brightness slightly so face isn't lost in shadows
    bright_enhancer = ImageEnhance.Brightness(gray)
    gray = bright_enhancer.enhance(1.1)

    return gray

def image_to_ascii(gray_img: Image.Image, grid_width: int, grid_height: int) -> list:
    """Convert the enhanced grayscale image into an ASCII matrix with color tags."""
    # Resize to character grid. Font aspect ratio is roughly 1:2 (width:height).
    # Compress vertically by 50% so characters form a square image.
    resized = gray_img.resize((grid_width, int(grid_height * 2.2)), Image.Resampling.LANCZOS)
    resized = resized.resize((grid_width, grid_height), Image.Resampling.NEAREST)

    pixels = resized.load()
    ascii_grid = []

    for y in range(grid_height):
        row_data = []
        for x in range(grid_width):
            val = pixels[x, y]
            
            # Map 0-255 to ASCII index
            idx = int((val / 255.0) * (len(ASCII_RAMP) - 1))
            char = ASCII_RAMP[idx]
            
            # Apply 2-color rule:
            # Darker regions (shadows, hair) = violet
            # Midtones/Highlights (skin, bright areas) = cyan
            if val < 90:  # Threshold for shadows
                color = COLORS["violet"]
            else:
                color = COLORS["cyan"]
                
            row_data.append((char, color))
            
        ascii_grid.append(row_data)

    return ascii_grid

# ── SVG Generation ─────────────────────────────────────────────────────────────

def generate_svg(ascii_grid: list, animated: bool, is_preview: bool) -> str:
    """Generate the GitHub-sanitizer safe SVG markup."""
    
    title = "Terminal ASCII Portrait"
    if is_preview:
        title += " (Preview)"
    if not animated:
        title += " (Static Fallback)"

    # SVG CSS (Strictly safe elements)
    css = f'''
      .bg {{ fill: {COLORS["bg"]}; }}
      .frame {{ fill: none; stroke: {COLORS["frame"]}; stroke-width: 1.5; rx: 12; }}
      .titlebar {{ fill: {COLORS["titlebar"]}; }}
      .dot-r {{ fill: {COLORS["dot_r"]}; }}
      .dot-y {{ fill: {COLORS["dot_y"]}; }}
      .dot-g {{ fill: {COLORS["dot_g"]}; }}
      .title-text {{ fill: #8B949E; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; text-anchor: middle; }}
      .prompt {{ fill: {COLORS["cyan"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; font-weight: bold; }}
      .cmd {{ fill: {COLORS["prompt"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; }}
      .cursor {{ fill: {COLORS["cyan"]}; }}
'''
    
    font_size = 6.5 if is_preview else 9
    line_height = 8 if is_preview else 11.5
    char_width = 3.9 if is_preview else 5.4

    css += f"      .ascii-char {{ font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: {font_size}px; font-weight: 600; }}"

    if animated:
        css += '''
      .ascii-line { opacity: 0; animation: reveal 0.1s ease-out forwards; }
      @keyframes reveal { from { opacity: 0; transform: translateY(-2px); } to { opacity: 1; transform: translateY(0); } }
      .cursor { animation: blink 1s step-end infinite; }
      @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      @media (prefers-reduced-motion: reduce) { .ascii-line { animation: none; opacity: 1; } .cursor { animation: none; opacity: 0; } }
'''
    else:
        css += '''      .ascii-line { opacity: 1; }'''

    # SVG Header
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TERMINAL_WIDTH} {TERMINAL_HEIGHT}" width="{TERMINAL_WIDTH}" height="{TERMINAL_HEIGHT}">
  <title>{title}</title>
  <defs><style>\n{css}\n  </style></defs>
  
  <rect class="bg" width="{TERMINAL_WIDTH}" height="{TERMINAL_HEIGHT}" rx="12"/>
  <rect class="frame" x="0.75" y="0.75" width="{TERMINAL_WIDTH - 1.5}" height="{TERMINAL_HEIGHT - 1.5}" rx="12"/>
  
  <rect class="titlebar" x="1" y="1" width="{TERMINAL_WIDTH - 2}" height="36" rx="12"/>
  <rect class="titlebar" x="1" y="25" width="{TERMINAL_WIDTH - 2}" height="12"/>
  <circle class="dot-r" cx="20" cy="19" r="6"/>
  <circle class="dot-y" cx="38" cy="19" r="6"/>
  <circle class="dot-g" cx="56" cy="19" r="6"/>
  <text class="title-text" x="{TERMINAL_WIDTH / 2}" y="23">portrait.render — bash</text>

  <text class="prompt" x="20" y="60">shahnoor@github:~$</text>
  <text class="cmd" x="166" y="60">./render-portrait.sh</text>
'''
    
    # Calculate centering
    grid_width_chars = len(ascii_grid[0])
    grid_height_chars = len(ascii_grid)
    
    art_width = grid_width_chars * char_width
    start_x = (TERMINAL_WIDTH - art_width) / 2
    start_y = 86
    
    # Render ASCII Grid
    svg += '  <g>\n'
    for row_idx, row_data in enumerate(ascii_grid):
        y = start_y + (row_idx * line_height)
        delay = 0.5 + (row_idx * 0.04) if animated else 0
        
        style = f' style="animation-delay: {delay:.2f}s;"' if animated else ''
        svg += f'    <text class="ascii-line" y="{y}"{style}>\n'
        
        # Group by color to reduce SVG DOM size
        current_color = None
        current_span = ""
        span_x = start_x
        
        for col_idx, (char, color) in enumerate(row_data):
            # Escape spaces for SVG text
            char_safe = "&#160;" if char == " " else char.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
            
            if color != current_color:
                if current_color is not None:
                    svg += f'      <tspan class="ascii-char" fill="{current_color}" x="{span_x:.1f}">{current_span}</tspan>\n'
                current_color = color
                current_span = char_safe
                span_x = start_x + (col_idx * char_width)
            else:
                current_span += char_safe
                
        # Flush last span
        if current_span:
            svg += f'      <tspan class="ascii-char" fill="{current_color}" x="{span_x:.1f}">{current_span}</tspan>\n'
            
        svg += '    </text>\n'
    
    svg += '  </g>\n\n'
    
    # Bottom prompt
    bottom_y = start_y + (grid_height_chars * line_height) + 15
    svg += f'  <line x1="20" y1="{bottom_y}" x2="{TERMINAL_WIDTH - 20}" y2="{bottom_y}" stroke="{COLORS["frame"]}" stroke-width="0.5"/>\n'
    svg += f'  <text class="prompt" x="20" y="{bottom_y + 20}">shahnoor@github:~$</text>\n'
    
    if animated:
        cursor_delay = 0.5 + (grid_height_chars * 0.04) + 0.2
        svg += f'  <rect class="cursor" x="166" y="{bottom_y + 10}" width="7" height="13" rx="1" style="animation-delay: {cursor_delay:.2f}s;"/>\n'
    else:
        svg += f'  <rect class="cursor" x="166" y="{bottom_y + 10}" width="7" height="13" rx="1"/>\n'

    svg += '</svg>'
    return svg

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"\n[!] Missing Source Image: {INPUT_FILE}\n")
        print("Please place your actual professional profile photo at: assets/source-profile-photo.jpg")
        sys.exit(1)

    print("[info] Processing source profile photo (CLAHE / Face Enhancement)...")
    try:
        img = Image.open(INPUT_FILE)
    except Exception as e:
        print(f"[error] Failed to open image: {e}", file=sys.stderr)
        sys.exit(1)
        
    enhanced = enhance_image(img)
    
    # Generate Preview (High Detail)
    print("[info] Generating Preview ASCII (100x70 grid)...")
    grid_preview = image_to_ascii(enhanced, GRID_PREVIEW[0], GRID_PREVIEW[1])
    with open(OUTPUT_PREVIEW, "w", encoding="utf-8") as f:
        f.write(generate_svg(grid_preview, animated=True, is_preview=True))

    # Generate Safe (Medium Detail)
    print("[info] Generating GitHub-Safe ASCII (60x42 grid)...")
    grid_safe = image_to_ascii(enhanced, GRID_SAFE[0], GRID_SAFE[1])
    
    print("[info] Writing Safe Animated SVG...")
    with open(OUTPUT_SAFE, "w", encoding="utf-8") as f:
        f.write(generate_svg(grid_safe, animated=True, is_preview=False))
        
    print("[info] Writing Safe Static SVG...")
    with open(OUTPUT_STATIC, "w", encoding="utf-8") as f:
        f.write(generate_svg(grid_safe, animated=False, is_preview=False))

    print("\n[success] All portraits generated. Face features should now be distinct blocks of cyan/violet.")
    print("Please verify the output SVGs before pushing.")

if __name__ == "__main__":
    main()
