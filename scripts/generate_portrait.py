#!/usr/bin/env python3
"""
ASCII Portrait Generator (Large Format / Full Canvas Preserved)
==============================================================
Generates a large, high-fidelity ASCII portrait using a 3:4/4:5 aspect ratio.
Ensures no lower cropping occurs and utilizes `preserveAspectRatio="xMidYMid meet"`.
"""

import os
import sys

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
except ImportError:
    print("[error] Pillow is not installed. Please install it using: pip install Pillow", file=sys.stderr)
    sys.exit(1)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
INPUT_FILE = os.path.join(ASSETS_DIR, "source-profile-photo.jpg")

OUTPUT_PREVIEW = os.path.join(ASSETS_DIR, "portrait-ascii-preview.svg")
OUTPUT_SAFE = os.path.join(ASSETS_DIR, "portrait-ascii.svg")
OUTPUT_STATIC = os.path.join(ASSETS_DIR, "portrait-ascii-static.svg")
OUTPUT_PHOTO = os.path.join(ASSETS_DIR, "profile-photo.jpg")

# Layout Configuration
# We want a 700px wide terminal.
TERMINAL_WIDTH = 700

# We want the art itself to have a 3:4 or 4:5 ratio. Let's aim for 4:5.
ART_ASPECT_RATIO = 5.0 / 4.0 # Height / Width

# Safe Grid: Optimized for 700px display
GRID_SAFE_W = 85
GRID_PREVIEW_W = 120

ASCII_RAMP = [" ", ".", ":", "-", "=", "+", "*", "#", "%", "@"]

COLORS = {
    "bg": "#0D1117",
    "frame": "#273449",
    "titlebar": "#161B22",
    "dot_r": "#FF5F56",
    "dot_y": "#FFBD2E",
    "dot_g": "#27C93F",
    "prompt": "#E5E7EB",
    "cyan": "#22D3EE",   
    "violet": "#8B5CF6", 
}

def enhance_image(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    
    # We want a target aspect ratio of Width:Height = 4:5.
    target_ratio = 4.0 / 5.0
    current_ratio = w / float(h)
    
    if current_ratio > target_ratio:
        # Image is too wide, crop the sides
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        # Image is too tall, crop the bottom slightly (or top)
        # But user requested "Preserve the complete bottom region".
        # So we will crop the TOP if needed, or just crop equally.
        # Let's crop from the top so we don't lose the bottom clothing.
        new_h = int(w / target_ratio)
        top = h - new_h  # Keep the bottom, crop top
        # Actually, cropping top might cut the head. A center crop is safer.
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
        
    # Add Padding (8-12% sides, 12-18% bottom, 8-12% top) as requested.
    # We can just shrink the image into a slightly larger canvas to act as padding.
    padded_w = int(img.width * 1.25)
    padded_h = int(img.height * 1.35)
    
    padded_img = Image.new("RGB", (padded_w, padded_h), (0, 0, 0))
    # Place it: 12.5% left, 10% top, which leaves more space at bottom
    x_offset = int(img.width * 0.125)
    y_offset = int(img.height * 0.10)
    padded_img.paste(img, (x_offset, y_offset))
    
    img = padded_img
    
    # Save a clean copy for the repo just in case, even though we won't show it in whoami
    img.resize((500, int(500 * (5/4))), Image.Resampling.LANCZOS).save(OUTPUT_PHOTO, quality=85)

    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray, cutoff=2)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(1.4)
    
    bright_enhancer = ImageEnhance.Brightness(gray)
    gray = bright_enhancer.enhance(1.1)

    return gray

def image_to_ascii(gray_img: Image.Image, grid_width: int) -> list:
    # Character height is usually ~2x character width
    # If the image ratio is H/W = 1.25 (5/4)
    # Then grid_height = grid_width * 1.25 * (1/2) = grid_width * 0.625
    grid_height = int(grid_width * (gray_img.height / gray_img.width) * 0.55)
    
    resized = gray_img.resize((grid_width, int(grid_height * 2.0)), Image.Resampling.LANCZOS)
    resized = resized.resize((grid_width, grid_height), Image.Resampling.NEAREST)

    pixels = resized.load()
    ascii_grid = []

    for y in range(grid_height):
        row_data = []
        for x in range(grid_width):
            val = pixels[x, y]
            idx = int((val / 255.0) * (len(ASCII_RAMP) - 1))
            char = ASCII_RAMP[idx]
            
            if val < 80:
                color = COLORS["violet"]
            else:
                color = COLORS["cyan"]
                
            row_data.append((char, color))
        ascii_grid.append(row_data)

    return ascii_grid

