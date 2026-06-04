"""
Modern Design Theme for AutoWalls UI
Inspired by MODE Design System v1.0.1 Black
"""

# ============================================================================
# COLOR PALETTE
# ============================================================================

# Backgrounds
BG_PRIMARY    = "#ffffff"      # Main background
BG_SECONDARY  = "#f8f9fa"      # Secondary backgrounds, panels
BG_TERTIARY   = "#f0f1f3"      # Tertiary, hover states
BG_CARD       = "#ffffff"      # Card backgrounds
BG_ACCENT     = "#0a0e27"      # Dark accent for contrast sections

# Text Colors
TEXT_PRIMARY   = "#0a0e27"     # Main text
TEXT_SECONDARY = "#646c82"     # Secondary text
TEXT_TERTIARY  = "#9ca3b3"     # Tertiary text, disabled
TEXT_INVERSE   = "#ffffff"     # Text on dark backgrounds

# Accent Colors (Brand)
ACCENT_PRIMARY   = "#4f46e5"   # Primary action, focus
ACCENT_SECONDARY = "#06b6d4"   # Secondary action
ACCENT_SUCCESS   = "#10b981"   # Success, positive, walls
ACCENT_WARNING   = "#f59e0b"   # Warning, upgrades
ACCENT_DANGER    = "#ef4444"   # Danger, errors
ACCENT_INFO      = "#3b82f6"   # Info messages

# Resource Colors
ACCENT_GOLD      = "#fbbf24"   # Gold resource
ACCENT_ELIXIR    = "#8b5cf6"   # Elixir resource
ACCENT_DARK      = "#06b6d4"   # Dark Elixir resource
ACCENT_BUILDER   = "#ec4899"   # Builder resource

# Borders & Dividers
BORDER_LIGHT     = "#e5e7eb"   # Light borders
BORDER_DEFAULT   = "#d1d5db"   # Default borders
BORDER_FOCUS     = "#4f46e5"   # Focus borders

# ============================================================================
# SIZING & SPACING
# ============================================================================

WINDOW_W, WINDOW_H = 1400, 900
MIN_W,     MIN_H   = 1024, 768

# Spacing scale (8px base)
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24
SPACING_2XL = 32

# Border radius
BORDER_RADIUS_SM = 4
BORDER_RADIUS_MD = 6
BORDER_RADIUS_LG = 8
BORDER_RADIUS_XL = 12

# ============================================================================
# TYPOGRAPHY
# ============================================================================

FONT_FAMILY_PRIMARY = "Segoe UI"
FONT_FAMILY_MONO    = "Courier"

# Font sizes
FONT_SIZE_LABEL_SM = 10
FONT_SIZE_LABEL    = 11
FONT_SIZE_BODY_SM  = 12
FONT_SIZE_BODY     = 13
FONT_SIZE_SUBTITLE = 14
FONT_SIZE_HEADING3 = 16
FONT_SIZE_HEADING2 = 18
FONT_SIZE_HEADING1 = 24

# Font weights
FONT_WEIGHT_NORMAL = "normal"
FONT_WEIGHT_MEDIUM = "500"
FONT_WEIGHT_BOLD   = "bold"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def interpolate_color(color1, color2, t):
    """Linear interpolation between two hex colors. t in [0, 1]."""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten(hex_color, amount=0.15):
    """Lighten a color by interpolating towards white."""
    return interpolate_color(hex_color, "#ffffff", amount)


def darken(hex_color, amount=0.15):
    """Darken a color by interpolating towards black."""
    return interpolate_color(hex_color, "#000000", amount)
