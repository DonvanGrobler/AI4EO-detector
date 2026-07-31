/* v0.4 UI enhancements. Loaded after the core application scripts. */
state.maxStepReached = 1;
state.currentStep = 1;

function updateStepTabs(currentStep) {
  document.querySelectorAll(".step-tab").forEach((tab) => {
    const step = Number(tab.dataset.step);
    const available = step <= state.maxStepReached;
    tab.disabled = !available && step !== currentStep;
    tab.classList.toggle("active", step === currentStep);
    tab.classList.toggle("completed", available && step < state.maxStepReached && step !== currentStep);
    if (step === currentStep) tab.setAttribute("aria-current", "step");
    else tab.removeAttribute("aria-current");
  });
}

function displayStep(step, unlock = true) {
  if (unlock) state.maxStepReached = Math.max(state.maxStepReached, step);
  state.currentStep = step;
  document.querySelectorAll(".step-panel").forEach((panel) => panel.classList.remove("active"));
  byId(`step-${step}`).classList.add("active");
  updateStepTabs(step);
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (step === 3) {
    refreshClaimMap();
    window.setTimeout(refreshClaimMap, 250);
  }
}

goToStep = function goToStepV04(step) {
  const requested = Number(step);
  if (!Number.isInteger(requested) || requested < 1 || requested > 4) return;
  if (requested > state.maxStepReached + 1) return;
  displayStep(requested, true);
};

document.querySelectorAll(".step-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const step = Number(tab.dataset.step);
    if (step <= state.maxStepReached) displayStep(step, false);
  });
});

function setHandoffCard(id, status) {
  const card = byId(id);
  card.classList.toggle("locked", status === "locked");
  card.classList.toggle("current", status === "current");
  card.classList.toggle("completed", status === "completed");
}

function resetHandoffFlow() {
  setHandoffCard("handoff-copy-image", "current");
  setHandoffCard("handoff-open-gemini", "locked");
  setHandoffCard("handoff-copy-prompt", "locked");
  setHandoffCard("handoff-finish", "locked");
  byId("open-gemini").disabled = true;
  byId("copy-prompt").disabled = true;
  byId("copy-image").textContent = "Copy image";
  byId("copy-prompt").textContent = "Copy prompt";
}

byId("prepare-check").addEventListener("click", () => {
  if (state.imageFile) resetHandoffFlow();
});

byId("copy-image").addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopImmediatePropagation();
  try {
    await copyImageToClipboard();
    showToast("Image copied. Open Gemini and paste it there.");
    byId("copy-image").textContent = "Image copied";
  } catch (error) {
    showToast(`${error.message} You can upload the image manually in Gemini.`, true);
    byId("copy-image").textContent = "Upload manually";
  }
  setHandoffCard("handoff-copy-image", "completed");
  setHandoffCard("handoff-open-gemini", "current");
  byId("open-gemini").disabled = false;
}, true);

byId("open-gemini").addEventListener("click", () => {
  const geminiWindow = window.open("https://gemini.google.com/app", "_blank");
  if (!geminiWindow) {
    showToast("Your browser blocked the Gemini tab. Allow pop-ups and try again.", true);
    return;
  }
  geminiWindow.opener = null;
  setHandoffCard("handoff-open-gemini", "completed");
  setHandoffCard("handoff-copy-prompt", "current");
  byId("copy-prompt").disabled = false;
});

byId("copy-prompt").addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopImmediatePropagation();
  try {
    await navigator.clipboard.writeText(state.prompt);
    showToast("Prompt copied. Return to Gemini and paste it after the image.");
    byId("copy-prompt").textContent = "Prompt copied";
  } catch (_) {
    showToast("Clipboard access was blocked. Open the prepared prompt below and copy it manually.", true);
    byId("copy-prompt").textContent = "Copy manually below";
  }
  setHandoffCard("handoff-copy-prompt", "completed");
  setHandoffCard("handoff-finish", "current");
}, true);

function applyTheme(theme) {
  const selected = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = selected;
  localStorage.setItem("eo-image-check-theme", selected);
  const toggle = byId("theme-toggle");
  toggle.textContent = selected === "dark" ? "Light mode" : "Dark mode";
  toggle.setAttribute("aria-label", selected === "dark" ? "Switch to light mode" : "Switch to dark mode");
}