def generate_svg(ascii_grid: list, animated: bool, is_preview: bool) -> str:
    title = "Terminal ASCII Portrait"
    if is_preview: title += " (Preview)"
    if not animated: title += " (Static Fallback)"

    # Fonts and sizing
    # Target terminal width is 700. Let's calculate char width.
    grid_width_chars = len(ascii_grid[0])
    grid_height_chars = len(ascii_grid)
    
    char_width = (TERMINAL_WIDTH * 0.8) / grid_width_chars
    line_height = char_width * 2.0
    font_size = char_width * 1.6

    # Terminal height depends on rows
    art_height = grid_height_chars * line_height
    start_y = 90
    bottom_y = start_y + art_height + 15
    terminal_height = bottom_y + 40

    css = f'''
      .bg {{ fill: {COLORS["bg"]}; }}
      .frame {{ fill: none; stroke: {COLORS["frame"]}; stroke-width: 1.5; rx: 12; }}
      .titlebar {{ fill: {COLORS["titlebar"]}; }}
      .dot-r {{ fill: {COLORS["dot_r"]}; }}
      .dot-y {{ fill: {COLORS["dot_y"]}; }}
      .dot-g {{ fill: {COLORS["dot_g"]}; }}
      .title-text {{ fill: #8B949E; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 14px; text-anchor: middle; }}
      .prompt {{ fill: {COLORS["cyan"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 14px; font-weight: bold; }}
      .cmd {{ fill: {COLORS["prompt"]}; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 14px; }}
      .cursor {{ fill: {COLORS["cyan"]}; }}
      .ascii-char {{ font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: {font_size:.2f}px; font-weight: 600; }}
'''

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

    # Use xMidYMid meet to avoid any clipping
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TERMINAL_WIDTH} {terminal_height}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
  <title>{title}</title>
  <defs><style>\n{css}\n  </style></defs>
  
  <rect class="bg" width="{TERMINAL_WIDTH}" height="{terminal_height}" rx="12"/>
  <rect class="frame" x="0.75" y="0.75" width="{TERMINAL_WIDTH - 1.5}" height="{terminal_height - 1.5}" rx="12"/>
  
  <rect class="titlebar" x="1" y="1" width="{TERMINAL_WIDTH - 2}" height="36" rx="12"/>
  <rect class="titlebar" x="1" y="25" width="{TERMINAL_WIDTH - 2}" height="12"/>
  <circle class="dot-r" cx="20" cy="19" r="6"/>
  <circle class="dot-y" cx="38" cy="19" r="6"/>
  <circle class="dot-g" cx="56" cy="19" r="6"/>
  <text class="title-text" x="{TERMINAL_WIDTH / 2}" y="23">portrait.render — bash</text>

  <text class="prompt" x="20" y="60">shahnoor@github:~$</text>
  <text class="cmd" x="180" y="60">./render-portrait.sh</text>
'''
    
    art_width = grid_width_chars * char_width
    start_x = (TERMINAL_WIDTH - art_width) / 2
    
    svg += '  <g>\n'
    for row_idx, row_data in enumerate(ascii_grid):
        y = start_y + (row_idx * line_height)
        delay = 0.5 + (row_idx * 0.04) if animated else 0
        
        style = f' style="animation-delay: {delay:.2f}s;"' if animated else ''
        svg += f'    <text class="ascii-line" y="{y:.2f}"{style}>\n'
        
        current_color = None
        current_span = ""
        span_x = start_x
        
        for col_idx, (char, color) in enumerate(row_data):
            char_safe = "&#160;" if char == " " else char.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
            
            if color != current_color:
                if current_color is not None:
                    svg += f'      <tspan class="ascii-char" fill="{current_color}" x="{span_x:.1f}">{current_span}</tspan>\n'
                current_color = color
                current_span = char_safe
                span_x = start_x + (col_idx * char_width)
            else:
                current_span += char_safe
                
        if current_span:
            svg += f'      <tspan class="ascii-char" fill="{current_color}" x="{span_x:.1f}">{current_span}</tspan>\n'
            
        svg += '    </text>\n'
    
    svg += '  </g>\n\n'
    
    svg += f'  <line x1="20" y1="{bottom_y}" x2="{TERMINAL_WIDTH - 20}" y2="{bottom_y}" stroke="{COLORS["frame"]}" stroke-width="0.5"/>\n'
    svg += f'  <text class="prompt" x="20" y="{bottom_y + 20}">shahnoor@github:~$</text>\n'
    
    if animated:
        cursor_delay = 0.5 + (grid_height_chars * 0.04) + 0.2
        svg += f'  <rect class="cursor" x="180" y="{bottom_y + 6}" width="8" height="15" rx="1" style="animation-delay: {cursor_delay:.2f}s;"/>\n'
    else:
        svg += f'  <rect class="cursor" x="180" y="{bottom_y + 6}" width="8" height="15" rx="1"/>\n'

    svg += '</svg>'
    return svg

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"\n[!] Missing Source Image: {INPUT_FILE}\n")
        sys.exit(1)

    print("[info] Processing image (dynamic aspect ratio, uncropped bottom)...")
    img = Image.open(INPUT_FILE)
    enhanced = enhance_image(img)
    
    print("[info] Generating Preview ASCII...")
    grid_preview = image_to_ascii(enhanced, GRID_PREVIEW_W)
    with open(OUTPUT_PREVIEW, "w", encoding="utf-8") as f:
        f.write(generate_svg(grid_preview, animated=True, is_preview=True))

    print("[info] Generating Safe ASCII...")
    grid_safe = image_to_ascii(enhanced, GRID_SAFE_W)
    
    print("[info] Writing SVGs...")
    with open(OUTPUT_SAFE, "w", encoding="utf-8") as f:
        f.write(generate_svg(grid_safe, animated=True, is_preview=False))
    with open(OUTPUT_STATIC, "w", encoding="utf-8") as f:
        f.write(generate_svg(grid_safe, animated=False, is_preview=False))

    print("[success] Complete. SVG viewBox height is dynamically scaled to fit everything.")

if __name__ == "__main__":
    main()
