# AI4EO Detector — MVP v0.3

A lightweight, transparent web application for two separate checks:

1. **Google AI provenance:** guide the user through Gemini's SynthID / Content Credentials verification using the screenshot that is actually circulating.
2. **Independent EO corroboration:** search public Sentinel-2 Level-2A observations through Element 84 Earth Search and stream public Cloud-Optimized GeoTIFFs from AWS Open Data.

The application deliberately does **not** claim that a screenshot is “real” or “fake.” It separates image provenance from whether a broad geographical claim is independently observable.


[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/DonvanGrobler/AI4EO-detector)

## Public hosting

The current MVP includes a FastAPI backend for Earth Search queries and server-side COG rendering, so it cannot run directly on GitHub Pages, which only serves static HTML, CSS and JavaScript. The included `render.yaml` and Dockerfile provide a free public deployment on Render:

1. Select **Deploy to Render** above.
2. Sign in to Render and connect the GitHub repository when asked.
3. Keep the **Free** instance type and create the service.
4. Render assigns a public `onrender.com` address and redeploys automatically after commits to `main`.

Visitors do not need a Render, AWS, Microsoft or Copernicus account. The only possible user sign-in remains the temporary Gemini step for SynthID verification.

Render's free web service sleeps after 15 minutes without traffic, so the first visit after an idle period can take about a minute to start. This is suitable for the MVP and blog demonstration, but not a production service with guaranteed availability.

## Why Element 84 Earth Search

- Public STAC API
- Public HTTPS COG assets
- No user account
- No OAuth flow
- No SAS signing
- No CDSE or Microsoft login

The MVP uses collection `sentinel-2-c1-l2a` and its ready-made `visual` COG asset.

## User flow

1. Paste or drag a screenshot into the app and paste the accompanying claim.
2. Copy the image and a prepared prompt into Gemini.
3. Paste Gemini's JSON result back into the app. Gemini is prompted to inspect both the accompanying text and readable labels inside the image.
4. Confirm or correct the extracted location, date mode and AOI on a map.
5. If a date is present, search for the closest acceptable observations before, during and after it. If no reliable date is present, search for the latest acceptable observation.
6. Review the returned acquisition date and an explanation of whether a closer/newer scene was rejected for cloud cover or is not yet catalogued.

## Run locally

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000` for local development. The public deployment uses the Render URL.

## Run with Docker

```bash
docker build -t eo-image-check .
docker run --rm -p 8000:8000 eo-image-check
```

Open `http://localhost:8000` for local Docker testing.

## Tests

```bash
pytest -q
```

The unit tests do not require network access. A live integration test must be run in an environment with access to:

- `https://earth-search.aws.element84.com`
- the public AWS COG hosts returned by Earth Search
- OpenStreetMap tiles and Leaflet CDN assets in the browser

## Privacy

- The screenshot is held in browser memory and is not uploaded to this application.
- It is sent outside the app only when the user manually pastes/uploads it into Gemini.
- No user accounts or persistent database are included.
- Search parameters are sent to the local app backend and then to Element 84 Earth Search.

## Important limitations

- SynthID detection only establishes compatible Google AI involvement when detected.
- A negative SynthID result does not establish authenticity.
- Sentinel-2's visible bands have 10 m resolution. The comparison is suitable for broad floods, wildfire scars, deforestation, large construction or regional land change—not individual buildings, vehicles, people or fine VHR details.
- Earth Search is a free best-effort public service without a production SLA.
- Cloud filtering uses scene-level `eo:cloud_cover`, which may not exactly describe cloud over the user-defined AOI. The rendered image must still be inspected.
- When no reliable date is found, the app defaults transparently to a latest-available search up to the user-confirmed reference date.
- The app explains “no newer acquisition catalogued” cautiously: the next intersecting overpass may not yet have occurred, or a recent product may still be processing/cataloguing. It does not calculate an exact future overpass time.
- The app chooses one STAC item per period. AOIs spanning several Sentinel-2 tiles are intentionally outside the MVP boundary.

## Suggested first test

Use a documented, landscape-scale event and prepare:

- one original Google Earth screenshot,
- one generated Google Earth screenshot,
- one cropped/recompressed version of the generated screenshot,
- the same accompanying claim text.

Record whether Gemini reports SynthID and whether the before/during/after Sentinel-2 observations provide useful independent context. Publish failures and inconclusive results as well as successful checks.



## Interface improvements in v0.3

- Fixed the broken Leaflet tile layout by replacing the incorrect Leaflet 1.9.4 stylesheet integrity hash with the official value. The app also invalidates the map size after Step 3 becomes visible and whenever its container changes size.
- Shortened Step 3 by using a compact provenance strip, combining coordinate and AOI fields, collapsing detailed extraction evidence, and reducing the map to a 390 px desktop height.
- Added a full-screen Sentinel-2 image viewer. Click any result image to open it, then use the mouse wheel or +/− controls to zoom and drag to pan. Double-click or press Reset to return to the fitted view.
- The result cards still request a lightweight 900 px preview, while the interactive viewer requests an 1800 px version. The API validates output sizes between 256 and 2048 px.

## Edge-case handling added in v0.2

- Gemini is explicitly instructed to read place names, map labels, coordinates, pins and date stamps inside the screenshot.
- The structured result records location source, evidence and confidence for human confirmation.
- Missing or merely relative dates such as “current” switch the UI to `latest_available` mode rather than inventing a date.
- Searches retain cloudy STAC items for diagnostics, then apply the user threshold locally. This lets the result explain when a newer or closer acquisition exists but was rejected for cloud cover.
- Every returned panel states its actual acquisition date, target date, date difference, latest catalogued date and selection reason.
