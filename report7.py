import pandas as pd
import plotly.express as px
import datetime
import os
import glob
import streamlit as st

# =========================
#  CONFIG
# =========================
st.set_page_config(layout="wide", page_title=" Drone Multi-Flight Dashboard")

# DATA_FOLDER = r"C:\Users\actionfi\Desktop\Projects\Aakash\Aakash_api_etccc\QGC data basic\Datassss\dataforserver"

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "dataforserver")


# =========================
#  REQUIRED COLUMNS
# =========================
required_cols = [
    "Timestamp", "groundSpeed", "airSpeed", "altitudeRelative", "altitudeAMSL",
    "flightDistance", "flightTime", "distanceToHome",
    "battery0.voltage", "battery0.current", "battery0.percentRemaining", "battery0.instantPower",
    "gps.lat", "gps.lon",
    "clock.currentDate", "clock.currentTime",
]

# =========================
#  LOAD & PROCESS DATA
# =========================
flight_summaries, gps_data, all_dfs = [], [], []
all_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))

for i, file in enumerate(all_files):
    df = pd.read_csv(file, parse_dates=["Timestamp"], low_memory=False)

    # Keep only required columns that exist
    available_cols = [col for col in required_cols if col in df.columns]
    df = df[available_cols].copy()

    # Add missing columns as NaN
    for col in required_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # Flight ID + time
    flight_id = f"flight_{i+1}"
    df["flight_id"] = flight_id
    df["date"] = pd.to_datetime(df["clock.currentDate"], errors="coerce")
    df["time"] = pd.to_datetime(df["clock.currentTime"], format="%H:%M:%S", errors="coerce")
    print("df:",df)
    # Drop invalid rows
    df = df[df["date"].notna()].reset_index(drop=True)

    # Convert numeric columns safely
    for col in ["flightDistance", "altitudeRelative", "groundSpeed", "airSpeed",
                "battery0.percentRemaining", "battery0.instantPower"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # FlightTime conversion
    df["flightTime"] = pd.to_timedelta(df["flightTime"], errors="coerce")

    # Per-flight summary
    summary = {
        "flight_id": flight_id,
        "flight_time": df["flightTime"].max(),
        "flight_distance": df["flightDistance"].max(),
        "max_altitude": df["altitudeRelative"].max(),
        "max_ground_speed": df["groundSpeed"].max(),
        "max_air_speed": df["airSpeed"].max(),
        "min_battery": df["battery0.percentRemaining"].min(),
        "avg_power": round(df["battery0.instantPower"].mean(), 2),
        "avg_altitude": round(df["altitudeRelative"].mean(), 2),
        "avg_flight_time": df["flightTime"].mean(),
        "avg_flight_distance": round(df["flightDistance"].mean(), 2),
        "avg_ground_speed": round(df["groundSpeed"].mean(), 2),
        "avg_air_speed": round(df["airSpeed"].mean(), 2),
        "avg_battery_remaining": round(df["battery0.percentRemaining"].mean(), 2),
    }
    flight_summaries.append(summary)

    # GPS Data
    gps_data.append(df[["gps.lat", "gps.lon", "flight_id"]])

    # Save raw data
    all_dfs.append(df)

# Combine summaries & GPS & full data
flight_summary = pd.DataFrame(flight_summaries)
gps_all = pd.concat(gps_data, ignore_index=True) if gps_data else pd.DataFrame()
df_all = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

# =========================
#  KPIs HELPERS
# =========================
def format_timedelta(td):
    if pd.isna(td): return "N/A"
    total_seconds = int(td.total_seconds())
    h, r = divmod(total_seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02}"

def fmt(value, unit=""):
    return f"{float(value):.2f}{unit}" if pd.notna(value) else "N/A"

# =========================
#  KPI CALCULATIONS
# =========================
total_flights = flight_summary["flight_id"].nunique()
total_flight_time = flight_summary["flight_time"].sum(skipna=True)
total_flight_distance = pd.to_numeric(flight_summary["flight_distance"], errors="coerce").sum(skipna=True)
max_altitude = pd.to_numeric(flight_summary["max_altitude"], errors="coerce").max(skipna=True)
max_ground_speed = pd.to_numeric(flight_summary["max_ground_speed"], errors="coerce").max(skipna=True)
max_air_speed = pd.to_numeric(flight_summary["max_air_speed"], errors="coerce").max(skipna=True)
min_battery = pd.to_numeric(flight_summary["min_battery"], errors="coerce").min(skipna=True)

# =========================
#  DASHBOARD
# =========================
st.title("🚁 Drone Multi-Flight Dashboard")

# --- KPIs ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Flights", total_flights)
col2.metric("Total Flight Time", format_timedelta(total_flight_time))
col3.metric("Total Distance (m)", fmt(total_flight_distance))

col4, col5, col6, col7 = st.columns(4)
col4.metric("Max Altitude (m)", fmt(max_altitude))
col5.metric("Max Ground Speed (m/s)", fmt(max_ground_speed))
col6.metric("Max Air Speed (m/s)", fmt(max_air_speed))
col7.metric("Lowest Battery %", fmt(min_battery))

st.markdown("---")

# --- Per-Flight Charts ---
st.subheader(" Per-Flight Summaries")
st.plotly_chart(px.bar(flight_summary, x="flight_id", y="avg_altitude",
                       title="Avg Altitude per Flight"), use_container_width=True)

st.plotly_chart(px.bar(flight_summary, x="flight_id",
                       y=["avg_ground_speed", "avg_air_speed"],
                       barmode="group", title="Avg Speeds per Flight"),
                use_container_width=True)

# st.plotly_chart(px.scatter(flight_summary, x="avg_flight_time", y="avg_flight_distance",
#                            size="avg_power", color="flight_id",
#                            title="Avg Flight Distance vs Time (bubble = avg power)"),
#                 use_container_width=True)

st.plotly_chart(px.bar(flight_summary, x="flight_id", y="avg_battery_remaining",
                       title="Avg Battery % Remaining per Flight"),
                use_container_width=True)


def plot_flight_metrics(df, group_col, metrics, chart_type):

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday","Friday", "Saturday", "Sunday"]
    hour_order = [datetime.datetime.strptime(str(h), "%H").strftime("%I %p") for h in range(24)]

    if group_col == "month":
        df["month"] = df["date"].dt.strftime("%b")
        df["month"] = pd.Categorical(df["month"], categories=month_order, ordered=True)
    elif group_col == "weekday":
        df["weekday"] = df["date"].dt.day_name()
        df["weekday"] = pd.Categorical(df["weekday"], categories=weekday_order, ordered=True)
    elif group_col == "hour":
        df["hour"] = df["time"].dt.hour
        df["hour"] = df["hour"].apply(lambda h: datetime.datetime.strptime(str(h), "%H").strftime("%I %p"))
        df["hour"] = pd.Categorical(df["hour"], categories=hour_order, ordered=True)
    elif group_col == "year":
        # if "year" not in df.columns:
        df["year"] = df["date"].dt.year.astype(str) 
        df["year"] = df["year"].astype(str)  # keep categorical, not numeric

    avg_vals = (df.groupby(["flight_id", group_col])[list(metrics.keys())].mean().reset_index())

    avg_long = avg_vals.melt(
        id_vars=["flight_id", group_col],
        value_vars=list(metrics.keys()),
        var_name="Metric",
        value_name="Value")
    
    avg_long["Metric"] = avg_long["Metric"].map(metrics)


    figs = {}
    
    for metric in avg_long["Metric"].unique():
        subset = avg_long[avg_long["Metric"] == metric]

        if chart_type == "line":
            fig = px.line(
                subset, x=group_col, y="Value",
                color="flight_id", markers=True,
                title=f"{group_col.capitalize()} - {metric}"
            )
        elif chart_type == "bar":
            fig = px.bar(
                subset, x=group_col, y="Value",
                color="flight_id", barmode="group",
                title=f"{group_col.capitalize()} - {metric}"
            )
        else:
            raise ValueError("Unsupported chart_type. Use 'line' or 'bar'.")

        fig.update_layout(
            xaxis=dict(type="category"),
            yaxis_title=f"Average {metric}"
        )
        figs[metric] = fig

    return figs


metrics = {
    "groundSpeed": "Ground Speed",
    "airSpeed": "Air Speed",
    "altitudeRelative": "Altitude",
    "battery0.percentRemaining": "Battery %"
}


group_col = st.selectbox("Group by", ["year", "month", "weekday", "hour"])
chart_type = st.radio("Chart type", ["line", "bar"])

charts = plot_flight_metrics(df_all, group_col=group_col, metrics=metrics, chart_type=chart_type)


for metric, fig in charts.items():
    st.subheader(f"{group_col.capitalize()} - {metric}")
    st.plotly_chart(fig, use_container_width=True)

# --- GPS Path ---
if not gps_all.empty:
    st.subheader(" Flight Paths (GPS)")
    fig_map = px.line_map(gps_all, lat="gps.lat", lon="gps.lon",
                          color="flight_id", title="GPS Tracks of All Flights",
                          height=600)
    fig_map.update_layout(mapbox_style="open-street-map")

    st.plotly_chart(fig_map, use_container_width=True)
