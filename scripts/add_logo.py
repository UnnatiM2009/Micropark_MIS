"""
Put a logo into the dashboard.

    python scripts/add_logo.py "C:\\Users\\you\\Downloads\\micropark-logo.png"

Or, on Windows, just drag the logo file onto add_logo.bat.

It copies the file into app/static/img/ with the right name, clears out any
older logo, and confirms what it did. Reload the dashboard in the browser and
the new logo is there. No restart needed.
"""

import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app.branding import ACCEPTED, IMG_DIR, PREFERRED  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("No file given. Drag your logo onto add_logo.bat, or pass the path.")
        return 1

    source = Path(" ".join(sys.argv[1:]).strip().strip('"'))

    if not source.exists():
        print(f"\nCould not find that file:\n  {source}\n")
        return 1

    suffix = source.suffix.lower()
    if suffix not in ACCEPTED:
        print(f"\n{suffix or 'That file'} is not an image the browser can show.")
        print("Use one of: " + ", ".join(ACCEPTED))
        return 1

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # remove any logo already installed, so the new one is the one that wins
    for name in PREFERRED:
        old = IMG_DIR / name
        if old.exists():
            old.unlink()
            print(f"Removed the previous {name}")

    target = IMG_DIR / f"logo{suffix}"
    shutil.copyfile(source, target)

    size_kb = target.stat().st_size / 1024
    print(f"\nInstalled: {target.name}  ({size_kb:.0f} KB)")
    print(f"Location : {target}")
    print("\nReload the dashboard in your browser and the logo will be there.")
    print("If it still looks like the old one, press Ctrl+F5 to clear the cache.")

    if suffix in (".jpg", ".jpeg"):
        print("\nNote: a JPG cannot have a transparent background, so the logo")
        print("will sit on a white block. A PNG or SVG looks cleaner.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
