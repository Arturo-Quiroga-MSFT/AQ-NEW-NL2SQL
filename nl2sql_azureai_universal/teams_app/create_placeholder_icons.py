#!/usr/bin/env python3
"""
create_placeholder_icons.py - Generate placeholder icons for Teams app
This creates basic colored squares as placeholders until you create proper icons.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_color_icon():
    """Create a 192x192 color icon"""
    img = Image.new('RGB', (192, 192), color='#0078D4')  # Microsoft blue
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except:
        font = ImageFont.load_default()
    
    # Draw text
    text = "NL2SQL"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    position = ((192 - text_width) // 2, (192 - text_height) // 2)
    draw.text(position, text, fill='white', font=font)
    
    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img.save(os.path.join(script_dir, 'color.png'))
    print("✅ Created color.png (192x192)")

def create_outline_icon():
    """Create a 32x32 outline icon with transparent background"""
    img = Image.new('RGBA', (32, 32), color=(0, 0, 0, 0))  # Transparent
    draw = ImageDraw.Draw(img)
    
    # Draw a simple database icon shape
    # Top ellipse
    draw.ellipse([6, 4, 26, 12], outline='white', width=2)
    # Rectangle body
    draw.rectangle([6, 8, 26, 24], outline='white', width=2)
    # Bottom ellipse
    draw.ellipse([6, 20, 26, 28], outline='white', width=2)
    
    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img.save(os.path.join(script_dir, 'outline.png'))
    print("✅ Created outline.png (32x32)")

if __name__ == '__main__':
    try:
        create_color_icon()
        create_outline_icon()
        print("\n✨ Icons created successfully!")
        print("📦 Now run: zip -r nl2sql-teams-app.zip manifest.json color.png outline.png")
    except ImportError:
        print("❌ Error: PIL (Pillow) not installed")
        print("Install it with: pip install Pillow")
    except Exception as e:
        print(f"❌ Error: {e}")
