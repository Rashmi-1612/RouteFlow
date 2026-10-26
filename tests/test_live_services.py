"""Service tests use mocked HTTP payloads shaped like the real APIs' documented responses."""
import pytest
import requests

from routeflow import db, geo, live, planner


class FakeResp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


PTS = ((28.6315, 77.2167), (28.6129, 77.2295), (28.6562, 77.2410))


def test_haversine_known_distance():
    assert geo.haversine_km((28.6315, 77.2167), (28.5245, 77.1855)) == pytest.approx(12.2, abs=0.6)


def test_osrm_table_parsed(monkeypatch):
    geo.road_matrix.cache_clear()
    payload = {"code": "Ok",
               "distances": [[0, 3000, 5000], [3100, 0, 8000], [5200, 8200, 0]],
               "durations": [[0, 400, 700], [410, 0, 1000], [710, 1010, 0]]}
    monkeypatch.setattr(geo.requests, "get", lambda *a, **k: FakeResp(payload))
    out = geo.road_matrix(PTS)
    assert out["source"] == "osrm"
    assert out["distance_km"][0][1] == 3.0 and out["duration_s"][2][1] == 1010


def test_osrm_null_entries_filled_with_estimate(monkeypatch):
    geo.road_matrix.cache_clear()
    payload = {"code": "Ok", "distances": [[0, None, 5000], [3100, 0, 8000], [5200, 8200, 0]],
               "durations": [[0, None, 700], [410, 0, 1000], [710, 1010, 0]]}
    monkeypatch.setattr(geo.requests, "get", lambda *a, **k: FakeResp(payload))
    out = geo.road_matrix(PTS)
    assert out["distance_km"][0][1] > 0 and "estimated" in out["note"]


def test_offline_falls_back_to_estimate(monkeypatch):
    geo.road_matrix.cache_clear()

    def boom(*a, **k):
        raise requests.ConnectionError("no network")
    monkeypatch.setattr(geo.requests, "get", boom)
    out = geo.road_matrix(PTS)
    assert out["source"] == "estimate" and out["distance_km"][0][1] > 0
    assert geo.geocode("somewhere far away") == []


def test_geocode_and_route_geometry(monkeypatch):
    geo.geocode.cache_clear(); geo.route_geometry.cache_clear()
    monkeypatch.setattr(geo.requests, "get", lambda url, **k: FakeResp(
        [{"display_name": "Qutub Minar, Delhi", "lat": "28.5245", "lon": "77.1855"}]
        if "search" in url else
        {"code": "Ok", "routes": [{"geometry": {"coordinates": [[77.2, 28.6], [77.3, 28.7]]}}]}))
    assert geo.geocode("qutub minar")[0]["lat"] == 28.5245
    g = geo.route_geometry(PTS)
    assert g["source"] == "osrm" and g["path"][0] == (28.6, 77.2)


def test_weather_parsing_and_factor(monkeypatch):
    live.fetch_weather.cache_clear()
    monkeypatch.setattr(live.requests, "get", lambda *a, **k: FakeResp({
        "utc_offset_seconds": 19800,
        "current": {"temperature_2m": 31.0, "precipitation": 3.0, "wind_speed_10m": 12, "weather_code": 63}}))
    w = live.fetch_weather(28.6, 77.2)
    assert w["ok"] and w["description"] == "Rain" and w["factor"] == pytest.approx(1.15)
    assert live.live_context(28.6, 77.2)["factor"] >= 1.15 * 0.95


def test_weather_offline_is_neutral(monkeypatch):
    live.fetch_weather.cache_clear()
    monkeypatch.setattr(live.requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.Timeout()))
    w = live.fetch_weather(1.0, 2.0)
    assert not w["ok"] and w["factor"] == 1.0


def test_factors():
    assert live.weather_factor(0, 0, 0) == 1.0
    assert live.weather_factor(10, 95, 50) == 1.6          # capped
    assert live.traffic_factor(18, 1) > live.traffic_factor(13, 1) > live.traffic_factor(23, 1)
    assert live.traffic_factor(18, 6) < live.traffic_factor(18, 1)


def test_planner_pipeline_offline():
    geo.road_matrix.cache_clear()
    locs = [(l["latitude"], l["longitude"]) for l in db_demo()]
    mat = geo.road_matrix(tuple(locs))
    demands = [0] + [3] * (len(locs) - 1)
    clusters, warns = planner.assign_stops(mat["distance_km"], demands, 3, 10)
    assert sum(len(c) for c in clusters) == len(locs) - 1
    results, skipped = planner.compare(list(planner.ALGORITHMS), mat["distance_km"],
                                       mat["distance_km"], mat["duration_s"], clusters)
    best_exact = min(r["total_km"] for r in results if r["algorithm"] in planner.EXACT)
    assert all(r["total_km"] >= best_exact - 1e-9 for r in results)


def db_demo():
    return [dict(latitude=r[2], longitude=r[3]) for r in db.DEMO_LOCATIONS]


def test_database_crud(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    db.get_engine.cache_clear()
    assert len(db.list_locations()) == len(db.DEMO_LOCATIONS)
    assert db.list_locations()[0]["location_type"] == "Hub"
    db.add_location("Test Stop", "addr", 28.6, 77.2, 2, 3)
    with pytest.raises(ValueError):
        db.add_location("test stop", "dup", 28.6, 77.2)
    new = db.list_locations()[-1]
    db.update_location(new["location_id"], 9, 1)
    assert db.list_locations()[-1]["demand"] == 9
    with pytest.raises(ValueError):
        db.delete_location(db.list_locations()[0]["location_id"])
    db.set_hub(new["location_id"])
    assert db.list_locations()[0]["location_name"] == "Test Stop"
    db.delete_location(db.list_locations()[1]["location_id"])
    db.save_run({"algorithm_name": "X", "objective": "distance", "n_stops": 3, "n_couriers": 1,
                 "total_distance_km": 1.0, "total_duration_min": 2.0, "route_sequence": "a",
                 "execution_time_ms": 0.1, "data_source": "estimate", "delay_factor": 1.0})
    assert len(db.list_runs()) == 1
    db.reset_demo()
    assert db.list_locations()[0]["location_name"] == "Courier Hub"
    db.get_engine.cache_clear()