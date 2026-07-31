# EO Image Check

A lightweight verification helper for screenshots of satellite, aerial, and map imagery.

It keeps two questions separate:

1. **Was Google AI involved in creating or editing the screenshot?** The application guides the user through Gemini's SynthID and Content Credentials check.
2. **Does independent Earth-observation data support the broad geographical claim?** The application retrieves public Sentinel-2 observations through Element 84 Earth Search and AWS Open Data.

> [!IMPORTANT]
> **Project status: experimental public prototype.** Results may be incomplete or inconclusive and must not be treated as a professional fact-checking determination, proof of authenticity, or confirmation that a depicted event occurred.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/DonvanGrobler/AI4EO-detector)

## What the tool does

- Accepts a pasted, dropped, or uploaded screenshot together with its accompanying post, caption, or article text.
- Prepares a structured Gemini prompt for checking SynthID, Content Credentials, visible place names, dates, and the broad claim.
- Lets the user confirm or correct the extracted location, date, search radius, and cloud limit.
- Searches public Sentinel-2 Level-2A observations before, during, and after a claimed date.
- Uses the latest acceptable observation when no reliable date is available.
- Explains when a newer or closer observation was rejected because of scene-level cloud cover.
- Displays returned imagery in a zoomable and pannable viewer.
- Keeps the screenshot in browser memory rather than uploading it to the application backend.

## What the tool does not do

- It does not provide a universal AI-image detector.
- It does not declare an image simply “real” or “fake.”
- A negative SynthID result does not prove that an image is authentic or that another AI system was not used.
- Sentinel-2 cannot authenticate the exact pixels or fine details of a very-high-resolution screenshot.
- It cannot reliably verify individual buildings, vehicles, people, or other details below Sentinel-2's effective resolution.
- Independent satellite observations may support or contradict a broad claim without proving that the circulated screenshot itself is genuine.

## How it works

1. Add a screenshot and any related text.
2. Copy the screenshot and open Gemini in a separate tab.
3. Paste the screenshot into Gemini, return to the application, and copy the prepared verification prompt.
4. Paste Gemini's structured JSON response back into the application.
5. Confirm the extracted location, date, search radius, and cloud threshold.
6. Compare public Sentinel-2 observations and read the accompanying limitations.

The Gemini handoff is currently manual because this application does not control or read a user's personal Gemini session.

## Current features

- Guided four-step workflow with completed-step navigation
- Screenshot drag-and-drop, file selection, and clipboard paste
- Prompt-injection-resistant handling of accompanying text as untrusted evidence
- Extraction of location clues from both text and readable labels inside the screenshot
- Explicit fallback to a latest-available search when no reliable date is present
- Public STAC search through Element 84 Earth Search
- Public HTTPS Cloud-Optimized GeoTIFF access through AWS Open Data
- Before, during, and after comparisons for dated claims
- Diagnostic explanations for cloud-related scene rejection
- Loading feedback for searches and imagery rendering
- Zoomable and pannable Sentinel-2 viewer
- Responsive layout and light/dark themes
- No application user accounts or persistent database

## Why Element 84 Earth Search

The application uses the `sentinel-2-c1-l2a` collection and its ready-made `visual` Cloud-Optimized GeoTIFF asset.

This provides:

- A public STAC API
- Public HTTPS imagery assets
- No end-user account
- No OAuth flow
- No SAS signing
- No Copernicus Data Space or Microsoft login

## Privacy

- The screenshot remains in browser memory and is not uploaded to this application's backend.
- It leaves the application only when the user deliberately pastes or uploads it into Gemini.
- No user account or persistent application database is included.
- Confirmed search parameters are sent to the application backend and then to Element 84 Earth Search.
- Do not submit private, sensitive, or personally identifying imagery unless you understand the implications of sending it to the external services involved.

Any future visitor analytics should be documented here before being enabled.

## Limitations

- SynthID detection indicates compatible Google AI involvement when detected; a missing signal remains inconclusive.
- Sentinel-2 visible imagery has 10 m spatial resolution and is most useful for broad floods, wildfire scars, deforestation, volcanic plumes, major construction, and regional land change.
- Cloud filtering currently uses scene-level `eo:cloud_cover`, which may not describe cloud directly over the selected area.
- The latest catalogued observation may lag behind the present because the next intersecting overpass has not occurred or a recent product is still being processed or catalogued.
- The application selects one STAC item per comparison period. Areas spanning several Sentinel-2 tiles remain outside the current scope.
- Earth Search and the public imagery hosts are external best-effort services without an availability guarantee from this project.
- Gemini's output must be reviewed by the user and may contain extraction or geolocation errors.

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

Open `http://localhost:8000`.

## Tests

```bash
pytest -q
```

The unit and interface-structure tests do not require network access. A live integration test requires access to:

- Element 84 Earth Search
- The public AWS COG assets returned by Earth Search
- OpenStreetMap tiles
- The Leaflet CDN

## Deploy on Render

The project includes a `render.yaml` Blueprint and a Dockerfile because the FastAPI and Rasterio backend cannot run on GitHub Pages alone.

1. Select **Deploy to Render** near the top of this README.
2. Sign in to Render and connect this repository.
3. Keep the **Free** instance type.
4. Create the service.
5. Use the assigned public `onrender.com` address.

Commits to `main` trigger automatic redeployment. Free Render services can sleep after periods without traffic, so the first request after an idle period may take longer.

Visitors do not need Render, AWS, Microsoft, Copernicus, or application accounts. Gemini may require its own sign-in for SynthID verification.

## Licence and external data

The source code in this repository is available under the [MIT License](LICENSE).

That licence applies to the repository code only. Sentinel-2 imagery, Earth Search catalogue records, AWS-hosted assets, OpenStreetMap tiles, Gemini outputs, Google services, and other third-party materials remain subject to their respective providers' terms, licences, and attribution requirements. This repository does not relicense those materials.

## Acknowledgements and independence

The project uses or interacts with services and data provided by Google, Element 84, AWS Open Data, the Copernicus Programme, ESA, and OpenStreetMap contributors.

This is an independent open-source project. It is not affiliated with, sponsored by, or endorsed by Google, Element 84, Amazon Web Services, Microsoft, the European Commission, ESA, or the Copernicus Programme.

## Reporting problems

Open a GitHub issue for reproducible bugs, failed searches, unclear results, accessibility problems, or suggestions.

Do not post private, sensitive, personally identifying, or operationally sensitive imagery in a public issue. Provide a redacted example or a clear written reproduction where possible.
