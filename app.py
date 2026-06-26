from __future__ import annotations

import io
import logging
import os
import xml.etree.ElementTree as ET
import zipfile

from flask import Flask, jsonify, render_template, request

from utm_utils import lat_lon_to_utm

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_BYTES


@app.context_processor
def inject_static_version():
    path = os.path.join(app.static_folder, "app.js")
    return {"app_js_v": int(os.path.getmtime(path))}


@app.route("/")
def index():
    return render_template("index.html", max_file_bytes=MAX_FILE_BYTES)


@app.route("/utm", methods=["POST"])
def utm():
    data = request.get_json(force=True)
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid lat/lon."}), 400

    try:
        result = lat_lon_to_utm(lat, lon)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(result)


@app.route("/utm/file", methods=["POST"])
def utm_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    f = request.files["file"]
    filename = f.filename.lower()

    if filename.endswith(".kml"):
        kml_bytes = f.read()
    elif filename.endswith(".kmz"):
        try:
            with zipfile.ZipFile(io.BytesIO(f.read())) as zf:
                kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
                if not kml_names:
                    return jsonify({"error": "No KML file found inside KMZ archive."}), 422
                kml_bytes = zf.read(kml_names[0])
        except zipfile.BadZipFile:
            return jsonify({"error": "Could not read KMZ: file is not a valid ZIP archive."}), 422
    else:
        return jsonify({"error": "Unsupported file type. Upload a KML or KMZ file."}), 400

    try:
        lat, lon, geojson = _parse_kml(kml_bytes)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except ET.ParseError:
        logging.exception("KML parse error")
        return jsonify({"error": "Could not parse file: invalid XML."}), 422

    try:
        result = lat_lon_to_utm(lat, lon)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    result["geojson"] = geojson
    return jsonify(result)


def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_coord_str(text: str) -> list:
    pairs = []
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            try:
                pairs.append([float(parts[0]), float(parts[1])])
            except ValueError:
                continue
    return pairs


def _coords_of(elem) -> list:
    for child in elem:
        if _strip_ns(child.tag) == "coordinates" and child.text:
            return _parse_coord_str(child.text)
    return []


def _parse_geometry(elem) -> dict | None:
    tag = _strip_ns(elem.tag)
    if tag == "Point":
        c = _coords_of(elem)
        if c:
            return {"type": "Point", "coordinates": c[0]}
    elif tag == "LineString":
        c = _coords_of(elem)
        if c:
            return {"type": "LineString", "coordinates": c}
    elif tag == "Polygon":
        rings = []
        for child in elem:
            ctag = _strip_ns(child.tag)
            if ctag in ("outerBoundaryIs", "innerBoundaryIs"):
                for lr in child:
                    if _strip_ns(lr.tag) == "LinearRing":
                        c = _coords_of(lr)
                        if c:
                            rings.append(c)
        if rings:
            return {"type": "Polygon", "coordinates": rings}
    elif tag == "MultiGeometry":
        geoms = [g for child in elem if (g := _parse_geometry(child))]
        if geoms:
            return {"type": "GeometryCollection", "geometries": geoms}
    return None


def _parse_kml(kml_bytes: bytes) -> tuple:
    """Return (lat, lon, geojson_feature_collection)."""
    root = ET.fromstring(kml_bytes)

    features = []
    for placemark in root.iter():
        if _strip_ns(placemark.tag) != "Placemark":
            continue
        name = None
        geom = None
        for child in placemark:
            ctag = _strip_ns(child.tag)
            if ctag == "name":
                name = child.text
            elif ctag in ("Point", "LineString", "Polygon", "MultiGeometry"):
                geom = _parse_geometry(child)
        if geom:
            features.append({
                "type": "Feature",
                "properties": {"name": name},
                "geometry": geom,
            })

    all_coords = _extract_coords_from_features(features)
    if not all_coords:
        raise ValueError("No coordinates found in KML.")

    # GeoJSON coordinates are [lon, lat]
    lat = sum(c[1] for c in all_coords) / len(all_coords)
    lon = sum(c[0] for c in all_coords) / len(all_coords)
    return lat, lon, {"type": "FeatureCollection", "features": features}


def _extract_coords_from_features(features: list) -> list:
    coords = []
    for feature in features:
        coords.extend(_extract_coords(feature["geometry"]))
    return coords


def _extract_coords(geom: dict | None) -> list:
    """Recursively collect all [lon, lat] pairs from a GeoJSON geometry."""
    if geom is None:
        return []
    t = geom["type"]
    if t == "Point":
        return [geom["coordinates"]]
    if t in ("LineString", "MultiPoint"):
        return list(geom["coordinates"])  # copy, not a reference to the source geometry
    if t in ("Polygon", "MultiLineString"):
        return [p for ring in geom["coordinates"] for p in ring]
    if t == "MultiPolygon":
        return [p for polygon in geom["coordinates"] for ring in polygon for p in ring]
    if t == "GeometryCollection":
        return [p for g in geom.get("geometries", []) for p in _extract_coords(g)]
    return []


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
