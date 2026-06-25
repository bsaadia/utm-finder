import math


def _zone_letter(lat):
    letters = "CDEFGHJKLMNPQRSTUVWX"
    if lat < -80 or lat > 84:
        return None
    idx = int((lat + 80) / 8)
    idx = min(idx, len(letters) - 1)
    return letters[idx]


def lat_lon_to_utm(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

    zone_number = int((lon + 180) / 6) + 1
    if lon == 180:
        zone_number = 60

    # Norway/Svalbard exceptions (UTM spec)
    if 56 <= lat < 64 and 3 <= lon < 12:
        zone_number = 32
    if 72 <= lat <= 84:
        if 0 <= lon < 9:
            zone_number = 31
        elif 9 <= lon < 21:
            zone_number = 33
        elif 21 <= lon < 33:
            zone_number = 35
        elif 33 <= lon < 42:
            zone_number = 37

    letter = _zone_letter(lat)
    north = lat >= 0
    epsg = 32600 + zone_number if north else 32700 + zone_number
    hemisphere = "N" if north else "S"

    return {
        "zone_number": zone_number,
        "zone_letter": letter,
        "hemisphere": hemisphere,
        "crs_code": f"EPSG:{epsg}",
        "crs_name": f"WGS 84 / UTM zone {zone_number}{hemisphere}",
    }
