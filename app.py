
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from routeflow import db, geo, live, planner


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="RouteFlow | Courier Operations",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM FRONTEND DESIGN
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #0b1220;
    --panel: #111c2e;
    --panel-hover: #17263d;
    --border: #263750;
    --text: #edf3fc;
    --muted: #96a9c0;
    --accent: #38d6c5;
    --green: #4ade80;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

[data-testid="stHeader"] {
    background: rgba(11, 18, 32, 0.94);
}

.block-container {
    max-width: 1500px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: #0e1829;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

[data-testid="stSidebar"] hr {
    border-color: var(--border);
}

[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 7px;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 10px 12px;
    border: 1px solid transparent;
    border-radius: 10px;
    transition: 0.2s;
}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: #17263d;
    border-color: #2b425e;
}

h1, h2, h3 {
    font-family: 'Manrope', sans-serif;
    letter-spacing: -0.5px;
}

h1 {
    font-size: 2rem;
    font-weight: 800;
}

h2 {
    font-size: 1.4rem;
    margin-top: 1.2rem;
}

.hero {
    padding: 30px;
    margin-bottom: 24px;
    border: 1px solid #29485a;
    border-radius: 20px;
    background:
        radial-gradient(
            circle at 90% 10%,
            rgba(56, 214, 197, 0.18),
            transparent 32%
        ),
        linear-gradient(120deg, #14243b, #12333d);
}

.hero h1 {
    font-size: 2.1rem;
    color: #ffffff;
    margin: 0 0 10px;
}

.hero p {
    color: #bacbde;
    max-width: 800px;
    line-height: 1.7;
    margin: 0;
}

.eyebrow {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 1.8px;
    color: var(--accent);
    margin-bottom: 10px;
}

.page-subtitle {
    color: var(--muted);
    margin-top: -10px;
    margin-bottom: 24px;
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #142137, #111b2d);
    border: 1px solid var(--border);
    border-radius: 15px;
    padding: 18px;
    min-height: 105px;
}

[data-testid="stMetricLabel"] {
    color: #a9bad0;
}

[data-testid="stMetricValue"] {
    color: #f5f8fc;
    font-weight: 800;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--border) !important;
    border-radius: 14px;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stPlotlyChart"] {
    background: #101a2b;
    border: 1px solid #22354e;
    border-radius: 15px;
    padding: 8px;
    overflow: hidden;
}

[data-testid="stForm"] {
    background: #101a2b;
    border: 1px solid var(--border);
    border-radius: 15px;
    padding: 20px;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] [data-baseweb="select"] {
    border-radius: 9px !important;
}

