const startLon = Math.max(-180, Math.min(180, (-new Date().getTimezoneOffset() / 60) * 15));
const map = L.map("map", {
  maxBounds: [[-90, -180], [90, 180]],
  maxBoundsViscosity: 1.0,
}).setView([30, startLon], 4);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors",
  maxZoom: 19,
  noWrap: true,
}).addTo(map);

let marker = null;
let kmlLayer = null;

function clearKmlLayer() {
  if (kmlLayer) { map.removeLayer(kmlLayer); kmlLayer = null; }
}

function setMarker(lat, lon, popupText) {
  if (marker) marker.setLatLng([lat, lon]);
  else marker = L.marker([lat, lon]).addTo(map);
  if (popupText) marker.bindPopup(popupText).openPopup();
}

function bandSuffix(data) {
  return data.zone_letter ? ` (band ${data.zone_letter})` : "";
}

function zoneLabel(data) {
  return `UTM Zone ${data.zone_number}${data.hemisphere}${bandSuffix(data)}`;
}

function showResult(data, lat, lon) {
  const bar = document.getElementById("result-bar");
  bar.className = "";
  document.getElementById("result-zone").textContent = zoneLabel(data);
  document.getElementById("result-crs").textContent = `${data.crs_code} — ${data.crs_name}`;
  document.getElementById("result-coords").textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
}

function showLoading() {
  const bar = document.getElementById("result-bar");
  bar.className = "loading";
  document.getElementById("result-zone").textContent = "Looking up UTM zone…";
  document.getElementById("result-crs").textContent = "";
  document.getElementById("result-coords").textContent = "";
}

function showError(msg) {
  const bar = document.getElementById("result-bar");
  bar.className = "error";
  document.getElementById("result-zone").textContent = msg;
  document.getElementById("result-crs").textContent = "";
  document.getElementById("result-coords").textContent = "";
}

async function queryUTM(lat, lon) {
  clearKmlLayer();
  showLoading();
  let res, data;
  try {
    res = await fetch("/utm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon }),
    });
    data = await res.json();
  } catch {
    showError("Request failed — check your connection and try again.");
    return;
  }
  if (!res.ok) { showError(data.error ?? "Unknown error"); return; }
  const normLat = data.lat ?? lat;
  const normLon = data.lon ?? lon;
  setMarker(normLat, normLon, `<b>${zoneLabel(data)}</b><br>${data.crs_code}`);
  showResult(data, normLat, normLon);
}

// Wrap longitude into [-180, 180] to handle clicks on repeated map frames.
function wrapLon(lon) {
  return ((lon + 180) % 360 + 360) % 360 - 180;
}

// Map click
map.on("click", (e) => queryUTM(e.latlng.lat, wrapLon(e.latlng.lng)));

// Place search
async function doSearch() {
  const q = document.getElementById("search").value.trim();
  if (!q) return;
  let res, results;
  try {
    // Browsers block setting User-Agent in fetch(); identification via Referer is automatic.
    res = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1`,
      { headers: { "Accept-Language": "en" } }
    );
    results = await res.json();
  } catch {
    showError("Search failed — check your connection and try again.");
    return;
  }
  if (!results.length) { showError(`No results for "${q}"`); return; }
  const { lat, lon } = results[0];
  map.flyTo([lat, lon], 8);
  queryUTM(parseFloat(lat), parseFloat(lon));
}

document.getElementById("search-btn").addEventListener("click", doSearch);
document.getElementById("search").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doSearch();
});

// ── Upload overlay ──────────────────────────────────────────────────────────
const overlay     = document.getElementById("upload-overlay");
const uploadBox   = document.getElementById("upload-box");
const dropContent = document.getElementById("upload-drop-content");
const spinner     = document.getElementById("upload-spinner");
const uploadError = document.getElementById("upload-error");
const fileInput   = document.getElementById("file-input");

function openOverlay() {
  setOverlayIdle();
  overlay.classList.add("visible");
}

function closeOverlay() {
  overlay.classList.remove("visible");
  fileInput.value = "";
}

function setOverlayIdle() {
  dropContent.classList.remove("hidden");
  spinner.classList.remove("visible");
  uploadError.classList.remove("visible");
  uploadError.textContent = "";
}

function setOverlayLoading() {
  dropContent.classList.add("hidden");
  spinner.classList.add("visible");
  uploadError.classList.remove("visible");
}

function setOverlayError(msg) {
  dropContent.classList.remove("hidden");
  spinner.classList.remove("visible");
  uploadError.textContent = msg;
  uploadError.classList.add("visible");
}

document.getElementById("open-upload-btn").addEventListener("click", openOverlay);
document.getElementById("cancel-upload-btn").addEventListener("click", closeOverlay);
document.getElementById("browse-btn").addEventListener("click", () => fileInput.click());

overlay.addEventListener("click", (e) => {
  if (e.target === overlay) closeOverlay();
});

// Drag-and-drop on the upload box
uploadBox.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadBox.classList.add("drag-over");
});
uploadBox.addEventListener("dragleave", (e) => {
  // Only remove highlight when the pointer leaves the box entirely, not a child.
  if (!uploadBox.contains(e.relatedTarget)) {
    uploadBox.classList.remove("drag-over");
  }
});
uploadBox.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadBox.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

// Dragging onto the map opens the overlay; guard against repeated calls on each dragover event.
const mapWrap = document.getElementById("map-wrap");
mapWrap.addEventListener("dragover", (e) => {
  e.preventDefault();
  if (!overlay.classList.contains("visible")) openOverlay();
  uploadBox.classList.add("drag-over");
});

fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) handleFile(file);
});

async function handleFile(file) {
  const name = file.name.toLowerCase();
  if (!name.endsWith(".kml") && !name.endsWith(".kmz")) {
    setOverlayError("Unsupported file type. Please upload a KML or KMZ file.");
    return;
  }

  if (file.size > MAX_FILE_BYTES) {
    const mb = (file.size / 1024 / 1024).toFixed(1);
    setOverlayError(`File is too large (${mb} MB). Maximum size is ${MAX_FILE_BYTES / 1024 / 1024} MB.`);
    return;
  }

  clearKmlLayer();
  setOverlayLoading();

  const form = new FormData();
  form.append("file", file);

  let data, res;
  try {
    res = await fetch("/utm/file", { method: "POST", body: form });
  } catch {
    setOverlayError("Upload failed — check your connection and try again.");
    return;
  }

  try {
    data = await res.json();
  } catch {
    if (res.status === 413) {
      setOverlayError("File is too large (limit: 10 MB).");
    } else {
      setOverlayError(`Server error (${res.status}). Try again.`);
    }
    return;
  }

  fileInput.value = "";

  if (!res.ok) {
    setOverlayError(data.error ?? "Unknown error.");
    return;
  }

  closeOverlay();

  const lat = data.centroid_lat;
  const lon = data.centroid_lon;

  if (data.geojson && data.geojson.features.length > 0) {
    kmlLayer = L.geoJSON(data.geojson, {
      style: { color: "#2563eb", weight: 2, fillOpacity: 0.15 },
      pointToLayer: (_, latlng) => L.circleMarker(latlng, {
        radius: 6, color: "#2563eb", fillColor: "#93c5fd", fillOpacity: 0.8, weight: 2,
      }),
    }).addTo(map);
    const bounds = kmlLayer.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40] });
    } else {
      map.flyTo([lat, lon], 8);
    }
  } else {
    map.flyTo([lat, lon], 8);
  }

  setMarker(lat, lon, `<b>${zoneLabel(data)}</b><br>${data.crs_code}`);
  showResult(data, lat, lon);
}
