# Logo

## Adding your logo

Any of these works. Pick whichever is easiest.

**1. Drag and drop (Windows)**
Drag your logo file onto `add_logo.bat` in the project folder. It puts the file
in the right place and tells you it is done.

**2. Copy it here by hand**
Save the file into this folder named `logo.png`. Other formats also work:
`logo.svg`, `logo.jpg`, `logo.jpeg`, `logo.webp`, `logo.gif`.

**3. Command line**
```
python scripts/add_logo.py "C:\path\to\your-logo.png"
```

Then reload the dashboard in the browser. No restart is needed. If the old logo
is still showing, press Ctrl+F5 to clear the browser cache.

## How the dashboard picks the logo

The page asks the server for `/logo`. The server looks in this folder in this
order and serves the first file it finds:

    logo.png -> logo.svg -> logo.jpg -> logo.jpeg -> logo.webp -> logo.gif

If none of those exist, it serves `logo-fallback.svg`, the drawn version that
ships with the project. So the header never shows a broken image.

## What works best

A **PNG with a transparent background**, around 400 to 600 px wide, or an SVG.
A JPG cannot be transparent, so it will show as a white block.

The logo sits on a white plate in the navy header, so dark artwork stays
readable. It is scaled to 34 px tall on a laptop and 25 px on a phone, and the
width adjusts on its own whatever the shape of your file.

`logo-fallback.svg` is only a stand-in. Replace it with the real file.
