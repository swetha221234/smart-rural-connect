import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from datetime import datetime
import random

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="Smart Rural Connect", layout="wide")

# ---------------- CLEAN UI STYLE ----------------
st.markdown("""
<style>
body {
    background-color: #f5f7fa;
}
.block-container {
    padding-top: 2rem;
}
div[data-testid="metric-container"] {
    background-color: white;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.1);
}
.stButton>button {
    background-color: #2E7D32;
    color: white;
    border-radius: 8px;
    height: 3em;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("<h1 style='text-align:center;'>🌾 Smart AI Rural Grievance System</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("rural.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS complaints(
id TEXT PRIMARY KEY,
name TEXT,
description TEXT,
category TEXT,
priority TEXT,
status TEXT,
latitude REAL,
longitude REAL,
created_date TEXT,
resolved_date TEXT
)
""")
conn.commit()

# ---------------- AI FUNCTIONS ----------------
def categorize(text):
    text = text.lower()
    if "water" in text:
        return "Water Supply"
    elif "road" in text:
        return "Road Issue"
    elif "electric" in text:
        return "Electricity"
    elif "garbage" in text:
        return "Sanitation"
    else:
        return "General"

def priority(text):
    urgent = ["urgent","danger","fire","accident"]
    for word in urgent:
        if word in text.lower():
            return "High"
    return "Normal"

# ---------------- SIDEBAR ----------------
st.sidebar.title("Navigation")
menu = st.sidebar.radio("", ["Register", "Track", "Admin", "Analytics"])

total = c.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
st.sidebar.metric("Total Complaints", total)

# ---------------- REGISTER ----------------
if menu == "Register":

    st.subheader("Register New Complaint")

    name = st.text_input("Your Name")
    description = st.text_area("Describe Issue")

    if "loc" not in st.session_state:
        st.session_state.loc = None

    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
    map_data = st_folium(m, height=350)

    if map_data and map_data.get("last_clicked"):
        st.session_state.loc = map_data["last_clicked"]

    if st.button("Submit Complaint"):
        if name and description and st.session_state.loc:
            cid = "RCC" + str(random.randint(1000,9999))
            cat = categorize(description)
            pr = priority(description)

            c.execute("INSERT INTO complaints VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (cid,name,description,cat,pr,"Pending",
                       st.session_state.loc["lat"],
                       st.session_state.loc["lng"],
                       str(datetime.now()),None))
            conn.commit()

            st.success("Complaint Registered Successfully")
            st.info(f"Complaint ID: {cid}")
            st.write("Category:",cat)
            st.write("Priority:",pr)
        else:
            st.warning("Fill all fields and select location")

# ---------------- TRACK ----------------
elif menu == "Track":

    st.subheader("Track Complaint")
    cid = st.text_input("Enter Complaint ID")

    if st.button("Check"):
        result = c.execute("SELECT * FROM complaints WHERE id=?",(cid,)).fetchone()
        if result:
            st.write("Name:",result[1])
            st.write("Category:",result[3])
            st.write("Priority:",result[4])

            status = result[5]

            if status=="Pending":
                st.warning("Pending")
                st.progress(25)
            elif status=="In Progress":
                st.info("In Progress")
                st.progress(60)
            else:
                st.success("Resolved")
                st.progress(100)
        else:
            st.error("Invalid ID")

# ---------------- ADMIN ----------------
elif menu == "Admin":

    st.subheader("Admin Login")
    pwd = st.text_input("Enter Password", type="password")

    if pwd:
        if pwd=="admin123":

            df = pd.read_sql_query("SELECT * FROM complaints", conn)

            if not df.empty:

                col1,col2 = st.columns(2)
                status_filter = col1.selectbox("Status",["All","Pending","In Progress","Resolved"])
                cat_filter = col2.selectbox("Category",["All"]+list(df["category"].unique()))

                if status_filter!="All":
                    df = df[df["status"]==status_filter]
                if cat_filter!="All":
                    df = df[df["category"]==cat_filter]

                st.dataframe(df,use_container_width=True)

                st.subheader("Update Status")
                sid = st.selectbox("Select ID",df["id"])
                new_status = st.selectbox("Change Status",["Pending","In Progress","Resolved"])

                if st.button("Update"):
                    resolved_time=None
                    if new_status=="Resolved":
                        resolved_time=str(datetime.now())

                    c.execute("UPDATE complaints SET status=?,resolved_date=? WHERE id=?",
                              (new_status,resolved_time,sid))
                    conn.commit()
                    st.success("Updated")

                st.subheader("Map View")
                map_view = folium.Map(location=[13.0827,80.2707],zoom_start=12)
                for _,row in df.iterrows():
                    folium.Marker([row["latitude"],row["longitude"]],
                                  popup=row["description"]).add_to(map_view)
                st_folium(map_view,height=400)

                st.subheader("Heatmap")
                heat_data = df[["latitude","longitude"]].values.tolist()
                heat_map = folium.Map(location=[13.0827,80.2707],zoom_start=12)
                HeatMap(heat_data).add_to(heat_map)
                st_folium(heat_map,height=400)

            else:
                st.info("No complaints")

        else:
            st.error("Invalid credentials")

# ---------------- ANALYTICS ----------------
elif menu=="Analytics":

    st.subheader("Analytics Dashboard")

    df = pd.read_sql_query("SELECT * FROM complaints", conn)

    if not df.empty:

        col1,col2,col3 = st.columns(3)
        col1.metric("Total",len(df))
        col2.metric("High Priority",len(df[df["priority"]=="High"]))
        col3.metric("Resolved",len(df[df["status"]=="Resolved"]))

        st.bar_chart(df["category"].value_counts())
        st.bar_chart(df["status"].value_counts())

        resolved = df[df["resolved_date"].notna()]
        if not resolved.empty:
            resolved["created_date"]=pd.to_datetime(resolved["created_date"])
            resolved["resolved_date"]=pd.to_datetime(resolved["resolved_date"])
            resolved["hours"]=(resolved["resolved_date"]-resolved["created_date"]).dt.total_seconds()/3600
            st.write("Average Resolution Time (hrs):",round(resolved["hours"].mean(),2))
    else:
        st.info("No data available")