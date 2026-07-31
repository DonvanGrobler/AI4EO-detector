# AI4EO Detector — v0.4

A lightweight public web application that keeps two questions separate:

1. **Image provenance:** guide the user through Gemini's SynthID and Content Credentials check using the screenshot that is actually circulating.
2. **Independent EO context:** compare the broad geographical claim with public Sentinel-2 Level-2A observations from Element 84 Earth Search and AWS Open Data.

The application does not declare a screenshot “real” or “fake.” A positive provenance signal and independent observations provide evidence; missing signals remain inconclusive.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/DonvanGrobler/AI4EO-detector)

## Public hosting

The application includes a FastAPI backend for Earth Search queries and server-side COG rendering, so it cannot run on GitHub Pages alone. The included `render.yaml` and Dockerfile support free deployment on Render:

1. Select **Deploy to Render** above.
2. Sign in to Render and connect this repository.
3. Keep the **Free** instance type.
4. Create the service and use the assigned public `onrender.com` address.

Commits to `main` redeploy automatically. Visitors do not need Render, AWS, Microsoft, Copernicus, or application accounts. Gemini may require its own sign-in for SynthID verification.

Render's free web service can sleep after periods without traffic, so the first request after an idle period may take longer. The interface displays loading feedback while the service finds and prepares imagery.

## Why Element 84 Earth Search

- Public STAC API
- Public HTTPS Cloud-Optimized GeoTIFF assets
- No user account
- No OAuth flow
- No SAS signing
- No CDSE or Microsoft login

The application uses the `sentinel-2-c1-l2a` collection and its ready-made `visual` COG asset.

## User flow

1. Add a screenshot and its accompanying claim.
2. Copy the screenshot, open Gemini, paste it, then return to copy the prepared verification prompt.
3. Paste Gemini's JSON result back into the application.
4. Confirm or correct the extracted location, date, search radius, and cloud limit.
5. Compare before/during/after observations, or the latest acceptable observation when no reliable date exists.
6. Open any returned image in a zoomable, pannable viewer.

## Interface changes in v0.4

- Completed workflow tabs are clickable; future steps remain disabled until reached.
- The Gemini handoff is presented as a guided sequence so the clipboard is not overwritten before the image is pasted.
- Search, preview, and high-resolution viewer loading states explain longer first requests.
- A single returned observation is displayed beside the interpretation panel to use the page width more effectively.
- Internal MVP labels were removed and user-facing text was shortened.
- Light and dark themes are available and remembered in the browser.

## Traffic measurement

Render's dashboard provides service-level request and bandwidth metrics. For visitor-oriented page views and basic audience trends, add a dedicated privacy-conscious web analytics beacon after the public hostname is known. Do not add analytics code without documenting it in the site's privacy information.

## Run locally

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

## Run with Docker

```bash
docker build -t eo-image-check .
docker run --rm -p 8000:8000 eo-image-check
```

## Tests

```bash
pytest -q
```

The unit and interface-structure tests do not require network access. A live integration test requires access to Earth Search, the returned public AWS COG assets, OpenStreetMap tiles, and the Leaflet CDN.

## Privacy

- The screenshot remains in browser memory and is not uploaded to this application.
- It leaves the application only when the user deliberately pastes or uploads it into Gemini.
- No user account or persistent application database is included.
- Confirmed search parameters are sent to the backend and then to Element 84 Earth Search.

## Important limitations

- A detected SynthID signal indicates compatible Google AI involvement; a negative result does not establish authenticity.
- Sentinel-2 visible imagery has 10 m resolution. It can provide context for broad floods, wildfire scars, deforestation, major construction, volcanic plumes, and regional changes, but not individual buildings, vehicles, people, or exact VHR details.
- Cloud filtering currently uses scene-level `eo:cloud_cover`, which may not describe cloud directly over the selected area.
- When no reliable date is found, the application searches transparently for the latest acceptable scene up to the confirmed reference date.
- “No newer acquisition catalogued” may mean that the next intersecting overpass has not occurred or that a recent product is still being processed or catalogued.
- The application selects one STAC item per period; areas spanning several Sentinel-2 tiles remain outside the current scope.
