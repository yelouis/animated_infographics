"""Unit tests for Gazetteer geo resolution and country bbox checking."""

from pathlib import Path

import pytest

from animated_infographics.planner.geo import Gazetteer, check_coords_in_bbox, load_country_bboxes

REPO_ROOT = Path(__file__).parent.parent
CITIES_PATH = REPO_ROOT / "data" / "vendor" / "cities15000.txt"
COUNTRY_INFO_PATH = REPO_ROOT / "data" / "vendor" / "countryInfo.txt"
BBOXES_PATH = REPO_ROOT / "data" / "geo" / "country_bboxes.json"


@pytest.fixture(scope="module")
def gazetteer() -> Gazetteer:
    return Gazetteer.load(CITIES_PATH, COUNTRY_INFO_PATH)


@pytest.fixture(scope="module")
def bboxes() -> dict[str, tuple[float, float, float, float]]:
    return load_country_bboxes(BBOXES_PATH)


def test_boston_resolves_usa(gazetteer: Gazetteer) -> None:
    res = gazetteer.resolve("Boston", "USA")
    assert res is not None
    lat, lon = res
    assert pytest.approx(42.36, abs=0.05) == lat
    assert pytest.approx(-71.06, abs=0.05) == lon


def test_constantinople_resolves_istanbul(gazetteer: Gazetteer) -> None:
    res = gazetteer.resolve("Constantinople")
    assert res is not None
    lat, lon = res
    # Istanbul lat ~41.01, lon ~28.95
    assert pytest.approx(41.01, abs=0.05) == lat
    assert pytest.approx(28.95, abs=0.05) == lon


def test_duluth_resolves_minnesota_highest_pop(gazetteer: Gazetteer) -> None:
    # Duluth MN (pop 86,110) must beat Duluth GA (pop 29,193)
    res = gazetteer.resolve("Duluth", "USA")
    assert res is not None
    lat, lon = res
    assert pytest.approx(46.78, abs=0.05) == lat
    assert pytest.approx(-92.11, abs=0.05) == lon


def test_thunder_bay_resolves_can(gazetteer: Gazetteer) -> None:
    res = gazetteer.resolve("Thunder Bay", "CAN")
    assert res is not None
    lat, lon = res
    assert pytest.approx(48.38, abs=0.05) == lat
    assert pytest.approx(-89.25, abs=0.05) == lon


def test_amarillo_resolves_usa(gazetteer: Gazetteer) -> None:
    res = gazetteer.resolve("Amarillo", "USA")
    assert res is not None
    lat, lon = res
    assert pytest.approx(35.22, abs=0.05) == lat
    assert pytest.approx(-101.83, abs=0.05) == lon


def test_nonexistent_place_returns_none(gazetteer: Gazetteer) -> None:
    assert gazetteer.resolve("NonExistentCityXYZ12345") is None


def test_country_filter_preference(gazetteer: Gazetteer) -> None:
    # Paris in USA (e.g. Paris, Texas) vs Paris in FRA
    res_usa = gazetteer.resolve("Paris", "USA")
    assert res_usa is not None
    res_fra = gazetteer.resolve("Paris", "FRA")
    assert res_fra is not None
    assert res_usa != res_fra


def test_gazetteer_loads_from_cache(tmp_path: Path) -> None:
    # Load first time into tmp_path
    g1 = Gazetteer.load(CITIES_PATH, COUNTRY_INFO_PATH, cache_dir=tmp_path)
    assert g1.resolve("Boston", "USA") is not None

    # Load second time: should hit pickle cache
    g2 = Gazetteer.load(CITIES_PATH, COUNTRY_INFO_PATH, cache_dir=tmp_path)
    assert g2.resolve("Boston", "USA") is not None


def test_check_coords_in_bbox(bboxes: dict[str, tuple[float, float, float, float]]) -> None:
    # Boston (42.36, -71.06) inside USA bbox
    assert check_coords_in_bbox(42.36, -71.06, "USA", bboxes)

    # Point at (0, 0) is not in USA
    assert not check_coords_in_bbox(0.0, 0.0, "USA", bboxes)

    # Unknown country
    assert not check_coords_in_bbox(42.36, -71.06, "XYZ", bboxes)
    assert not check_coords_in_bbox(42.36, -71.06, None, bboxes)

    # Point within 0.5 margin vs beyond margin
    # USA min_lat ~ 18.91 (Hawaii/PR/etc) or check exact USA bbox
    min_lon, min_lat, max_lon, max_lat = bboxes["USA"]
    # Exactly on boundary
    assert check_coords_in_bbox(min_lat, min_lon, "USA", bboxes, margin=0.0)
    # 0.4 deg outside boundary with margin 0.5
    assert check_coords_in_bbox(min_lat - 0.4, min_lon, "USA", bboxes, margin=0.5)
    # 0.6 deg outside boundary with margin 0.5
    assert not check_coords_in_bbox(min_lat - 0.6, min_lon, "USA", bboxes, margin=0.5)
