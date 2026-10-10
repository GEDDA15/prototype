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

# Reset button at top of sidebar
if st.sidebar.button("🔄 Reset Configuration", use_container_width=True):
    st.session_state.started = False
    if "google_map_obj" in st.session_state:
        del st.session_state.google_map_obj
    st.rerun()

st.sidebar.divider()

# --- STEP 1: GPS & Number of Orders ---
st.sidebar.header("Step 1: GPS & Number of Orders")
lat = st.sidebar.number_input("GPS Latitude", value=18.1124, format="%.4f")
lon = st.sidebar.number_input("GPS Longitude", value=83.4125, format="%.4f")

num_orders = st.sidebar.number_input("Number of Target Orders", min_value=1, max_value=20, value=4)

default_destinations = "Vizianagaram Fort Front Gate, Vizianagaram Clock Tower, Kondakarakam Hill, Jagaram Waterfalls"
destinations_input = st.sidebar.text_area(f"Enter {num_orders} Order Destinations (comma-separated)", value=default_destinations, height=80)

st.sidebar.divider()

# --- STEP 2: Depot Selection ---
st.sidebar.header("Step 2: Depot Selection")
depot_options = ["North Hub Depot", "South Transit Sub-Depot", "East Express Hub", "West Distribution Center"]
selected_depots = st.sidebar.multiselect(
    "Select Active Sub-Depots",
    depot_options,
    default=["North Hub Depot", "South Transit Sub-Depot"]
)

st.sidebar.divider()

# --- STEP 3: Vehicle Selection ---
st.sidebar.header("Step 3: Vehicle Selection")
vehicle_options = ["Vehicle V1 (Van)", "Vehicle V2 (Truck)", "Vehicle V3 (Bike)", "Vehicle V4 (EV)", "Vehicle V5 (Heavy Loader)"]
selected_vehicles = st.sidebar.multiselect(
    "Select Active Fleet Vehicles",
    vehicle_options,
    default=["Vehicle V1 (Van)", "Vehicle V2 (Truck)", "Vehicle V3 (Bike)"]
)

st.sidebar.divider()

# --- RUN BUTTON ---
if st.sidebar.button("🚀 START ROUTING & MAP GENERATION", type="primary", use_container_width=True):
    if not selected_vehicles:
        st.sidebar.error("Please select at least one vehicle.")
    elif not selected_depots:
        st.sidebar.error("Please select at least one depot.")
    else:
        st.session_state.started = True
        if "google_map_obj" in st.session_state:
            del st.session_state.google_map_obj
        st.rerun()

# --- MAIN DASHBOARD VIEW ---
if not st.session_state.started:
    st.info("👈 **Configure your orders, depots, and vehicles in the sidebar, then click 'START ROUTING & MAP GENERATION'.**")
else:
    nodes_data, route_paths, vehicle_routes = solve_shortest_low_traffic_routes(
        selected_depots, selected_vehicles, destinations_input, lat, lon
    )
    total_orders = len([n for n in nodes_data if n["type"] == "Customer"])

    st.success(f"Google GPS routes calculated successfully from (`{lat:.4f}, {lon:.4f}`) across {len(selected_vehicles)} vehicles and {len(selected_depots)} sub-depots!")

    # KPI Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Google GPS Source", f"{lat:.4f}, {lon:.4f}")
    col2.metric("Target Destinations", total_orders)
    col3.metric("Active Fleet", len(selected_vehicles))
    col4.metric("Traffic Condition", "🟢 Low / Clear")

    st.divider()

    # --- FULL-SCREEN MAXIMIZE TOGGLE BUTTON ---
    col_ctrl1, col_ctrl2 = st.columns([4, 1])
    with col_ctrl1:
        st.subheader("🗺️ Google Maps Navigation & Low-Traffic Route View")
    with col_ctrl2:
        if st.button("🔲 Toggle Maximize Map" if not st.session_state.maximized else "↙️ Minimize Map", use_container_width=True):
            st.session_state.maximized = not st.session_state.maximized
            st.rerun()

    # Build or retrieve cached Google Maps Folium instance
    if "google_map_obj" not in st.session_state:
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

    # Render layout
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