byId("theme-toggle").addEventListener("click", () => {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});
applyTheme(document.documentElement.dataset.theme);

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
      <div class="image-loading" role="status"><span class="spinner" aria-hidden="true"></span><span>Preparing preview…</span></div>
      <img class="result-preview" src="${escapeHtml(scene.preview_url)}" alt="${escapeHtml(title)} Sentinel-2 observation" loading="eager" />
      <span class="zoom-hint">Zoom and pan</span>
    </button>
    <div class="result-meta">
      <dl>
        <dt>Observation date</dt><dd>${escapeHtml(scene.datetime.slice(0, 10))}</dd>
        <dt>Date checked</dt><dd>${escapeHtml(scene.target_date)}</dd>
        <dt>Date difference</dt><dd>${scene.date_distance_days} day(s)</dd>
        <dt>Scene cloud</dt><dd>${cloud}</dd>
        <dt>Area coverage</dt><dd>${coverage}</dd>
        <dt>Latest catalogued</dt><dd>${escapeHtml(latestCatalogued)}</dd>
        <dt>Satellite</dt><dd>${escapeHtml(scene.platform || "Sentinel-2")}</dd>
      </dl>
      <div class="result-reason"><strong>Why this observation?</strong><br>${escapeHtml(scene.selection_reason)}<br><br><strong>Why not a closer or newer one?</strong><br>${escapeHtml(period.recency_explanation || "No additional information was available.")}</div>
      <p><a href="${escapeHtml(scene.item_url)}" target="_blank" rel="noopener">View source details</a></p>
    </div>
  </article>`;
}

function activatePreviewLoading(resultGrid) {
  resultGrid.querySelectorAll(".result-image-button").forEach((button) => {
    const image = button.querySelector("img");
    const markLoaded = () => button.classList.add("is-loaded");
    const markError = () => {
      button.classList.add("is-error");
      const label = button.querySelector(".image-loading span:last-child");
      if (label) label.textContent = "Preview could not be prepared.";
    };
    image.addEventListener("load", markLoaded, { once: true });
    image.addEventListener("error", markError, { once: true });
    if (image.complete) {
      if (image.naturalWidth > 0) markLoaded();
      else markError();
    }
    button.addEventListener("click", () => openImageViewer(button.dataset.imageSrc, button.dataset.imageTitle));
  });
}

renderResults = function renderResultsV04(data) {
  state.lastSearch = data;
  byId("resolution-notice").textContent = data.resolution_notice;
  byId("cloud-notice").textContent = data.cloud_notice;
  const resultGrid = byId("result-grid");
  resultGrid.classList.toggle("single", data.periods.length === 1);
  byId("results-layout").classList.toggle("single-result", data.periods.length === 1);
  resultGrid.innerHTML = data.periods.map(resultCard).join("");
  activatePreviewLoading(resultGrid);

  const synth = state.gemini?.verification?.synthid;
  const synthText = synth === "detected"
    ? "Gemini reported SynthID, which indicates that Google AI generated or edited at least part of the screenshot."
    : synth === "not_detected"
      ? "Gemini did not report SynthID. This does not prove that the screenshot is authentic or non-AI."
      : "The Google AI provenance check was inconclusive.";
  const temporalText = data.date_mode === "latest_available"
    ? "No reliable date was available, so the search returned the newest observation that met the selected scene-cloud limit."
    : "The search returned the closest suitable observations around the date you confirmed.";
  byId("interpretation").innerHTML = `<p>${escapeHtml(synthText)}</p><p>${escapeHtml(temporalText)}</p><p>Use the Sentinel‑2 images to compare broad landscape conditions only. They cannot verify small objects or exact details in a very-high-resolution screenshot.</p>`;
};

openImageViewer = function openImageViewerV04(src, title) {
  const viewer = byId("image-viewer");
  const image = byId("viewer-image");
  const loading = byId("viewer-loading");
  byId("viewer-title").textContent = title || "Interactive image view";
  loading.classList.remove("hidden");
  loading.querySelector(".spinner")?.classList.remove("hidden");
  loading.querySelector("span:last-child").textContent = "Preparing the larger image…";
  image.classList.remove("is-loaded");
  image.onload = () => {
    loading.classList.add("hidden");
    image.classList.add("is-loaded");
  };
  image.onerror = () => {
    loading.querySelector(".spinner")?.classList.add("hidden");
    loading.querySelector("span:last-child").textContent = "The larger image could not be prepared.";
  };
  image.src = src;
  viewer.classList.remove("hidden");
  document.body.classList.add("viewer-open");
  resetImageViewer();
  window.setTimeout(() => byId("viewer-viewport").focus(), 0);
};

function buildSearchPayload() {
  const dateMode = byId("date-mode").value;
  const payload = {
    latitude: Number(byId("latitude").value),
    longitude: Number(byId("longitude").value),
    date_mode: dateMode,
    radius_km: Number(byId("radius-km").value),
    cloud_cover: Number(byId("cloud-cover").value),
    window_days: Number(byId("window-days").value),
  };
  if (dateMode === "latest_available") payload.reference_date = byId("reference-date").value || todayLocalIso();
  else {
    payload.start_date = byId("start-date").value;
    payload.end_date = byId("end-date").value || payload.start_date;
  }
  if (!Number.isFinite(payload.latitude) || !Number.isFinite(payload.longitude)) throw new Error("Confirm the location coordinates before searching.");
  if (dateMode === "claimed_period" && (!payload.start_date || !payload.end_date)) throw new Error("Confirm the date, or choose the latest available observation.");
  if (dateMode === "latest_available" && !payload.reference_date) throw new Error("Confirm the latest date to search up to.");
  return payload;
}

runSearch = async function runSearchV04() {
  const payload = buildSearchPayload();
  const dateMode = payload.date_mode;
  const dateLabel = dateMode === "latest_available"
    ? `latest available up to ${payload.reference_date}`
    : `${payload.start_date} to ${payload.end_date}`;
  byId("results-location").textContent = `${byId("location-name").value || `${payload.latitude}, ${payload.longitude}`} · ${dateLabel}`;

  const button = byId("run-search");
  button.disabled = true;
  button.textContent = "Finding observations…";
  byId("results-content").classList.add("hidden");
  byId("search-loading").classList.remove("hidden");
  displayStep(4, false);

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "The Sentinel-2 search could not be completed.");
    renderResults(data);
    byId("search-loading").classList.add("hidden");
    byId("results-content").classList.remove("hidden");
    state.maxStepReached = Math.max(state.maxStepReached, 4);
    updateStepTabs(4);
  } catch (error) {
    byId("search-loading").classList.add("hidden");
    state.maxStepReached = Math.min(state.maxStepReached, 3);
    displayStep(3, false);
    throw error;
  } finally {
    button.disabled = false;
    button.textContent = "Compare with Sentinel‑2";
  }
};

updateStepTabs(1);
resetHandoffFlow();
