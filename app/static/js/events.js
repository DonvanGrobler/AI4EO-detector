byId("drop-zone").addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") byId("image-input").click();
});
byId("image-input").addEventListener("change", (event) => setImage(event.target.files[0]));
byId("remove-image").addEventListener("click", clearImage);
["dragenter", "dragover"].forEach((name) => byId("drop-zone").addEventListener(name, (event) => {
  event.preventDefault();
  byId("drop-zone").classList.add("dragging");
}));
["dragleave", "drop"].forEach((name) => byId("drop-zone").addEventListener(name, (event) => {
  event.preventDefault();
  byId("drop-zone").classList.remove("dragging");
}));
byId("drop-zone").addEventListener("drop", (event) => setImage(event.dataTransfer.files[0]));
window.addEventListener("paste", (event) => {
  const imageItem = [...(event.clipboardData?.items || [])].find((item) => item.type.startsWith("image/"));
  if (imageItem && byId("step-1").classList.contains("active")) setImage(imageItem.getAsFile());
});

byId("prepare-check").addEventListener("click", () => {
  if (!state.imageFile) return showToast("Add an image before continuing.", true);
  state.prompt = buildGeminiPrompt(byId("claim-text").value.trim());
  byId("prepared-prompt").textContent = state.prompt;
  goToStep(2);
});
byId("copy-prompt").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(state.prompt); showToast("Prompt copied."); }
  catch { showToast("Could not copy the prompt. Select it manually below.", true); }
});
byId("copy-image").addEventListener("click", async () => {
  try { await copyImageToClipboard(); showToast("Image copied."); }
  catch (error) { showToast(error.message, true); }
});
byId("parse-result").addEventListener("click", () => {
  try {
    state.gemini = validateGeminiResult(parseGeminiJson(byId("gemini-result").value));
    renderVerificationSummary(state.gemini);
    populateClaim(state.gemini);
    goToStep(3);
  } catch (error) {
    showToast(error.message, true);
  }
});
byId("date-mode").addEventListener("change", (event) => setDateMode(event.target.value, false));
byId("latitude").addEventListener("change", () => updateMapLocation(Number(byId("latitude").value), Number(byId("longitude").value), false));
byId("longitude").addEventListener("change", () => updateMapLocation(Number(byId("latitude").value), Number(byId("longitude").value), false));
byId("radius-km").addEventListener("input", () => {
  updateAoiCircle();
  if (byId("step-3").classList.contains("active") && state.aoiCircle) {
    state.map.fitBounds(state.aoiCircle.getBounds(), { padding: [28, 28], maxZoom: 13, animate: false });
  }
});
byId("run-search").addEventListener("click", async () => {
  try { await runSearch(); } catch (error) { showToast(error.message, true); }
});

byId("back-to-one").addEventListener("click", () => goToStep(1));
byId("back-to-two").addEventListener("click", () => goToStep(2));
byId("back-to-three").addEventListener("click", () => goToStep(3));
byId("start-over").addEventListener("click", () => window.location.reload());

byId("viewer-close").addEventListener("click", closeImageViewer);
document.querySelectorAll("[data-viewer-close]").forEach((element) => element.addEventListener("click", closeImageViewer));
byId("viewer-zoom-in").addEventListener("click", () => zoomImageViewer(1.35));
byId("viewer-zoom-out").addEventListener("click", () => zoomImageViewer(1 / 1.35));
byId("viewer-reset").addEventListener("click", resetImageViewer);
byId("viewer-viewport").addEventListener("wheel", (event) => {
  event.preventDefault();
  zoomImageViewer(event.deltaY < 0 ? 1.2 : 1 / 1.2);
}, { passive: false });
byId("viewer-viewport").addEventListener("dblclick", resetImageViewer);
byId("viewer-viewport").addEventListener("pointerdown", (event) => {
  if (state.viewer.scale <= 1) return;
  state.viewer.dragging = true;
  state.viewer.pointerId = event.pointerId;
  state.viewer.startX = event.clientX;
  state.viewer.startY = event.clientY;
  state.viewer.originX = state.viewer.x;
  state.viewer.originY = state.viewer.y;
  event.currentTarget.setPointerCapture(event.pointerId);
  event.currentTarget.classList.add("dragging");
});
byId("viewer-viewport").addEventListener("pointermove", (event) => {
  if (!state.viewer.dragging || event.pointerId !== state.viewer.pointerId) return;
  state.viewer.x = state.viewer.originX + event.clientX - state.viewer.startX;
  state.viewer.y = state.viewer.originY + event.clientY - state.viewer.startY;
  applyViewerTransform();
});
function endViewerDrag(event) {
  if (!state.viewer.dragging || event.pointerId !== state.viewer.pointerId) return;
  state.viewer.dragging = false;
  state.viewer.pointerId = null;
  event.currentTarget.classList.remove("dragging");
}
byId("viewer-viewport").addEventListener("pointerup", endViewerDrag);
byId("viewer-viewport").addEventListener("pointercancel", endViewerDrag);
window.addEventListener("keydown", (event) => {
  if (byId("image-viewer").classList.contains("hidden")) return;
  if (event.key === "Escape") closeImageViewer();
  if (event.key === "+" || event.key === "=") zoomImageViewer(1.25);
  if (event.key === "-") zoomImageViewer(1 / 1.25);
  if (event.key === "0") resetImageViewer();
});

byId("reference-date").value = todayLocalIso();
setDateMode("claimed_period", false);
initMap();
