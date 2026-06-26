import pytest
from utm_utils import _zone_letter, lat_lon_to_utm


def test_basic_north():
    result = lat_lon_to_utm(48.8566, 2.3522)  # Paris
    assert result["zone_number"] == 31
    assert result["zone_letter"] == "U"
    assert result["hemisphere"] == "N"
    assert result["crs_code"] == "EPSG:32631"


def test_basic_south():
    result = lat_lon_to_utm(-33.8688, 151.2093)  # Sydney
    assert result["zone_number"] == 56
    assert result["zone_letter"] == "H"
    assert result["hemisphere"] == "S"
    assert result["crs_code"] == "EPSG:32756"


def test_crs_name():
    result = lat_lon_to_utm(40.7128, -74.0060)  # New York
    assert result["crs_name"] == "WGS 84 / UTM zone 18N"


def test_norway_exception():
    # Zone 31V/32V boundary: lon in [3,12) with lat in [56,64) → zone 32
    result = lat_lon_to_utm(58.0, 5.0)
    assert result["zone_number"] == 32


def test_svalbard_31():
    result = lat_lon_to_utm(78.0, 4.0)
    assert result["zone_number"] == 31


def test_svalbard_33():
    result = lat_lon_to_utm(78.0, 15.0)
    assert result["zone_number"] == 33


def test_svalbard_35():
    result = lat_lon_to_utm(78.0, 25.0)
    assert result["zone_number"] == 35


def test_svalbard_37():
    result = lat_lon_to_utm(78.0, 35.0)
    assert result["zone_number"] == 37


def test_lon_180_wraps_to_zone_1():
    # Normalization maps 180° to -180° (same meridian), which falls in zone 1.
    result = lat_lon_to_utm(0.0, 180.0)
    assert result["zone_number"] == 1


def test_antimeridian_west():
    result = lat_lon_to_utm(0.0, -180.0)
    assert result["zone_number"] == 1


def test_equator_is_north():
    result = lat_lon_to_utm(0.0, 0.0)
    assert result["hemisphere"] == "N"
    assert result["crs_code"] == "EPSG:32631"


def test_zone_letter_polar_north_returns_none():
    result = lat_lon_to_utm(85.0, 0.0)
    assert result["zone_letter"] is None


def test_zone_letter_polar_south_returns_none():
    result = lat_lon_to_utm(-81.0, 0.0)
    assert result["zone_letter"] is None


def test_invalid_lat():
    with pytest.raises(ValueError):
        lat_lon_to_utm(91.0, 0.0)


def test_out_of_range_lon_normalizes():
    # lon=181 wraps to -179, which is zone 1 — no error raised.
    result = lat_lon_to_utm(0.0, 181.0)
    assert result["zone_number"] == 1


def test_crs_name_southern():
    result = lat_lon_to_utm(-33.8688, 151.2093)  # Sydney
    assert result["crs_name"] == "WGS 84 / UTM zone 56S"


# _zone_letter boundary tests
def test_zone_letter_bottom_boundary():
    # lat=-80 is the first valid band (C)
    assert _zone_letter(-80.0) == "C"


def test_zone_letter_just_below_bottom_boundary():
    assert _zone_letter(-80.1) is None


def test_zone_letter_top_boundary():
    # lat=84 is the last valid band (X); the index clamp is required here
    assert _zone_letter(84.0) == "X"


def test_zone_letter_just_above_top_boundary():
    assert _zone_letter(84.1) is None


def test_zone_letter_x_band():
    # Band X spans 72–84 (12° wide, unlike the standard 8°)
    assert _zone_letter(72.0) == "X"
    assert _zone_letter(80.0) == "X"
