#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Archey GRUB Theme Installer
# Run this from within the installed system (or arch-chroot /mnt)
# ─────────────────────────────────────────────────────────────────────────────
set -e

THEME_DIR="/boot/grub/themes/archey"
GRUB_CFG="/etc/default/grub"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Archey GRUB theme..."

# ── 1. Copy theme files ───────────────────────────────────────────────────────
mkdir -p "$THEME_DIR"
cp -r "$SCRIPT_DIR/archey/"* "$THEME_DIR/"
echo "  Copied theme to $THEME_DIR"

# ── 2. Generate fonts from system fonts ───────────────────────────────────────
echo "  Generating fonts..."

# Prefer Terminus if installed, fall back to DejaVu
if fc-list | grep -qi "terminus"; then
    FONT_REG=$(fc-match "Terminus:style=Regular" --format="%{file}")
    FONT_BOLD=$(fc-match "Terminus:style=Bold"    --format="%{file}")
else
    FONT_REG=$(fc-match "DejaVu Sans Mono:style=Book" --format="%{file}")
    FONT_BOLD=$(fc-match "DejaVu Sans Mono:style=Bold" --format="%{file}")
    echo "  Note: Terminus not found, using DejaVu Sans Mono"
fi

# Generate PF2 fonts at the sizes used in theme.txt
grub-mkfont -s 11 -o "$THEME_DIR/Terminus-11.pf2"  "$FONT_REG"
grub-mkfont -s 12 -o "$THEME_DIR/Terminus-12.pf2"  "$FONT_REG"
grub-mkfont -s 13 -o "$THEME_DIR/Terminus-13.pf2"  "$FONT_REG"
grub-mkfont -s 14 -o "$THEME_DIR/Terminus-14.pf2"  "$FONT_REG"
grub-mkfont -s 16 -o "$THEME_DIR/Terminus-Bold-16.pf2" "$FONT_BOLD"
grub-mkfont -s 24 -o "$THEME_DIR/Terminus-Bold-24.pf2" "$FONT_BOLD"

echo "  Fonts generated"

# ── 3. Update /etc/default/grub ───────────────────────────────────────────────
echo "  Configuring /etc/default/grub..."

# Remove any existing GRUB_THEME line
sed -i '/^GRUB_THEME=/d' "$GRUB_CFG"
sed -i '/^GRUB_BACKGROUND=/d' "$GRUB_CFG"

# Set theme
echo "GRUB_THEME=\"$THEME_DIR/theme.txt\"" >> "$GRUB_CFG"

# Set resolution (change to match your display if needed)
sed -i 's/^#*GRUB_GFXMODE=.*/GRUB_GFXMODE=1920x1080x32,auto/' "$GRUB_CFG"
sed -i 's/^#*GRUB_GFXPAYLOAD_LINUX=.*/GRUB_GFXPAYLOAD_LINUX=keep/' "$GRUB_CFG"

# Remove ugly "quiet splash" if present so errors show in dark rose terminal
# sed -i 's/ quiet//' "$GRUB_CFG"   # uncomment if you want verbose boot

echo "  /etc/default/grub updated"

# ── 4. Regenerate GRUB config ──────────────────────────────────────────────────
echo "  Running grub-mkconfig..."
grub-mkconfig -o /boot/grub/grub.cfg

echo ""
echo "==> Archey GRUB theme installed successfully!"
echo "    Reboot to see it."
