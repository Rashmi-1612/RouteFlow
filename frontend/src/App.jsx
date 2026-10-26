
import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import {
  Activity,
  ArrowRight,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Gauge,
  MapPin,
  Navigation,
  Package,
  Plus,
  RefreshCw,
  Route,
  Search,
  Settings2,
  Trash2,
  Truck,
  Warehouse,
} from "lucide-react";
import "leaflet/dist/leaflet.css";


const API = "http://127.0.0.1:8000/api";

const DEFAULT_CENTER = [28.6139, 77.209];

const hubIcon = new L.DivIcon({
  className: "custom-marker hub-marker",
  html: "<span>H</span>",
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});

const stopIcon = new L.DivIcon({
  className: "custom-marker stop-marker",
  html: "<span>•</span>",
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

function validCoordinates(lat, lon) {
  const latitude = Number(lat);
  const longitude = Number(lon);

  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    Math.abs(latitude) > 90 ||
    Math.abs(longitude) > 180
  ) {
    return null;
  }

  return [latitude, longitude];
}

function locationCoordinates(location) {
  if (!location || typeof location !== "object") {
    return null;
  }

  const coords = location.coordinates;

  let lat = location.latitude ?? location.lat;
  let lon =
    location.longitude ??
    location.lon ??
    location.lng;

  if (Array.isArray(coords)) {
    lat ??= coords[0];
    lon ??= coords[1];
  } else if (coords && typeof coords === "object") {
    lat ??= coords.latitude ?? coords.lat;
    lon ??= coords.longitude ?? coords.lon ?? coords.lng;
  }

  return validCoordinates(lat, lon);
}

function FitBounds({ locations = [], route }) {
  const map = useMap();

  useEffect(() => {
    const routePoints = Array.isArray(route?.path)
      ? route.path
          .map((point) => {
            if (Array.isArray(point)) {
              return validCoordinates(point[0], point[1]);
            }

            if (point && typeof point === "object") {
              return validCoordinates(
                point.latitude ?? point.lat,
                point.longitude ?? point.lon ?? point.lng
              );
            }

            return null;
          })
          .filter(Boolean)
      : [];

    const locationPoints = locations
      .map(locationCoordinates)
      .filter(Boolean);

    const points = routePoints.length ? routePoints : locationPoints;

    if (points.length === 1) {
      map.setView(points[0], 13);
    } else if (points.length > 1) {
      map.fitBounds(points, {
        padding: [40, 40],
        maxZoom: 13,
      });
    }
  }, [map, locations, route]);

  return null;
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || data.message || "Request failed. Is the backend running?"
    );
  }

  return data;
}

function MapMarkers({ locations = [] }) {
  return locations.map((location, index) => {
    if (!location) return null;

    const position = locationCoordinates(location);
    if (!position) return null;

    const isHub = location.location_type === "Hub";

    return (
      <Marker
        key={location.location_id ?? location.id ?? index}
        position={position}
        icon={isHub ? hubIcon : stopIcon}
      >
        <Popup>
          <b>{location.location_name || location.name || "Location"}</b>
          <br />
          {location.address || ""}
          <br />
          {location.location_type || "Delivery stop"}
        </Popup>
      </Marker>
    );
  });
}

