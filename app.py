import io
import xml.etree.ElementTree as ET

from flask import Flask, jsonify, render_template, request

from utm_utils import lat_lon_to_utm

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/utm", methods=["POST"])
def utm():
    data = request.get_json(force=True)
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid lat/lon"}), 400

    try:
        result = lat_lon_to_utm(lat, lon)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(result)


@app.route("/utm/file", methods=["POST"])
def utm_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    filename = f.filename.lower()

    try:
        if filename.endswith(".tif") or filename.endswith(".tiff"):
            lat, lon = _centroid_from_tiff(f)
        elif filename.endswith(".kml"):
            lat, lon = _centroid_from_kml(f)
        else:
            return jsonify({"error": "Unsupported file type. Upload a GeoTIFF or KML."}), 400
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 422

    try:
        result = lat_lon_to_utm(lat, lon)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    result["centroid_lat"] = lat
    result["centroid_lon"] = lon
    return jsonify(result)


def _centroid_from_tiff(file_storage):
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform_bounds

    data = file_storage.read()
    with rasterio.open(io.BytesIO(data)) as ds:
        bounds = ds.bounds
        src_crs = ds.crs
        if src_crs and not src_crs.is_geographic:
            left, bottom, right, top = transform_bounds(src_crs, CRS.from_epsg(4326), *bounds)
        else:
            left, bottom, right, top = bounds.left, bounds.bottom, bounds.right, bounds.top

    lat = (bottom + top) / 2
    lon = (left + right) / 2
    return lat, lon


def _centroid_from_kml(file_storage):
    data = file_storage.read()
    root = ET.fromstring(data)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    coords = []
    for tag in ("coordinates", "{http://www.opengis.net/kml/2.2}coordinates"):
        for elem in root.iter(tag):
            for token in elem.text.strip().split():
                parts = token.split(",")
                if len(parts) >= 2:
                    try:
                        coords.append((float(parts[1]), float(parts[0])))  # lat, lon
                    except ValueError:
                        continue

    if not coords:
        raise ValueError("No coordinates found in KML")

    lat = sum(c[0] for c in coords) / len(coords)
    lon = sum(c[1] for c in coords) / len(coords)
    return lat, lon


if __name__ == "__main__":
    app.run(debug=True)
