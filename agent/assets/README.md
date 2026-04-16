# Agent assets

`icon.ico` should be a 16×16 + 32×32 multi-resolution Windows icon used
by PyInstaller (`--icon`) and picked up by `agent/tray.py` at runtime.

No icon is checked in yet — the tray generates a 64×64 solid blue
placeholder with Pillow until we drop in real artwork.