[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button,
[data-testid="stLinkButton"] a {
    border-radius: 10px;
    font-weight: 700;
    min-height: 42px;
    transition: 0.2s;
}

[data-testid="stButton"] button:hover,
[data-testid="stDownloadButton"] button:hover {
    transform: translateY(-1px);
    border-color: var(--accent);
}

[data-testid="stButton"] button[kind="primary"] {
    background: #28bfb2;
    border: 1px solid #40d8c9;
    color: #061720;
}

[data-testid="stButton"] button[kind="primary"]:hover {
    background: #52dfd0;
}

[data-testid="stAlert"] {
    border-radius: 12px;
}

.status {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 30px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
    margin: 5px 0 15px;
}

.status-live {
    color: #7af0d7;
    background: #0d3b39;
    border: 1px solid #1b756b;
}

.status-estimated {
    color: #f7cd75;
    background: #392b18;
    border: 1px solid #785b2b;
}

hr {
    border-color: var(--border);
}

@media (max-width: 760px) {
    .block-container {
        padding: 1rem 0.8rem 2rem;
    }

    .hero {
        padding: 22px;
    }

    .hero h1 {
        font-size: 1.6rem;
    }
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTS AND HELPERS
# ============================================================

COLORS = [
    "#22d3ee", "#f97316", "#a78bfa", "#4ade80",
    "#f43f5e", "#facc15", "#38bdf8", "#fb7185"
]

OBJECTIVES = {
    "Shortest distance": "distance",
    "Fastest adjusted travel time": "time",
}


def source_badge(source):
    if source == "osrm":
        return (
            '<span class="status status-live">'
            '● ROAD ROUTING · OSRM'
            '</span>'
        )

    return (
        '<span class="status status-estimated">'
        '● ESTIMATED · OFFLINE FALLBACK'
        '</span>'
    )


def zoom_for(latitudes, longitudes):
    span = max(
        max(latitudes) - min(latitudes),
        (max(longitudes) - min(longitudes)) * 0.9,
        0.01,
    )
    return max(3, min(15, math.log2(562 / (span * 1.3))))


def base_map(latitudes, longitudes, height=520):
    fig = go.Figure()

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#101a2b",
        plot_bgcolor="#101a2b",
        font=dict(color="#e2e8f0"),
        legend=dict(
            bgcolor="rgba(17,26,46,0.85)",
            font=dict(color="#e2e8f0"),
        ),
        map=dict(
            style="carto-darkmatter",
            center=dict(
                lat=sum(latitudes) / len(latitudes),
                lon=sum(longitudes) / len(longitudes),
            ),
            zoom=zoom_for(latitudes, longitudes),
        ),
    )

    return fig


def network_map(locations):
    latitudes = [loc["latitude"] for loc in locations]
    longitudes = [loc["longitude"] for loc in locations]

    fig = base_map(latitudes, longitudes, height=440)

    for loc_type, color, size in [
        ("Hub", "#f43f5e", 20),
        ("Delivery", "#22d3ee", 13),
    ]:
        selected = [
            loc for loc in locations
            if loc["location_type"] == loc_type
        ]

        if selected:
            fig.add_trace(go.Scattermap(
                lat=[loc["latitude"] for loc in selected],
                lon=[loc["longitude"] for loc in selected],
                mode="markers",
                name=loc_type,
                marker=dict(size=size, color=color),
                text=[loc["location_name"] for loc in selected],
                hovertemplate="%{text}<extra></extra>",
            ))

    return fig


def route_map(locations, routes, use_roads=True):
    latitudes = [loc["latitude"] for loc in locations]
    longitudes = [loc["longitude"] for loc in locations]
    fig = base_map(latitudes, longitudes)

    source = "osrm"

    for courier_index, route in enumerate(routes):
        color = COLORS[courier_index % len(COLORS)]

        ordered_points = tuple(
            (locations[i]["latitude"], locations[i]["longitude"])
            for i in route
        )

        if use_roads:
            geometry = geo.route_geometry(ordered_points)
            path = geometry["path"]

            if geometry["source"] != "osrm":
                source = "estimate"
        else:
            path = list(ordered_points)
            source = "estimate"

        fig.add_trace(go.Scattermap(
            lat=[point[0] for point in path],
            lon=[point[1] for point in path],
            mode="lines",
            line=dict(width=4, color=color),
            name=f"Courier {courier_index + 1}",
            hoverinfo="skip",
        ))

        stops = route[1:-1]

        if stops:
            fig.add_trace(go.Scattermap(
                lat=[locations[i]["latitude"] for i in stops],
                lon=[locations[i]["longitude"] for i in stops],
                mode="markers+text",
                text=[str(i + 1) for i in range(len(stops))],
                textfont=dict(color="#0b1220", size=12),
                textposition="middle center",
                marker=dict(size=22, color=color),
                name=f"Courier {courier_index + 1} stops",
                showlegend=False,
                customdata=[
                    locations[i]["location_name"] for i in stops
                ],
                hovertemplate="%{customdata}<extra></extra>",
            ))

    hub = locations[0]

    fig.add_trace(go.Scattermap(
        lat=[hub["latitude"]],
        lon=[hub["longitude"]],
        mode="markers",
        name="Hub",
        marker=dict(size=24, color="#f43f5e"),
        text=[hub["location_name"]],
        hovertemplate="HUB: %{text}<extra></extra>",
    ))

    return fig, source


def objective_matrix(kind, distance_matrix, adjusted_duration):
    if kind == "distance":
        return distance_matrix

    return [
        [seconds / 60.0 for seconds in row]
        for row in adjusted_duration
    ]


def load_context():
    locations = db.list_locations()
    points = tuple(
        (loc["latitude"], loc["longitude"])
        for loc in locations
    )
    return locations, points


def render_table(data):
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

try:
    locations, points = load_context()
except Exception as exc:
    st.error(f"Could not load the delivery network: {exc}")
    st.stop()

if not locations:
    st.error("No locations are configured. Add a hub and delivery stops first.")
    st.stop()

hub = locations[0]

with st.sidebar:
    st.markdown(
        """
        <div style="font-size:1.5rem;font-weight:850;color:#f4f8ff">
            🚚 RouteFlow
        </div>
        <div style="font-size:.75rem;color:#91a8c1;letter-spacing:1.3px">
            COURIER OPERATIONS
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Route planning workspace")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "Locations",
            "Route Planner",
            "Benchmark Lab",
            "History",
        ],
        key="navigation_page",
        label_visibility="collapsed",
    )

    st.divider()

    st.caption("Location search supports places across India")
    st.caption(f"Database: {db.backend_name()}")
    st.caption(f"{len(locations)} locations")
    st.caption(f"{max(len(locations) - 1, 0)} delivery stops")

    with st.expander("Data sources"):
        st.markdown(
            """
            - Road routing: OSRM
            - Address search: Nominatim
            - Map display: OpenStreetMap-compatible tiles
            - Weather: Open-Meteo
            - Congestion: time-of-day model
            """
        )


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">ROUTE INTELLIGENCE PLATFORM</div>
            <h1>Courier Route Optimization</h1>
            <p>
                Plan smarter deliveries with road-based routing,
                weather-aware ETAs, and optimization algorithms.
                Manage stops, compare courier plans, and track your
                operations from one workspace.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    @st.fragment(run_every=60)
    def live_weather_panel():
        context = live.live_context(
            hub["latitude"],
            hub["longitude"],
        )

        weather = context["weather"]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Local time",
            context["now"].strftime("%H:%M"),
            context["now"].strftime("%a, %d %b"),
        )

        temperature = weather["temperature_c"]
        temperature_text = (
            f"{temperature:.0f} °C"
            if temperature is not None
            else "Unavailable"
        )

        c2.metric(
            "Hub weather",
            weather["description"],
            temperature_text,
        )

        c3.metric(
            "Weather adjustment",
            f"x{context['weather_factor']:.2f}",
        )

        c4.metric(
            "Congestion model",
            f"x{context['traffic_factor']:.2f}",
        )

        if not weather["ok"]:
            st.caption(
                "Weather service unavailable. Offline estimates are being used."
            )
        else:
            st.caption(
                "Weather refreshes every 60 seconds. Congestion is modelled, "
                "not measured live traffic."
            )

    try:
        live_weather_panel()
    except Exception as exc:
        st.info(f"Live weather is temporarily unavailable: {exc}")

    st.subheader("Delivery network")

    left, right = st.columns([1.5, 1])

    with left:
        st.plotly_chart(
            network_map(locations),
            use_container_width=True,
        )

    with right:
        st.markdown("### Network summary")

        network_data = pd.DataFrame([
            {
                "Location": loc["location_name"],
                "Type": loc["location_type"],
                "Parcels": loc["demand"],
                "Service (min)": loc["service_min"],
            }
            for loc in locations
        ])

        render_table(network_data)

        if st.button(
            "Open Route Planner",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["navigation_page"] = "Route Planner"
            st.rerun()

    runs = db.list_runs()

    if not runs.empty:
        st.subheader("Recent optimization runs")
        render_table(
            runs.head(5)[[
                "created_at",
                "algorithm_name",
                "objective",
                "n_couriers",
                "total_distance_km",
                "total_duration_min",
            ]]
        )


# ============================================================
# LOCATION MANAGEMENT
# ============================================================

elif page == "Locations":

    st.title("Location management")

    st.markdown(
        '<div class="page-subtitle">'
        'Manage the hub and delivery stops in your network.'
        '</div>',
        unsafe_allow_html=True,
    )

    location_data = pd.DataFrame([
        {
            "ID": loc["location_id"],
            "Name": loc["location_name"],
            "Type": loc["location_type"],
            "Address": loc["address"],
            "Latitude": round(loc["latitude"], 5),
            "Longitude": round(loc["longitude"], 5),
            "Parcels": loc["demand"],
            "Service (min)": loc["service_min"],
        }
        for loc in locations
    ])

    render_table(location_data)

    st.subheader("Add a delivery stop")

    query = st.text_input(
        "Search for an address or place anywhere in India",
        placeholder="e.g. Hawa Mahal, Jaipur or MI Road, Jaipur",
        help="Search for a city, locality, landmark, PIN code, or full Indian address.",
    )

    st.caption(
        "Free geocoding uses OpenStreetMap Nominatim. "
        "Searches may take a few seconds and are subject to public-service usage limits."
    )

    if st.button("Search address"):
        if not query.strip():
            st.warning("Enter a place or address to search.")
        else:
            with st.spinner("Searching addresses across India..."):
                st.session_state["geo_results"] = geo.geocode(query)

            if not st.session_state["geo_results"]:
                st.warning(
                    "No results found. Try adding the city and state, "
                    "or enter coordinates manually below."
                )

    geo_results = st.session_state.get("geo_results", [])
    choice = None

    if geo_results:
        selected_index = st.selectbox(
            "Choose the correct address",
            range(len(geo_results)),
            format_func=lambda i: geo_results[i]["label"][:110],
        )
        choice = geo_results[selected_index]

    with st.form("add_delivery_stop"):
        stop_name = st.text_input(
            "Stop name",
            value=choice["label"].split(",")[0] if choice else "",
        )

        c1, c2 = st.columns(2)

        latitude = c1.number_input(
            "Latitude",
            value=float(choice["lat"]) if choice else float(hub["latitude"]),
            format="%.6f",
        )

        longitude = c2.number_input(
            "Longitude",
            value=float(choice["lon"]) if choice else float(hub["longitude"]),
            format="%.6f",
        )

        c3, c4 = st.columns(2)

        demand = c3.number_input(
            "Parcel load",
            min_value=1,
            max_value=1000,
            value=1,
        )

        service_time = c4.number_input(
            "Service time (minutes)",
            min_value=0,
            max_value=120,
            value=5,
        )

        submitted = st.form_submit_button(
            "Add delivery stop",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not stop_name.strip():
                st.error("Enter a name for the delivery stop.")
            else:
                try:
                    db.add_location(
                        stop_name.strip(),
                        choice["label"] if choice else "",
                        latitude,
                        longitude,
                        demand,
                        service_time,
                    )

                    geo.road_matrix.cache_clear()
                    geo.route_geometry.cache_clear()
                    st.session_state.pop("geo_results", None)
                    st.session_state.pop("routeflow_plan", None)

                    st.success("Delivery stop added successfully.")
                    st.rerun()

                except Exception as exc:
                    st.error(f"Could not add the stop: {exc}")

    st.divider()
    st.subheader("Edit or remove a location")

    location_names = {
        loc["location_id"]: loc["location_name"]
        for loc in locations
    }

    selected_id = st.selectbox(
        "Select a location",
        list(location_names),
        format_func=location_names.get,
    )

    selected_location = next(
        loc for loc in locations
        if loc["location_id"] == selected_id
    )

    c1, c2, c3, c4 = st.columns(4)

    new_demand = c1.number_input(
        "Parcel load",
        min_value=0,
        max_value=1000,
        value=int(selected_location["demand"]),
        key=f"demand_{selected_id}",
    )

    new_service = c2.number_input(
        "Service minutes",
        min_value=0,
        max_value=120,
        value=int(selected_location["service_min"]),
        key=f"service_{selected_id}",
    )

    if c3.button("Save changes", use_container_width=True):
        db.update_location(
            selected_id,
            new_demand,
            new_service,
        )
        st.session_state.pop("routeflow_plan", None)
        st.success("Location updated.")
        st.rerun()

    if c4.button("Make hub", use_container_width=True):
        db.set_hub(selected_id)
        geo.road_matrix.cache_clear()
        geo.route_geometry.cache_clear()
        st.session_state.pop("routeflow_plan", None)
        st.success("Hub updated.")
        st.rerun()

    if st.button("Reset to demo locations"):
        db.reset_demo()
        geo.road_matrix.cache_clear()
        geo.route_geometry.cache_clear()
        st.session_state.pop("routeflow_plan", None)
        st.session_state.pop("geo_results", None)
        st.rerun()


# ============================================================
# ROUTE PLANNER
# ============================================================

elif page == "Route Planner":

    st.title("Route planner")

    st.markdown(
        '<div class="page-subtitle">'
        'Choose your optimization goal, configure the fleet, and calculate routes.'
        '</div>',
        unsafe_allow_html=True,
    )

    if len(locations) < 2:
        st.info("Add at least one delivery stop before optimizing.")
        st.stop()

    if len(locations) > 60:
        st.warning(
            "Large networks may take longer to route. "
            "Consider testing with fewer stops first."
        )

    with st.form("route_planner_form"):

        c1, c2 = st.columns(2)

        objective_label = c1.selectbox(
            "Optimization objective",
            list(OBJECTIVES),
        )

        algorithm_choices = c2.multiselect(
            "Algorithms to compare",
            list(planner.ALGORITHMS),
            default=[
                "Held-Karp DP (exact)",
                "Nearest Neighbour",
                "NN + 2-opt/Or-opt",
            ],
        )

        c3, c4, c5 = st.columns(3)

        courier_count = c3.number_input(
            "Number of couriers",
            min_value=1,
            max_value=8,
            value=1,
        )

        capacity = c4.number_input(
            "Parcel capacity per courier",
            min_value=1,
            max_value=5000,
            value=14,
        )

        departure_time = c5.time_input(
            "Departure time",
            value=None,
        )

        c6, c7, c8 = st.columns(3)

        use_weather = c6.checkbox("Apply weather adjustment", True)
        use_traffic = c7.checkbox("Apply congestion model", True)
        use_roads = c8.checkbox("Draw road geometry", True)

        optimize_clicked = st.form_submit_button(
            "Optimize delivery routes",
            type="primary",
            use_container_width=True,
        )

    if optimize_clicked:

        if not algorithm_choices:
            st.warning("Select at least one algorithm.")

        else:
            try:
                with st.spinner(
                    "Getting road distances and calculating optimal routes..."
                ):
                    road_data = geo.road_matrix(points)

                    context = live.live_context(
                        hub["latitude"],
                        hub["longitude"],
                        use_weather,
                        use_traffic,
                    )

                    adjusted_duration = [
                        [
                            seconds * context["factor"]
                            for seconds in row
                        ]
                        for row in road_data["duration_s"]
                    ]

                    objective = OBJECTIVES[objective_label]

                    objective_cost = objective_matrix(
                        objective,
                        road_data["distance_km"],
                        adjusted_duration,
                    )

                    demands = [
                        loc["demand"]
                        for loc in locations
                    ]

                    clusters, warnings = planner.assign_stops(
                        objective_cost,
                        demands,
                        courier_count,
                        capacity,
                    )

                    results, skipped = planner.compare(
                        algorithm_choices,
                        objective_cost,
                        road_data["distance_km"],
                        adjusted_duration,
                        clusters,
                    )

                if not results:
                    st.error(
                        "No algorithm completed successfully. "
                        + " ".join(skipped)
                    )

                else:
                    key = (
                        "total_km"
                        if objective == "distance"
                        else "total_min"
                    )

                    results.sort(
                        key=lambda result: (
                            round(result[key], 6),
                            result["time_ms"],
                        )
                    )

                    start_datetime = context["now"]

                    if departure_time is not None:
                        start_datetime = context["now"].replace(
                            hour=departure_time.hour,
                            minute=departure_time.minute,
                            second=0,
                            microsecond=0,
                        )

                    st.session_state["routeflow_plan"] = {
                        "results": results,
                        "warnings": warnings,
                        "skipped": skipped,
                        "objective": objective,
                        "road_data": road_data,
                        "adjusted_duration": adjusted_duration,
                        "context": context,
                        "start": start_datetime,
                        "locations": locations,
                        "use_roads": use_roads,
                    }

            except Exception as exc:
                st.error(f"Route optimization failed: {exc}")

    plan = st.session_state.get("routeflow_plan")

    if plan:

        if plan["locations"] != locations:
            st.warning(
                "The delivery network has changed. "
                "Optimize again to calculate updated routes."
            )

        for message in plan["warnings"] + plan["skipped"]:
            st.warning(message)

        results = plan["results"]
        objective = plan["objective"]
        road_data = plan["road_data"]
        context = plan["context"]

        st.markdown(
            source_badge(road_data["source"]),
            unsafe_allow_html=True,
        )

        if road_data.get("note"):
            st.caption(road_data["note"])

        selected_algorithm = st.selectbox(
            "Display route for",
            [result["algorithm"] for result in results],
        )

        selected_result = next(
            result for result in results
            if result["algorithm"] == selected_algorithm
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Total distance",
            f"{selected_result['total_km']:.1f} km",
        )

        c2.metric(
            "Adjusted driving time",
            f"{selected_result['total_min']:.0f} min",
        )

        c3.metric(
            "Travel-time adjustment",
            f"x{context['factor']:.2f}",
            delta_color="off",
        )

        c4.metric(
            "Solver runtime",
            f"{selected_result['time_ms']:.2f} ms",
        )

        st.subheader("Route map")

        figure, geometry_source = route_map(
            plan["locations"],
            selected_result["routes"],
            use_roads=plan["use_roads"],
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

        if geometry_source != "osrm":
            st.caption(
                "Road geometry was unavailable, so straight-line route segments "
                "are displayed instead."
            )

        location_names = [
            loc["location_name"]
            for loc in plan["locations"]
        ]

        coordinates = [
            (loc["latitude"], loc["longitude"])
            for loc in plan["locations"]
        ]

        service_times = [
            loc["service_min"]
            for loc in plan["locations"]
        ]

        st.subheader("Courier schedules and ETAs")

        tabs = st.tabs([
            f"Courier {i + 1}"
            for i in range(len(selected_result["routes"]))
        ])

        export_rows = []

        for i, (tab, route) in enumerate(
            zip(tabs, selected_result["routes"])
        ):

            with tab:
                distance, minutes = planner.route_totals(
                    route,
                    road_data["distance_km"],
                    plan["adjusted_duration"],
                )

                parcel_load = sum(
                    plan["locations"][stop]["demand"]
                    for stop in route[1:-1]
                )

                st.caption(
                    f"{len(route) - 2} stops · "
                    f"{distance:.1f} km · "
                    f"{minutes:.0f} min driving · "
                    f"{parcel_load} parcels"
                )

                schedule = planner.build_schedule(
                    route,
                    location_names,
                    plan["adjusted_duration"],
                    road_data["distance_km"],
                    service_times,
                    plan["start"],
                )

                render_table(pd.DataFrame(schedule))

                for row in schedule:
                    export_rows.append({
                        "Courier": i + 1,
                        **row,
                    })

                if len(route) - 2 <= 9:
                    st.link_button(
                        "Open route in Google Maps",
                        planner.google_maps_url(route, coordinates),
                    )

        st.subheader("Algorithm comparison")

        key = (
            "total_km"
            if objective == "distance"
            else "total_min"
        )

        exact_values = [
            result[key]
            for result in results
            if result["algorithm"] in planner.EXACT
        ]

        best_exact = min(exact_values) if exact_values else None

        comparison = pd.DataFrame([
            {
                "Algorithm": result["algorithm"],
                "Distance (km)": round(result["total_km"], 2),
                "Drive time (min)": round(result["total_min"], 1),
                "Runtime (ms)": round(result["time_ms"], 3),
                "Gap vs exact (%)": (
                    round((result[key] - best_exact) / best_exact * 100, 2)
                    if best_exact is not None and best_exact > 0
                    else None
                ),
            }
            for result in results
        ])

        render_table(comparison)

        c1, c2 = st.columns(2)

        c1.plotly_chart(
            px.bar(
                comparison,
                x="Algorithm",
                y="Distance (km)",
                color="Algorithm",
                title="Total route distance",
            ),
            use_container_width=True,
        )

        c2.plotly_chart(
            px.bar(
                comparison,
                x="Algorithm",
                y="Runtime (ms)",
                color="Algorithm",
                title="Algorithm runtime",
            ),
            use_container_width=True,
        )

        st.divider()

        c1, c2 = st.columns(2)

        if c1.button(
            "Save result to history",
            type="primary",
            use_container_width=True,
        ):

            try:
                db.save_run({
                    "algorithm_name": selected_result["algorithm"],
                    "objective": objective,
                    "n_stops": len(plan["locations"]) - 1,
                    "n_couriers": len(selected_result["routes"]),
                    "total_distance_km": selected_result["total_km"],
                    "total_duration_min": selected_result["total_min"],
                    "route_sequence": " | ".join(
                        " → ".join(location_names[i] for i in route)
                        for route in selected_result["routes"]
                    ),
                    "execution_time_ms": selected_result["time_ms"],
                    "data_source": road_data["source"],
                    "delay_factor": context["factor"],
                })

                st.success("Route saved to history.")

            except Exception as exc:
                st.error(f"Could not save the route: {exc}")

        c2.download_button(
            "Export courier schedule (CSV)",
            pd.DataFrame(export_rows).to_csv(index=False),
            file_name="routeflow_schedule.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ============================================================
# BENCHMARK LAB
# ============================================================

elif page == "Benchmark Lab":

    st.title("Benchmark Lab")

    st.markdown(
        '<div class="page-subtitle">'
        'Compare runtime and solution quality on repeatable test instances.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Random instances are used to compare exact algorithms against "
        "heuristics. Benchmark inputs are separate from your saved delivery network."
    )

    c1, c2, c3 = st.columns(3)

    max_stops = c1.slider(
        "Maximum stops",
        min_value=4,
        max_value=14,
        value=12,
    )

    trials = c2.slider(
        "Trials per size",
        min_value=1,
        max_value=5,
        value=3,
    )

    seed = c3.number_input(
        "Random seed",
        min_value=0,
        max_value=9999,
        value=42,
    )

    if st.button(
        "Run benchmark",
        type="primary",
        use_container_width=True,
    ):

        with st.spinner("Running algorithm benchmarks..."):
            st.session_state["benchmark_data"] = pd.DataFrame(
                planner.benchmark(
                    list(range(4, max_stops + 1)),
                    trials,
                    int(seed),
                )
            )

    benchmark_data = st.session_state.get("benchmark_data")

    if benchmark_data is not None:

        c1, c2 = st.columns(2)

        c1.plotly_chart(
            px.line(
                benchmark_data,
                x="n_stops",
                y="time_ms",
                color="algorithm",
                markers=True,
                log_y=True,
                title="Runtime by problem size",
                labels={
                    "time_ms": "Runtime (ms)",
                    "n_stops": "Number of stops",
                },
            ),
            use_container_width=True,
        )

        gap_data = benchmark_data.dropna(subset=["gap_pct"])

        gap_data = gap_data[
            ~gap_data["algorithm"].isin(planner.EXACT)
        ]

        c2.plotly_chart(
            px.line(
                gap_data,
                x="n_stops",
                y="gap_pct",
                color="algorithm",
                markers=True,
                title="Heuristic gap vs exact solution",
                labels={
                    "gap_pct": "Gap above optimum (%)",
                    "n_stops": "Number of stops",
                },
            ),
            use_container_width=True,
        )

        render_table(benchmark_data.round(4))


# ============================================================
# HISTORY
# ============================================================

elif page == "History":

    st.title("Results history")

    st.markdown(
        '<div class="page-subtitle">'
        'Review and export previously saved route optimization runs.'
        '</div>',
        unsafe_allow_html=True,
    )

    history = db.list_runs()

    if history.empty:

        st.info(
            "No saved runs yet. Calculate a route in Route Planner "
            "and choose Save result to history."
        )

    else:

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Saved runs",
            len(history),
        )

        c2.metric(
            "Best recorded distance",
            f"{history['total_distance_km'].min():.1f} km",
        )

        c3.metric(
            "Algorithms used",
            history["algorithm_name"].nunique(),
        )

        render_table(history)

        history["created_at"] = pd.to_datetime(
            history["created_at"]
        )

        st.plotly_chart(
            px.line(
                history.sort_values("created_at"),
                x="created_at",
                y="total_distance_km",
                color="algorithm_name",
                markers=True,
                title="Saved route distance over time",
            ),
            use_container_width=True,
        )

        st.download_button(
            "Download history as CSV",
            history.to_csv(index=False),
            file_name="routeflow_history.csv",
            mime="text/csv",
        )

        if st.button("Clear history"):
            db.clear_runs()
            st.rerun()
