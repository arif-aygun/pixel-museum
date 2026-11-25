# Pixel Museum

Every morning, Pixel Museum picks a public-domain painting from the
[Metropolitan Museum of Art](https://www.metmuseum.org/about-the-met/policies-and-documents/open-access),
turns it into 64×64 pixel art with a gold museum frame, and publishes it to GitHub Pages.
A small local script then shows the painting on your Discord profile as a
**"Playing Pixel Museum"** activity card.

**Today's piece:** https://arif-aygun.github.io/pixel-museum/

## How it works

```
pixel_art_of_the_day.py        picks the day's painting and pixelates it into docs/
.github/workflows/daily.yml    runs the script every day at 04:07 UTC and commits the result
docs/index.html                the page that shows today's piece (served by GitHub Pages)
rpc/pixel_museum_rpc.py        Discord Rich Presence; runs on your own computer
```

1. The workflow searches the Met collection API for highlighted paintings. It hashes the date
   to choose one, so every date always maps to the same painting.
2. The image is center-cropped, downsampled to 56×56, reduced to a 16-colour palette without
   dithering, framed, and scaled up 8× to 512×512.
3. The PNG goes to `docs/art/YYYY-MM-DD.png`, and the metadata (title, artist, date, link)
   goes to `docs/today.json`.
4. The Rich Presence script reads `today.json` every 30 minutes and updates your Discord status.

## Run your own

### 1. GitHub Pages

1. Fork this repo, or push a copy of it to a **public** repository.
2. **Settings → Pages**: set Source to *Deploy from a branch*, Branch to `main`,
   and folder to `/docs`.
3. **Actions → pixel-museum-daily → Run workflow** to generate the first piece.
4. After a minute or two, open `https://<your-username>.github.io/<repo-name>/`.

After that, the workflow runs every morning on its own.

### 2. Discord Rich Presence

1. In the [Discord Developer Portal](https://discord.com/developers/applications),
   create an application named **Pixel Museum** and copy its **Application ID**.
   The application's name and icon are what appear on the card.
2. In [`rpc/pixel_museum_rpc.py`](rpc/pixel_museum_rpc.py), set `CLIENT_ID` to that ID
   and `BASE` to your Pages URL.
3. Install the dependencies and run the script while the Discord desktop app is open:
   ```
   pip install pypresence requests
   python rpc/pixel_museum_rpc.py
   ```
4. In Discord, turn on **User Settings → Activity Privacy → Share your detected activities with others**.

The script needs no bot token, only the Application ID. If Discord restarts, the script reconnects on its own.

#### Start with Windows

Press `Win + R`, run `shell:startup`, and create a shortcut in that folder with this target:

```
pythonw "C:\path\to\pixel-museum\rpc\pixel_museum_rpc.py"
```

`pythonw` runs the script in the background, without a console window.

### Try the converter locally

```
pip install pillow requests
python pixel_art_of_the_day.py               # fetch today's painting
python pixel_art_of_the_day.py --local x.jpg # pixelate any local image
```

## Discord profile widget (disabled)

Discord currently doesn't allow new applications to create profile widgets. The workflow
already has an **Update Discord widget** step for when it does. To use it, add the
`DISCORD_APP_ID`, `DISCORD_USER_ID` and `DISCORD_BOT_TOKEN` secrets, then remove the
`if: false` line.

## Notes

- Only public-domain works are used, via the Met's Open Access API.
- Each image file is named after its date, so Discord never shows a stale cached image.
- The Met retired the `v1/search` endpoint on 2026-10-01, so this project uses `v1.1/search`.
