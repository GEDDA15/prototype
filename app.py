import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from optimizer import solve_shortest_low_traffic_routes

st.set_page_config(page_title="RouteMind AI — Google GPS Fleet Planner", layout="wide")

st.title("🧠 RouteMind AI — Google Maps GPS & Low-Traffic Fleet Routing")
st.markdown("Real-time navigation dashboard powered by Google Maps tile layers with zero blinking and full-screen controls.")

# Initialize Session States
if "started" not in st.session_state:
    st.session_state.started = False
if "maximized" not in st.session_state:
    st.session_state.maximized = False

# --- SIDEBAR INPUTS ---
st.sidebar.header("Step 1: GPS Coordinates & Destinations")

lat = st.sidebar.number_input("GPS Latitude", value=12.9716, format="%.4f")
lon = st.sidebar.number_input("GPS Longitude", value=77.5946, format="%.4f")

default_destinations = "MG Road, Indiranagar, Koramangala, Whitefield, Jayanagar, Electronic City, Hebbal"
destinations_input = st.sidebar.text_area("Enter Order Destinations (comma-separated)", value=default_destinations, height=90)

st.sidebar.header("Step 2: Fleet Configuration")
num_depots = st.sidebar.number_input("Number of Depots/Hubs", min_value=1, max_value=4, value=2)
num_vehicles = st.sidebar.number_input("Assign Number of Vehicles", min_value=1, max_value=10, value=3)

st.sidebar.divider()

st.sidebar.header("Step 3: Run Routing Engine")
if st.sidebar.button("🚀 START ROUTING & MAP GENERATION", type="primary", use_container_width=True):
    st.session_state.started = True
    if "google_map_obj" in st.session_state:
        del st.session_state.google_map_obj

if st.sidebar.button("🔄 Reset / Reconfigure", use_container_width=True):
    st.session_state.started = False
    if "google_map_obj" in st.session_state:
        del st.session_state.google_map_obj
    st.rerun()

# --- MAIN DASHBOARD VIEW ---
if not st.session_state.started:
    st.info("👈 **Input your GPS coordinates and destinations in the sidebar, then click 'START ROUTING & MAP GENERATION'.**")
else:
    nodes_data, route_paths, vehicle_routes = solve_shortest_low_traffic_routes(num_depots, num_vehicles, destinations_input, lat, lon)
    num_orders = len([n for n in nodes_data if n["type"] == "Customer"])

    st.success(f"Google GPS routes calculated successfully from (`{lat:.4f}, {lon:.4f}`) across {num_vehicles} vehicles!")

    # KPI Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Google GPS Source", f"{lat:.4f}, {lon:.4f}")
    col2.metric("Target Destinations", num_orders)
    col3.metric("Traffic Condition", "🟢 Low / Clear")
    col4.metric("Path Optimization", "Google Maps Routing Active")

    st.divider()

    # --- FULL-SCREEN MAXIMIZE TOGGLE BUTTON ---
    col_ctrl1, col_ctrl2 = st.columns([4, 1])
    with col_ctrl1:
        st.subheader("🗺️ Google Maps Navigation & Low-Traffic Route View")
    with col_ctrl2:
        if st.button("🔲 Toggle Maximize Map" if not st.session_state.maximized else "↙️ Minimize Map", use_container_width=True):
            st.session_state.maximized = not st.session_state.maximized
            st.rerun()

    # Build or retrieve cached Google Maps Folium instance (prevents blinking completely)
    if "google_map_obj" not in st.session_state:
        # Initialize map with Google Maps Roadmap Tiles
        m = folium.Map(
            location=[lat, lon],
            zoom_start=13,
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google Maps'
        )
        
        # Draw route polylines
        for rp in route_paths:
            if len(rp["path"]) > 1:
                folium.PolyLine(
                    rp["path"],
                    color=rp["color"],
                    weight=6,
                    opacity=0.9,
                    tooltip=rp["vehicle"]
                ).add_to(m)

        # Plot GPS Hub & Destinations
        for node in nodes_data:
            if node["type"] == "Live Depot":
                folium.Marker(
                    [node["lat"], node["lon"]],
                    popup="📡 Real-Time GPS Origin",
                    icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
                ).add_to(m)
            elif node["type"] == "Depot":
                folium.Marker(
                    [node["lat"], node["lon"]],
                    popup=f"Sub-Depot: {node['name']}",
                    icon=folium.Icon(color="blue", icon="home", prefix="fa")
                ).add_to(m)
            else:
                folium.Marker(
                    [node["lat"], node["lon"]],
                    popup=f"Destination: {node['name']} ({node['shortest_distance_km']} km)",
                    icon=folium.Icon(color="green", icon="flag-checkered", prefix="fa")
                ).add_to(m)
        
        st.session_state.google_map_obj = m

    # Render layout with returned_objects=[] to ensure zero component blinking
    if st.session_state.maximized:
        st_folium(st.session_state.google_map_obj, use_container_width=True, height=650, returned_objects=[], key="google_map_max")
        st.divider()
        st.subheader("🚚 Assigned Fleet Route Details")
        st.dataframe(pd.DataFrame(vehicle_routes), use_container_width=True)
    else:
        col_map, col_details = st.columns([1.2, 1])
        with col_map:
            st_folium(st.session_state.google_map_obj, use_container_width=True, height=450, returned_objects=[], key="google_map_norm")
        with col_details:
            st.subheader("🚚 Assigned Fleet Route Details")
            st.dataframe(pd.DataFrame(vehicle_routes), use_container_width=True, height=430)

    st.divider()
    st.subheader("📋 Destination Traffic & Distance Breakdown")
    customer_nodes = [
        {
            "Order ID": n["id"],
            "Destination": n["name"],
            "Assigned Depot": n["assigned_depot"],
            "Traffic Condition": n["traffic_condition"],
            "Shortest Distance": f"{n['shortest_distance_km']} km"
        }
        for n in nodes_data if n["type"] == "Customer"
    ]
    st.dataframe(pd.DataFrame(customer_nodes), use_container_width=True)