function initMap() {
  state.map = L.map("map", { zoomControl: true, preferCanvas: true }).setView([20, 0], 2);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
    detectRetina: true,
  }).addTo(state.map);
  state.map.on("click", (event) => updateMapLocation(event.latlng.lat, event.latlng.lng, false));

  if (window.ResizeObserver) {
    const observer = new ResizeObserver(() => state.map?.invalidateSize({ pan: false }));
    observer.observe(byId("map"));
  }
}

function updateMapLocation(lat, lon, zoom) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
  byId("latitude").value = lat.toFixed(6);
  byId("longitude").value = lon.toFixed(6);
  if (!state.marker) state.marker = L.marker([lat, lon]).addTo(state.map);
  else state.marker.setLatLng([lat, lon]);
  updateAoiCircle();
  if (zoom && state.aoiCircle) {
    state.map.fitBounds(state.aoiCircle.getBounds(), { padding: [28, 28], maxZoom: 13, animate: false });
  }
}

function updateAoiCircle() {
  const lat = Number(byId("latitude").value);
  const lon = Number(byId("longitude").value);
  const radiusKm = Number(byId("radius-km").value || 5);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
  if (!state.aoiCircle) state.aoiCircle = L.circle([lat, lon], { radius: radiusKm * 1000, weight: 2 }).addTo(state.map);
  else state.aoiCircle.setLatLng([lat, lon]).setRadius(radiusKm * 1000);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function resultCard(period) {
  const title = period.period === "latest"
    ? "Latest acceptable observation"
    : period.period.charAt(0).toUpperCase() + period.period.slice(1);
  if (!period.scene) {
    return `<article class="result-card"><header><h3>${escapeHtml(title)}</h3></header><div class="empty-result"><div><p>${escapeHtml(period.message || "No observation found.")}</p><p>${escapeHtml(period.recency_explanation || "")}</p></div></div></article>`;
  }
  const scene = period.scene;
  const cloud = scene.cloud_cover == null ? "Unknown" : `${Number(scene.cloud_cover).toFixed(1)}%`;
  const coverage = `${Math.round(scene.coverage_fraction * 100)}%`;
  const latestCatalogued = period.latest_catalogued_datetime ? period.latest_catalogued_datetime.slice(0, 10) : "Unknown";
  const viewerUrl = `${scene.preview_url}&max_size=1800`;
  return `<article class="result-card">
    <header><h3>${escapeHtml(title)}</h3><span>${escapeHtml(scene.datetime.slice(0, 10))}</span></header>
    <button class="result-image-button" type="button" data-image-src="${escapeHtml(viewerUrl)}" data-image-title="${escapeHtml(`${title} · ${scene.datetime.slice(0, 10)}`)}" aria-label="Open ${escapeHtml(title)} in zoomable viewer">
      <img src="${escapeHtml(scene.preview_url)}" alt="${escapeHtml(title)} Sentinel-2 observation" loading="lazy" />
      <span class="zoom-hint">Zoom and pan</span>
    </button>
    <div class="result-meta">
      <dl>
        <dt>Returned date</dt><dd>${escapeHtml(scene.datetime.slice(0, 10))}</dd>
        <dt>Target date</dt><dd>${escapeHtml(scene.target_date)}</dd>
        <dt>Date difference</dt><dd>${scene.date_distance_days} day(s)</dd>
        <dt>Cloud cover</dt><dd>${cloud}</dd>
        <dt>AOI coverage</dt><dd>${coverage}</dd>
        <dt>Latest catalogued</dt><dd>${escapeHtml(latestCatalogued)}</dd>
        <dt>Platform</dt><dd>${escapeHtml(scene.platform || "Sentinel-2")}</dd>
      </dl>
      <div class="result-reason"><strong>Why this scene?</strong><br>${escapeHtml(scene.selection_reason)}<br><br><strong>Why not closer/newer?</strong><br>${escapeHtml(period.recency_explanation || "No additional diagnostic was available.")}</div>
      <p><a href="${escapeHtml(scene.item_url)}" target="_blank" rel="noopener">View STAC record</a></p>
    </div>
  </article>`;
}

function renderResults(data) {
  state.lastSearch = data;
  byId("resolution-notice").textContent = data.resolution_notice;
  byId("cloud-notice").textContent = data.cloud_notice;
  const resultGrid = byId("result-grid");
  resultGrid.classList.toggle("single", data.periods.length === 1);
  resultGrid.innerHTML = data.periods.map(resultCard).join("");
  resultGrid.querySelectorAll(".result-image-button").forEach((button) => {
    button.addEventListener("click", () => openImageViewer(button.dataset.imageSrc, button.dataset.imageTitle));
  });
  const synth = state.gemini?.verification?.synthid;
  const synthText = synth === "detected"
    ? "Gemini reported SynthID. This is evidence that Google AI generated or edited at least part of the screenshot."
    : synth === "not_detected"
      ? "Gemini did not report SynthID. This is not proof that the screenshot is authentic or non-AI."
      : "The Google AI provenance check was inconclusive.";
  const temporalText = data.date_mode === "latest_available"
    ? "Because no reliable claim date was available, the EO check searched backwards from the confirmed reference date and returned the newest scene meeting the selected scene-cloud threshold."
    : "The EO check searched for the closest acceptable observations around the user-confirmed claim period.";
  byId("interpretation").innerHTML = `<p>${escapeHtml(synthText)}</p><p>${escapeHtml(temporalText)}</p><p>The Sentinel‑2 panels independently show broad conditions near the confirmed location and dates. Compare landscape-scale features only; do not use them to authenticate small objects or exact VHR pixels.</p>`;
}
