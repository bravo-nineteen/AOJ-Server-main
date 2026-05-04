# Installer Branding Assets

Place Airsoft Online Japan branding files in this folder.

Required for custom icon branding:

- `aoj_icon.ico` : Windows icon file used by Inno Setup and uninstaller.

Recommended source workflow:

1. Start from your AOJ logo image.
2. Export an `.ico` file containing at least these sizes: 16x16, 32x32, 48x48, 256x256.
3. Save as `installer/assets/aoj_icon.ico`.

Notes:

- The installer script already references this path.
- If the icon file is missing, the install still works but Windows uses a default icon.