export default function App() {
  const [page, setPage] = useState("Overview");
  const [locations, setLocations] = useState([]);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [chosen, setChosen] = useState("");
  const [name, setName] = useState("");
  const [demand, setDemand] = useState(1);
  const [service, setService] = useState(5);

  const [searching, setSearching] = useState(false);
  const [saving, setSaving] = useState(false);
  const [objective, setObjective] = useState("distance");
  const [algorithm, setAlgorithm] = useState("NN + 2-opt/Or-opt");
  const [couriers, setCouriers] = useState(1);
  const [capacity, setCapacity] = useState(14);
  const [useTraffic, setUseTraffic] = useState(true);
  const [useWeather, setUseWeather] = useState(false);

  const [plan, setPlan] = useState(null);
  const [planning, setPlanning] = useState(false);
  const [algorithms, setAlgorithms] = useState([]);

  async function refresh() {
    try {
      const [locationData, statusData, algorithmData] = await Promise.all([
        api("/locations"),
        api("/health"),
        api("/algorithms"),
      ]);

      const safeLocations = Array.isArray(locationData)
        ? locationData
        : locationData.locations || [];

      const safeAlgorithms = Array.isArray(algorithmData)
        ? algorithmData
        : algorithmData.algorithms || [];

      setLocations(safeLocations.filter(Boolean));
      setHealth(statusData);
      setAlgorithms(safeAlgorithms);
      setError("");
    } catch (e) {
      setError(e.message);
      setHealth(null);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const hub =
    locations.find((location) => location?.location_type === "Hub") ||
    locations[0] ||
    null;

  const deliveries = locations.filter(
    (location) => location && location.location_type !== "Hub"
  );

  const selectedCandidate =
    candidates[Number(chosen)] || null;

  const activeRoute = plan?.routes?.[0] || null;
  const allRoutes = Array.isArray(plan?.routes) ? plan.routes : [];

  const center = useMemo(
    () => locationCoordinates(hub) || DEFAULT_CENTER,
    [hub]
  );

  async function searchAddress(event) {
    event?.preventDefault();

    setError("");
    setNotice("");
    setCandidates([]);
    setChosen("");

    if (query.trim().length < 3) {
      setError("Enter at least 3 characters to search.");
      return;
    }

    setSearching(true);

    try {
      const data = await api(
        `/geocode?q=${encodeURIComponent(query.trim())}`
      );

      const results = Array.isArray(data)
        ? data
        : data.results || data.locations || [];

      setCandidates(results.filter(Boolean));

      if (results.length) {
        setChosen("0");

        const label =
          results[0].label ||
          results[0].display_name ||
          results[0].address ||
          "";

        setName(label.split(",")[0] || query.trim());
        setNotice(
          `${results.length} address option(s) found. Choose the correct result.`
        );
      } else {
        setError(
          "No address found. Try a specific address, city, or state."
        );
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  }

  async function addStop(event) {
    event.preventDefault();

    if (!selectedCandidate) {
      setError("Search for an address and select a result first.");
      return;
    }

    const coordinates = locationCoordinates(selectedCandidate);

    if (!coordinates) {
      setError("The selected search result has invalid coordinates.");
      return;
    }

    setSaving(true);
    setError("");
    setNotice("");

    try {
      await api("/locations", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim() || query.trim(),
          address:
            selectedCandidate.label ||
            selectedCandidate.display_name ||
            selectedCandidate.address ||
            "",
          lat: coordinates[0],
          lon: coordinates[1],
          demand: Number(demand),
          service_min: Number(service),
        }),
      });

      setQuery("");
      setCandidates([]);
      setChosen("");
      setName("");
      setDemand(1);
      setService(5);
      setPlan(null);

      await refresh();
      setNotice("Delivery stop added successfully.");
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function makeHub(id) {
    if (id == null) {
      setError("This location has no ID.");
      return;
    }

    setError("");
    setNotice("");

    try {
      await api(`/locations/${encodeURIComponent(id)}/make-hub`, {
        method: "POST",
      });

      setPlan(null);
      await refresh();
      setNotice("Courier hub updated.");
    } catch (e) {
      setError(e.message);
    }
  }

  async function removeStop(id) {
    if (id == null) {
      setError("This location has no ID.");
      return;
    }

    setError("");
    setNotice("");

    try {
      await api(`/locations/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });

      setPlan(null);
      await refresh();
      setNotice("Delivery stop removed.");
    } catch (e) {
      setError(e.message);
    }
  }

  async function optimize(event) {
    event?.preventDefault();

    if (!hub) {
      setError("Add a courier hub before generating a route.");
      return;
    }

    if (!deliveries.length) {
      setError("Add at least one delivery stop before planning.");
      return;
    }

    setPlanning(true);
    setError("");
    setNotice("");

    try {
      const result = await api("/plan", {
        method: "POST",
        body: JSON.stringify({
          objective,
          algorithm,
          couriers: Number(couriers),
          capacity: Number(capacity),
          use_weather: useWeather,
          use_traffic: useTraffic,
        }),
      });

      setPlan(result);
      setNotice("Route plan generated.");
    } catch (e) {
      setError(e.message);
    } finally {
      setPlanning(false);
    }
  }

  const nav = [
    { name: "Overview", icon: Gauge },
    { name: "Locations", icon: MapPin },
    { name: "Route Planner", icon: Route },
    { name: "History", icon: Activity },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Truck size={22} />
          </div>
          <div>
            <b>RouteFlow</b>
            <small>COURIER OPERATIONS</small>
          </div>
        </div>

        <div className="side-label">WORKSPACE</div>

        <nav>
          {nav.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={`nav-item ${
                  page === item.name ? "active" : ""
                }`}
                onClick={() => setPage(item.name)}
              >
                <Icon size={18} />
                <span>{item.name}</span>
                {item.name === "Route Planner" && (
                  <ArrowRight size={14} className="nav-arrow" />
                )}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="api-status">
            <span className={`status-dot ${health ? "online" : ""}`} />
            <div>
              <b>{health ? "Backend connected" : "Backend offline"}</b>
              <small>
                {health
                  ? `Database: ${health.database ?? "Connected"}`
                  : "Start the FastAPI server"}
              </small>
            </div>
          </div>

          <button className="nav-item muted" onClick={refresh}>
            <RefreshCw size={17} />
            Refresh data
          </button>

          <div className="profile">
            <div className="avatar">RF</div>
            <div>
              <b>RouteFlow Admin</b>
              <small>Project workspace</small>
            </div>
            <Settings2 size={17} />
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <b>{page}</b>
          </div>
          <div className="top-actions">
            <span className="live-pill">
              <i /> ROUTING SERVICES
            </span>
            <button className="icon-btn" title="Help">
              <CircleHelp size={18} />
            </button>
            <div className="avatar small">RF</div>
          </div>
        </header>

        {error && (
          <div className="alert error">
            <b>Something needs attention</b>
            <span>{error}</span>
            <button onClick={() => setError("")}>×</button>
          </div>
        )}

        {notice && (
          <div className="alert success">
            <Check size={17} />
            <span>{notice}</span>
            <button onClick={() => setNotice("")}>×</button>
          </div>
        )}

        {page === "Overview" && (
          <>
            <section className="page-heading">
              <div>
                <div className="eyebrow">OPERATIONS OVERVIEW</div>
                <h1>
                  Good day, RouteFlow <span>✦</span>
                </h1>
                <p>Here’s what’s happening across your courier network.</p>
              </div>
              <button
                className="primary-btn"
                onClick={() => setPage("Route Planner")}
              >
                <Route size={17} /> Plan a route
              </button>
            </section>

            <section className="stat-grid">
              <Stat
                icon={Warehouse}
                label="Courier hubs"
                value={hub ? 1 : 0}
                detail={hub?.location_name || "No hub configured"}
                color="violet"
              />
              <Stat
                icon={MapPin}
                label="Delivery stops"
                value={deliveries.length}
                detail="Saved locations"
                color="blue"
              />
              <Stat
                icon={Package}
                label="Total parcel load"
                value={deliveries.reduce(
                  (sum, location) => sum + Number(location.demand || 0),
                  0
                )}
                detail="Across all delivery stops"
                color="orange"
              />
              <Stat
                icon={Activity}
                label="Route status"
                value={plan ? "Ready" : "Not planned"}
                detail={
                  plan
                    ? `${plan.total_km ?? "—"} km planned`
                    : "Generate a route to begin"
                }
                color="green"
                textValue
              />
            </section>

            <section className="content-grid">
              <div className="panel map-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Network map</h2>
                    <p>Courier hub and delivery locations</p>
                  </div>
                  <span className="subtle-pill">
                    <span className="status-dot online" /> OpenStreetMap
                  </span>
                </div>

                <MapContainer
                  center={center}
                  zoom={11}
                  scrollWheelZoom
                  className="map"
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <MapMarkers locations={locations} />
                  {activeRoute?.path?.length > 1 && (
                    <Polyline
                      positions={activeRoute.path}
                      pathOptions={{
                        color: "#ff4d57",
                        weight: 5,
                        opacity: 0.85,
                      }}
                    />
                  )}
                  <FitBounds locations={locations} route={activeRoute} />
                </MapContainer>

                <div className="map-legend">
                  <span><i className="legend-hub" /> Courier hub</span>
                  <span><i className="legend-stop" /> Delivery stop</span>
                  <span><i className="legend-route" /> Planned route</span>
                </div>
              </div>

              <div className="panel quick-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Quick actions</h2>
                    <p>Common tasks for your network</p>
                  </div>
                </div>

                <button
                  className="action-row"
                  onClick={() => setPage("Locations")}
                >
                  <div className="action-icon pink"><Plus size={19} /></div>
                  <div>
                    <b>Add delivery stop</b>
                    <small>Search and save a new address</small>
                  </div>
                  <ArrowRight size={17} />
                </button>

                <button
                  className="action-row"
                  onClick={() => setPage("Route Planner")}
                >
                  <div className="action-icon blue">
                    <Navigation size={19} />
                  </div>
                  <div>
                    <b>Optimize routes</b>
                    <small>Find an efficient visit order</small>
                  </div>
                  <ArrowRight size={17} />
                </button>

                <div className="mini-info">
                  <div className="mini-info-icon"><Activity size={17} /></div>
                  <div>
                    <b>Routing engine</b>
                    <p>OSRM road routing with estimate fallback when available.</p>
                  </div>
                </div>

                <div className="mini-info">
                  <div className="mini-info-icon"><Clock3 size={17} /></div>
                  <div>
                    <b>Estimated timings</b>
                    <p>Drive-time estimates may differ from actual conditions.</p>
                  </div>
                </div>
              </div>
            </section>

            <section className="panel table-panel">
              <div className="panel-heading">
                <div>
                  <h2>Delivery locations</h2>
                  <p>Your saved hub and stops</p>
                </div>
                <button className="text-btn" onClick={() => setPage("Locations")}>
                  Manage locations <ArrowRight size={15} />
                </button>
              </div>
              <LocationTable
                locations={locations}
                makeHub={makeHub}
                removeStop={removeStop}
              />
            </section>
          </>
        )}

        {page === "Locations" && (
          <>
            <section className="page-heading">
              <div>
                <div className="eyebrow">NETWORK MANAGEMENT</div>
                <h1>Locations</h1>
                <p>Search Indian addresses and manage your delivery stops.</p>
              </div>
              <span className="subtle-pill">
                <span className="status-dot online" /> India-wide search
              </span>
            </section>

            <section className="content-grid locations-grid">
              <div className="panel add-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Add a delivery stop</h2>
                    <p>Address lookup via OpenStreetMap Nominatim</p>
                  </div>
                  <div className="panel-icon"><MapPin size={20} /></div>
                </div>

                <form onSubmit={searchAddress} className="search-form">
                  <label>Search address or place</label>
                  <div className="search-input">
                    <Search size={18} />
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="e.g. Hawa Mahal, Jaipur"
                    />
                    <button type="submit" disabled={searching}>
                      {searching ? "Searching…" : "Search"}
                    </button>
                  </div>
                  <small>
                    Include a city or state for better results. Avoid rapid
                    repeated searches.
                  </small>
                </form>

                {candidates.length > 0 && (
                  <form className="stop-form" onSubmit={addStop}>
                    <label>Choose the correct address</label>
                    <div className="select-wrap">
                      <select
                        value={chosen}
                        onChange={(event) => setChosen(event.target.value)}
                      >
                        {candidates.map((candidate, index) => (
                          <option key={index} value={index}>
                            {candidate.label ||
                              candidate.display_name ||
                              candidate.address ||
                              `Result ${index + 1}`}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={16} />
                    </div>

                    {selectedCandidate && (
                      <div className="coords">
                        <span>
                          LATITUDE{" "}
                          <b>
                            {locationCoordinates(selectedCandidate)?.[0]?.toFixed(5) ?? "—"}
                          </b>
                        </span>
                        <span>
                          LONGITUDE{" "}
                          <b>
                            {locationCoordinates(selectedCandidate)?.[1]?.toFixed(5) ?? "—"}
                          </b>
                        </span>
                      </div>
                    )}

                    <label>Stop name</label>
                    <input
                      className="field"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      placeholder="e.g. Hawa Mahal"
                    />

                    <div className="two-fields">
                      <div>
                        <label>Parcel load</label>
                        <input
                          className="field"
                          type="number"
                          min="0"
                          value={demand}
                          onChange={(event) => setDemand(event.target.value)}
                        />
                      </div>
                      <div>
                        <label>Service time (minutes)</label>
                        <input
                          className="field"
                          type="number"
                          min="0"
                          value={service}
                          onChange={(event) => setService(event.target.value)}
                        />
                      </div>
                    </div>

                    <button
                      className="primary-btn full"
                      disabled={saving || !selectedCandidate}
                    >
                      <Plus size={17} />
                      {saving ? "Saving stop…" : "Add delivery stop"}
                    </button>
                  </form>
                )}
              </div>

              <div className="panel map-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Location preview</h2>
                    <p>Verify the selected point on the map</p>
                  </div>
                </div>

                <MapContainer
                  center={
                    locationCoordinates(selectedCandidate) || center
                  }
                  zoom={selectedCandidate ? 14 : 11}
                  scrollWheelZoom
                  className="map location-map"
                >
                  <TileLayer
                    attribution="&copy; OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <MapMarkers locations={locations} />
                  {selectedCandidate &&
                    locationCoordinates(selectedCandidate) && (
                      <Marker
                        position={locationCoordinates(selectedCandidate)}
                        icon={stopIcon}
                      >
                        <Popup>
                          {selectedCandidate.label ||
                            selectedCandidate.display_name ||
                            "Selected address"}
                        </Popup>
                      </Marker>
                    )}
                  <FitBounds
                    locations={
                      selectedCandidate &&
                      locationCoordinates(selectedCandidate)
                        ? [
                            {
                              latitude: locationCoordinates(selectedCandidate)[0],
                              longitude: locationCoordinates(selectedCandidate)[1],
                            },
                          ]
                        : locations
                    }
                  />
                </MapContainer>
              </div>
            </section>

            <section className="panel table-panel">
              <div className="panel-heading">
                <div>
                  <h2>Saved locations</h2>
                  <p>
                    {locations.length} total · {deliveries.length} delivery stops
                  </p>
                </div>
                <button className="secondary-btn" onClick={refresh}>
                  <RefreshCw size={15} /> Refresh
                </button>
              </div>
              <LocationTable
                locations={locations}
                makeHub={makeHub}
                removeStop={removeStop}
              />
            </section>
          </>
        )}

        {page === "Route Planner" && (
          <>
            <section className="page-heading">
              <div>
                <div className="eyebrow">ROUTE INTELLIGENCE</div>
                <h1>Route planner</h1>
                <p>
                  Optimize your courier route using your configured Python
                  algorithms.
                </p>
              </div>
              <span className="subtle-pill">
                <Activity size={14} /> {locations.length} network points
              </span>
            </section>

            <section className="planner-layout">
              <div className="panel planner-form">
                <div className="panel-heading">
                  <div>
                    <h2>Planning settings</h2>
                    <p>Choose the route objective and constraints.</p>
                  </div>
                  <div className="panel-icon"><Settings2 size={20} /></div>
                </div>

                <form onSubmit={optimize} className="stop-form">
                  <label>Optimize for</label>
                  <div className="select-wrap">
                    <select
                      value={objective}
                      onChange={(event) => setObjective(event.target.value)}
                    >
                      <option value="distance">Shortest distance</option>
                      <option value="time">Shortest estimated time</option>
                    </select>
                    <ChevronDown size={16} />
                  </div>

                  <label>Optimization algorithm</label>
                  <div className="select-wrap">
                    <select
                      value={algorithm}
                      onChange={(event) => setAlgorithm(event.target.value)}
                    >
                      {algorithms.map((item, index) => {
                        const value =
                          typeof item === "string"
                            ? item
                            : item.name || item.id;

                        return (
                          <option key={value || index} value={value}>
                            {value}
                          </option>
                        );
                      })}
                    </select>
                    <ChevronDown size={16} />
                  </div>

                  <div className="two-fields">
                    <div>
                      <label>Couriers</label>
                      <input
                        className="field"
                        type="number"
                        min="1"
                        max="8"
                        value={couriers}
                        onChange={(event) => setCouriers(event.target.value)}
                      />
                    </div>
                    <div>
                      <label>Capacity per courier</label>
                      <input
                        className="field"
                        type="number"
                        min="1"
                        value={capacity}
                        onChange={(event) => setCapacity(event.target.value)}
                      />
                    </div>
                  </div>

                  <div className="note-card">
                    <CircleHelp size={17} />
                    <p>
                      Start with nearby stops in one city. Cross-city routing
                      may be slower with public routing services.
                    </p>
                  </div>

                  <button
                    className="primary-btn full"
                    disabled={planning || deliveries.length === 0 || !hub}
                  >
                    <Route size={17} />
                    {planning ? "Optimizing…" : "Generate optimized route"}
                  </button>
                </form>
              </div>

              <div className="live-options" aria-label="Route adjustment settings">
                <label className="live-option">
                  <span>
                    <strong>Traffic adjustment</strong>
                    <small>Apply traffic-related time adjustment</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={useTraffic}
                    onChange={(event) => setUseTraffic(event.target.checked)}
                    aria-label="Apply traffic adjustment"
                  />
                </label>
                <label className="live-option">
                  <span>
                    <strong>Weather adjustment</strong>
                    <small>Apply weather-related time adjustment</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={useWeather}
                    onChange={(event) => setUseWeather(event.target.checked)}
                    aria-label="Apply weather adjustment"
                  />
                </label>
              </div>

              <div className="panel map-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Route visualization</h2>
                    <p>
                      {plan
                        ? `Route from ${hub?.location_name || "hub"}`
                        : "Your planned route will appear here"}
                    </p>
                  </div>
                  {plan && (
                    <span className="subtle-pill">
                      {plan.source === "osrm"
                        ? "OSRM road data"
                        : "Estimated distances"}
                    </span>
                  )}
                </div>

                <MapContainer
                  center={center}
                  zoom={11}
                  scrollWheelZoom
                  className="map planner-map"
                >
                  <TileLayer
                    attribution="&copy; OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <MapMarkers locations={locations} />
                  {activeRoute?.path?.length > 1 && (
                    <Polyline
                      positions={activeRoute.path}
                      pathOptions={{
                        color: "#ff4d57",
                        weight: 5,
                        opacity: 0.9,
                      }}
                    />
                  )}
                  <FitBounds locations={locations} route={activeRoute} />
                </MapContainer>
              </div>
            </section>

            {plan && (
              <>
                <section className="stat-grid result-stats">
                  <Stat
                    icon={Route}
                    label="Total road distance"
                    value={`${plan.total_km ?? "—"} km`}
                    detail="For selected plan"
                    color="violet"
                    textValue
                  />
                  <Stat
                    icon={Clock3}
                    label="Estimated drive time"
                    value={`${plan.total_min ?? "—"} min`}
                    detail="Excludes some operational delays"
                    color="blue"
                    textValue
                  />
                  <Stat
                    icon={Gauge}
                    label="Solver runtime"
                    value={`${plan.time_ms ?? "—"} ms`}
                    detail={plan.algorithm || algorithm}
                    color="orange"
                    textValue
                  />
                  <Stat
                    icon={Activity}
                    label="Data source"
                    value={plan.source === "osrm" ? "OSRM roads" : "Estimate"}
                    detail={plan.note || "Routing source status"}
                    color="green"
                    textValue
                  />
                </section>

                {plan.warnings?.length > 0 && (
                  <div className="alert warning">
                    {plan.warnings.join(" ")}
                  </div>
                )}

                {activeRoute && (
                  <section className="panel table-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Visit order & schedule</h2>
                        <p>
                          Ordered stops generated by {plan.algorithm || algorithm}
                        </p>
                      </div>
                      {Array.isArray(activeRoute.names) &&
                        activeRoute.names.length > 0 && (
                          <button
                            className="secondary-btn"
                            onClick={() => {
                              const points = activeRoute.indices
                                ?.map((index) =>
                                  locationCoordinates(locations[index])
                                )
                                .filter(Boolean);

                              if (points?.length) {
                                const url =
                                  "https://www.google.com/maps/dir/" +
                                  points
                                    .map((point) => point.join(","))
                                    .join("/");

                                window.open(
                                  url,
                                  "_blank",
                                  "noopener,noreferrer"
                                );
                              }
                            }}
                          >
                            Open in Google Maps <ArrowRight size={15} />
                          </button>
                        )}
                    </div>

                    {Array.isArray(activeRoute.names) && (
                      <div className="route-sequence">
                        {activeRoute.names.map((routeName, index) => (
                          <span
                            key={`${routeName}-${index}`}
                            className={index === 0 ? "sequence-hub" : ""}
                          >
                            {index > 0 && <ArrowRight size={13} />}
                            {routeName}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            {Object.keys(
                              (Array.isArray(plan.schedules)
                                ? plan.schedules.flat()
                                : [])[0] || {}
                            ).map((key) => (
                              <th key={key}>{key}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {(Array.isArray(plan.schedules)
                            ? plan.schedules.flat()
                            : []
                          ).map((row, index) => (
                            <tr key={index}>
                              {Object.values(row || {}).map((value, cellIndex) => (
                                <td key={cellIndex}>{String(value ?? "")}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}
              </>
            )}
          </>
        )}

        {page === "History" && <History />}

        <footer>
          RouteFlow <span>•</span> Courier route optimization{" "}
          <span>•</span> Built with React + Python
        </footer>
      </main>
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  detail,
  color,
  textValue = false,
}) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${color}`}>
        <Icon size={19} />
      </div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${textValue ? "text-value" : ""}`}>
        {value}
      </div>
      <div className="stat-detail">{detail}</div>
    </div>
  );
}

function LocationTable({ locations, makeHub, removeStop }) {
  const safeLocations = (Array.isArray(locations) ? locations : []).filter(
    Boolean
  );

  if (!safeLocations.length) {
    return <div className="empty-state">No saved locations yet.</div>;
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>LOCATION</th>
            <th>TYPE</th>
            <th>ADDRESS</th>
            <th>PARCELS</th>
            <th>SERVICE</th>
            <th>COORDINATES</th>
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {safeLocations.map((location, index) => {
            const coords = locationCoordinates(location);
            const isHub = location.location_type === "Hub";
            const id = location.location_id ?? location.id;

            return (
              <tr key={id ?? index}>
                <td>
                  <div className="location-cell">
                    <span
                      className={`table-dot ${isHub ? "hub-dot" : ""}`}
                    />
                    <b>{location.location_name || location.name || "Unnamed"}</b>
                  </div>
                </td>
                <td>
                  <span className={`type-pill ${isHub ? "hub-type" : ""}`}>
                    {location.location_type || (isHub ? "Hub" : "Delivery")}
                  </span>
                </td>
                <td
                  className="address-cell"
                  title={location.address || ""}
                >
                  {location.address || "—"}
                </td>
                <td>{location.demand ?? "—"}</td>
                <td>{location.service_min ?? "—"} min</td>
                <td className="coordinate-cell">
                  {coords
                    ? `${coords[0].toFixed(4)}, ${coords[1].toFixed(4)}`
                    : "Unavailable"}
                </td>
                <td>
                  <div className="table-actions">
                    {!isHub && (
                      <button
                        title="Make hub"
                        onClick={() => makeHub(id)}
                      >
                        <Warehouse size={15} />
                      </button>
                    )}
                    {!isHub && (
                      <button
                        title="Delete stop"
                        className="danger-icon"
                        onClick={() => removeStop(id)}
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function History() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  async function loadHistory() {
    try {
      const data = await api("/history");
      setRows(Array.isArray(data) ? data : data.runs || data.history || []);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">ACTIVITY LOG</div>
          <h1>Route history</h1>
          <p>Review saved optimization runs from the database.</p>
        </div>
        <button className="secondary-btn" onClick={loadHistory}>
          <RefreshCw size={15} /> Refresh history
        </button>
      </section>

      <section className="panel table-panel">
        <div className="panel-heading">
          <div>
            <h2>Saved runs</h2>
            <p>{rows.length} optimization runs</p>
          </div>
        </div>

        {error ? (
          <div className="empty-state">{error}</div>
        ) : rows.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {Object.keys(rows[0] || {}).map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={row?.id ?? row?.run_id ?? index}>
                    {Object.values(row || {}).map((value, cellIndex) => (
                      <td key={cellIndex}>
                        {typeof value === "object"
                          ? JSON.stringify(value)
                          : String(value ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            No saved runs yet. Generate a route to see history here.
          </div>
        )}
      </section>
    </>
  );
}
