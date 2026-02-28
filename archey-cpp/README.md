# Archey C++ — Build Instructions

## Dependencies (on the build machine)

```bash
sudo pacman -S qt6-base gcc pkg-config
```

## Build

```bash
cd archey-cpp
make
```

Binary is output to `./archey`.

## Deploy to ISO

```bash
# Copy binary to airootfs
cp archey myiso/airootfs/usr/local/bin/archey
chmod +x myiso/airootfs/usr/local/bin/archey

# Add qt6-base to packages.x86_64
echo "qt6-base" >> myiso/packages.x86_64

# Rebuild ISO
sudo mkarchiso -v -w /tmp/archey-work -o /tmp/archey-out myiso/
```

## ISO packages needed

Add to `packages.x86_64`:
```
qt6-base
qt6-svg         # optional, for SVG icons
```

The Python/PyQt6 packages can be removed.

## zlogin

`myiso/airootfs/root/.zlogin`:
```bash
#!/bin/zsh
systemctl start iwd &>/dev/null
xinit /usr/local/bin/archey -- :0 vt1
```

## Verify binary

```bash
file archey
# Should say: ELF 64-bit LSB executable, x86-64, dynamically linked
ldd archey
# Check libQt6Widgets.so.6 and libQt6Core.so.6 are present on the ISO
```
