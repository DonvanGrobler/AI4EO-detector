function clampViewerScale(value) {
  return Math.min(8, Math.max(1, value));
}

function applyViewerTransform() {
  const image = byId("viewer-image");
  image.style.transform = `translate3d(${state.viewer.x}px, ${state.viewer.y}px, 0) scale(${state.viewer.scale})`;
  byId("viewer-viewport").classList.toggle("can-pan", state.viewer.scale > 1);
}

function resetImageViewer() {
  state.viewer.scale = 1;
  state.viewer.x = 0;
  state.viewer.y = 0;
  applyViewerTransform();
}

function zoomImageViewer(multiplier) {
  state.viewer.scale = clampViewerScale(state.viewer.scale * multiplier);
  if (state.viewer.scale === 1) {
    state.viewer.x = 0;
    state.viewer.y = 0;
  }
  applyViewerTransform();
}

function openImageViewer(src, title) {
  const viewer = byId("image-viewer");
  byId("viewer-title").textContent = title || "Interactive image view";
  byId("viewer-image").src = src;
  viewer.classList.remove("hidden");
  document.body.classList.add("viewer-open");
  resetImageViewer();
  window.setTimeout(() => byId("viewer-viewport").focus(), 0);
}

function closeImageViewer() {
  byId("image-viewer").classList.add("hidden");
  byId("viewer-image").removeAttribute("src");
  document.body.classList.remove("viewer-open");
  resetImageViewer();
}

async function copyImageToClipboard() {
  if (!state.imageFile) throw new Error("No image is available.");
  if (!navigator.clipboard || !window.ClipboardItem) throw new Error("This browser cannot copy images directly. Upload the original image in Gemini instead.");
  const bitmap = await createImageBitmap(state.imageFile);
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(bitmap, 0, 0);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
}

async function runSearch() {
  const dateMode = byId("date-mode").value;
  const payload = {
    latitude: Number(byId("latitude").value),
    longitude: Number(byId("longitude").value),
    date_mode: dateMode,
    radius_km: Number(byId("radius-km").value),
    cloud_cover: Number(byId("cloud-cover").value),
    window_days: Number(byId("window-days").value),
  };
  if (dateMode === "latest_available") {
    payload.reference_date = byId("reference-date").value || todayLocalIso();
  } else {
    payload.start_date = byId("start-date").value;
    payload.end_date = byId("end-date").value || payload.start_date;
  }

  if (!Number.isFinite(payload.latitude) || !Number.isFinite(payload.longitude)) {
    throw new Error("Confirm the location coordinates before searching.");
  }
  if (dateMode === "claimed_period" && (!payload.start_date || !payload.end_date)) {
    throw new Error("Confirm the claim date, or switch to latest available observation.");
  }
  if (dateMode === "latest_available" && !payload.reference_date) {
    throw new Error("Confirm the latest-search reference date.");
  }

  const button = byId("run-search");
  button.disabled = true;
  button.textContent = "Searching…";
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Sentinel-2 search failed.");
    const dateLabel = dateMode === "latest_available"
      ? `latest available up to ${payload.reference_date}`
      : `${payload.start_date} to ${payload.end_date}`;
    byId("results-location").textContent = `${byId("location-name").value || `${payload.latitude}, ${payload.longitude}`} · ${dateLabel}`;
    renderResults(data);
    goToStep(4);
  } finally {
    button.disabled = false;
    button.textContent = "Search public Sentinel‑2";
  }
}
