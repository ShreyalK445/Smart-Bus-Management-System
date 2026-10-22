import streamlit as st
import sqlite3, hashlib, uuid
from datetime import datetime, date
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).with_name("smart_bus.db")

st.set_page_config(
    page_title="SmartBus | Digital Ticketing", 
    page_icon="🚌", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enterprise dashboard styling inspired by the reference image ---
st.markdown("""
<style>
:root { --navy:#102451; --blue:#1769b0; --blue2:#2f80c9; --ink:#1d2c49; --muted:#64748b; --line:#dce3ed; --canvas:#f3f5f8; }
.stApp { background: var(--canvas); color: var(--ink); }
[data-testid="stHeader"] { background: rgba(243,245,248,.96); }
.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1450px; }
section[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
section[data-testid="stSidebar"] h2 { color:var(--navy); }
.title-container { background:linear-gradient(105deg,#102451 0%,#153b77 58%,#1769b0 100%); padding:1.5rem 2rem; border-radius:4px; color:#fff; margin-bottom:1.3rem; box-shadow:0 3px 10px #10245118; }
.title-container h1 { color:#fff !important; margin:0; font-size:2rem; font-weight:750; letter-spacing:-.4px; }
.title-container p { color:#d6e6fa; font-size:.98rem; margin:.35rem 0 0; }
.top-brand { background:#fff; border:1px solid var(--line); border-bottom:4px solid var(--navy); padding:.75rem 1rem; margin-bottom:1rem; display:flex; align-items:center; justify-content:space-between; }
.eyebrow { color:#52647e; font-size:.72rem; font-weight:750; letter-spacing:1.2px; text-transform:uppercase; }
.page-heading { color:var(--navy); font-size:1.8rem; font-weight:800; margin:.15rem 0 .25rem; }
.page-subtitle { color:var(--muted); margin:0 0 1rem; font-size:.94rem; }
.section-heading { color:var(--navy); font-weight:750; font-size:1.05rem; margin:.4rem 0 .75rem; }
.bus-card { background:#fff; border:1px solid var(--line); border-left:4px solid var(--blue); border-radius:3px; padding:1.1rem 1.25rem; margin-bottom:.8rem; box-shadow:0 2px 5px #172b4d0a; }
.bus-card:hover { border-color:#a9c7e6; border-left-color:var(--blue2); box-shadow:0 4px 12px #172b4d12; }
.badge { background:#eaf2fb; color:#174b85; padding:.25rem .65rem; border-radius:3px; font-size:.76rem; font-weight:750; display:inline-block; border:1px solid #d3e3f5; }
.badge-route { background:#e9f6ef; color:#18764b; border:1px solid #cdebd9; }
.workflow { display:flex; gap:0; align-items:stretch; margin:1rem 0 1.4rem; }
.workflow-step { flex:1; background:#e9edf3; color:#30415c; padding:.65rem .5rem; text-align:center; font-size:.78rem; font-weight:700; border-right:2px solid #fff; }
.workflow-step.active { background:#1769b0; color:white; }
.workflow-step.done { background:#238b57; color:white; }
.info-panel { background:#fff; border:1px solid var(--line); padding:1.25rem; border-radius:3px; }
div[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-top:3px solid var(--blue); padding:.8rem 1rem; border-radius:3px; box-shadow:0 2px 5px #172b4d08; }
div[data-testid="stMetricLabel"] { color:#60718a; }
.stButton > button, .stFormSubmitButton > button { background:#1769b0; color:#fff; border:1px solid #1769b0; border-radius:3px; font-weight:700; min-height:2.55rem; }
.stButton > button:hover, .stFormSubmitButton > button:hover { background:#10548f; color:#fff; border-color:#10548f; }
.stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"], .stDateInput input { border-radius:3px; }
div[data-testid="stTabs"] button { font-weight:700; }
hr { border-color:var(--line); }
@media (max-width: 700px) { .workflow-step { font-size:.65rem; padding:.55rem .2rem; } .title-container { padding:1.2rem; } .title-container h1 { font-size:1.65rem; } }
</style>
""", unsafe_allow_html=True)

def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS buses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, bus_number TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL, destination TEXT NOT NULL, departure TEXT NOT NULL,
            arrival TEXT NOT NULL, fare REAL NOT NULL, seats INTEGER NOT NULL, active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT, booking_code TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL, bus_id INTEGER NOT NULL, travel_date TEXT NOT NULL,
            passenger_count INTEGER NOT NULL, total_fare REAL NOT NULL, status TEXT NOT NULL DEFAULT 'CONFIRMED',
            created_at TEXT NOT NULL, FOREIGN KEY(bus_id) REFERENCES buses(id)
        );
        """)
        # Demo accounts
        con.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)",
                    ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "Admin"))
        con.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)",
                    ("passenger", hashlib.sha256("bus123".encode()).hexdigest(), "Passenger"))
        count = con.execute("SELECT COUNT(*) FROM buses").fetchone()[0]
        if count == 0:
            sample = [
                ("SB-101","Nagpur","Wardha","08:00","09:30",120,40,1),
                ("SB-102","Nagpur","Amravati","09:15","12:00",220,40,1),
                ("SB-103","Wardha","Nagpur","10:30","12:00",120,35,1),
                ("SB-104","Nagpur","Bhandara","14:00","15:45",150,35,1),
                ("SB-105","Amravati","Nagpur","16:30","19:15",220,40,1),
            ]
            con.executemany("""INSERT INTO buses(bus_number,source,destination,departure,arrival,fare,seats,active)
                               VALUES(?,?,?,?,?,?,?,?)""", sample)

def pw_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()

