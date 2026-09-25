"""Geographic resolution, GeoNames gazetteer indexing, and country bounding box validation."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


def norm_geo_name(s: str) -> str:
    """Normalize place name for gazetteer matching: NFKD diacritic strip, casefold, strip."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold().strip()


@dataclass(frozen=True, slots=True)
class CityRecord:
    """Indexed GeoNames city record."""

    lat: float
    lon: float
    country_iso3: str
    population: int


class Gazetteer:
    """Fast in-memory GeoNames gazetteer with persistent disk caching."""

    def __init__(self, index: dict[str, list[CityRecord]]) -> None:
        self._index = index

    @classmethod
    def load(
        cls,
        cities: Path,
        country_info: Path,
        cache_dir: Path | None = None,
    ) -> Gazetteer:
        """Load gazetteer index, caching the pickled result keyed by file SHA-256."""
        cities_bytes = cities.read_bytes()
        info_bytes = country_info.read_bytes()
        h = hashlib.sha256(cities_bytes + b"\n" + info_bytes).hexdigest()

        base_cache = cache_dir or Path(os.environ.get("INFOGRAPHICS_CACHE_DIR", "./cache"))
        geo_cache = base_cache / "geo"
        geo_cache.mkdir(parents=True, exist_ok=True)
        cache_file = geo_cache / f"gazetteer_{h}.pickle"

        if cache_file.is_file():
            try:
                with open(cache_file, "rb") as f:
                    cached_index = pickle.load(f)
                return cls(cached_index)
            except Exception:
                pass  # Fall through to rebuild on corruption

        # 1. Parse countryInfo.txt (ISO2 -> ISO3)
        iso2_to_iso3: dict[str, str] = {}
        for line in country_info.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                iso2_to_iso3[parts[0].strip()] = parts[1].strip()

        # 2. Parse cities15000.txt
        index: dict[str, list[CityRecord]] = {}
        for line in cities.read_text(encoding="utf-8").splitlines():
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) < 15:
                continue

            name, asciiname, altnames = parts[1], parts[2], parts[3]
            try:
                lat, lon = float(parts[4]), float(parts[5])
            except ValueError:
                continue

            iso2 = parts[8].strip()
            iso3 = iso2_to_iso3.get(iso2, "")
            pop = int(parts[14]) if parts[14].isdigit() else 0
            rec = CityRecord(lat=lat, lon=lon, country_iso3=iso3, population=pop)

            names = {norm_geo_name(name), norm_geo_name(asciiname)}
            if altnames:
                for alt in altnames.split(","):
                    n = norm_geo_name(alt)
                    if n:
                        names.add(n)

            for n in names:
                if n not in index:
                    index[n] = []
                index[n].append(rec)

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass

        return cls(index)

    def resolve(self, name: str, country_iso3: str | None = None) -> tuple[float, float] | None:
        """Resolve a place name to (lat, lon).

        Candidates in country_iso3 are preferred; among candidates, highest population wins.
        If direct match fails, tries comma-separated components and possessive qualifiers.
        """
        key = norm_geo_name(name)
        candidates = self._index.get(key)
        if candidates:
            if country_iso3:
                country_candidates = [c for c in candidates if c.country_iso3 == country_iso3]
                if country_candidates:
                    best = max(country_candidates, key=lambda c: c.population)
                    return (best.lat, best.lon)

            best = max(candidates, key=lambda c: c.population)
            return (best.lat, best.lon)

        # Try comma-separated components from right to left (e.g. "North End, Boston" -> "Boston")
        if "," in name:
            for part in reversed(name.split(",")):
                p = part.strip()
                if p:
                    res = self.resolve(p, country_iso3)
                    if res is not None:
                        return res

        # Try possessive components (e.g. "Boston's North End" -> "Boston")
        normalized_quotes = name.replace("’s ", "'s ")
        if "'s " in normalized_quotes:
            for part in normalized_quotes.split("'s "):
                p = part.strip()
                if p:
                    res = self.resolve(p, country_iso3)
                    if res is not None:
                        return res

        # Try stripping common geographic qualifiers (e.g. "Boston Harbor" -> "Boston")
        suffixes = (" Harbor", " Harbour", " City", " District", " Town")
        for sfx in suffixes:
            if name.endswith(sfx):
                base = name[: -len(sfx)].strip()
                if base:
                    res = self.resolve(base, country_iso3)
                    if res is not None:
                        return res

        return None


def load_country_bboxes(path: Path) -> dict[str, tuple[float, float, float, float]]:
    """Load country bounding boxes as {ISO3: (min_lon, min_lat, max_lon, max_lat)}."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    result: dict[str, tuple[float, float, float, float]] = {}
    for k, v in data.items():
        if k.startswith("$"):
            continue
        if isinstance(v, list) and len(v) == 4:
            result[k] = (float(v[0]), float(v[1]), float(v[2]), float(v[3]))
    return result


def check_coords_in_bbox(
    lat: float,
    lon: float,
    country_iso3: str | None,
    bboxes: Mapping[str, tuple[float, float, float, float]],
    margin: float = 0.5,
) -> bool:
    """Check if (lat, lon) falls inside the country's bounding box expanded by margin degrees."""
    if not country_iso3 or country_iso3 not in bboxes:
        return False

    min_lon, min_lat, max_lon, max_lat = bboxes[country_iso3]

    if not (min_lat - margin <= lat <= max_lat + margin):
        return False

    if min_lon > max_lon:
        # Crosses antimeridian (e.g. USA, RUS, NZL, KIR)
        return (lon >= min_lon - margin) or (lon <= max_lon + margin)

    return min_lon - margin <= lon <= max_lon + margin
