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

# --- Professional custom styling ---
st.markdown("""
    <style>
    /* General App Styling */
    .main { background-color: #f8fafc; }
    
    /* Main Title Styling */
    .title-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #2563eb 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(30, 58, 138, 0.25);
    }
    .title-container h1 { color: #ffffff !important; margin: 0; font-size: 2.5rem; font-weight: 800; }
    .title-container p { color: #93c5fd; font-size: 1.1rem; margin-top: 0.5rem; margin-bottom: 0; }

    /* Styled Container Cards */
    .bus-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .bus-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
        border-color: #3b82f6;
    }

    /* Modern badges */
    .badge {
        background-color: #eff6ff;
        color: #2563eb;
        padding: 0.3rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        border: 1px solid #dbeafe;
    }
    .badge-route {
        background-color: #f0fdf4;
        color: #16a34a;
        border: 1px solid #dcfce7;
    }
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

def login_screen():
    st.markdown("""
        <div class='title-container'>
            <h1>🚌 SmartBus</h1>
            <p>Experience seamless transit booking with our fast, modern digital ticketing portal</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        tab1, tab2 = st.tabs(["🔑 Sign In", "📝 Create Account"])
        with tab1:
            with st.form("login_form"):
                st.subheader("Welcome Back")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                ok = st.form_submit_button("Login to System", use_container_width=True)
            if ok:
                with connect() as con:
                    user = con.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                                       (username.strip(), pw_hash(password))).fetchone()
                if user:
                    st.session_state.user = {"username": user["username"], "role": user["role"]}
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        with tab2:
            with st.form("register_form"):
                st.subheader("Join SmartBus")
                new_user = st.text_input("Choose Username")
                new_pass = st.text_input("Choose Password", type="password")
                confirm = st.text_input("Confirm Password", type="password")
                create = st.form_submit_button("Create Passenger Account", use_container_width=True)
            if create:
                if len(new_user.strip()) < 3 or len(new_pass) < 6:
                    st.warning("Username must be ≥ 3 characters & password ≥ 6 characters.")
                elif new_pass != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        with connect() as con:
                            con.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                                        (new_user.strip(), pw_hash(new_pass), "Passenger"))
                        st.success("Account successfully created! Please sign in.")
                    except sqlite3.IntegrityError:
                        st.error("That username already exists.")

    with col2:
        st.markdown("""
            <div style='background-color: #ffffff; padding: 2rem; border-radius: 16px; border: 1px solid #e2e8f0; height: 100%;'>
                <h3 style='margin-top: 0; color: #1e293b;'>Why SmartBus?</h3>
                <p style='color: #64748b;'>Our platform redesign focuses on clarity, accessibility, and clean visual structures inspired by world-class travel interfaces.</p>
                <ul style='color: #475569; padding-left: 1.25rem; line-height: 1.8;'>
                    <li><b>Instant Digital Ticket Generation</b>: Secure unique reference codes.</li>
                    <li><b>Live Route Scheduling</b>: Real-time route visibility and filtering.</li>
                    <li><b>Administrative Control Panel</b>: Easy fleet scheduling.</li>
                </ul>
                <div style='margin-top: 1.5rem; padding: 1rem; background-color: #f8fafc; border-radius: 8px; border-left: 4px solid #3b82f6;'>
                    <span style='font-size: 0.9rem; font-weight: bold; color: #1e3a8a;'>💡 Demo Accounts Available</span><br/>
                    <span style='font-size: 0.85rem; color: #475569;'>• Admin: <b>admin</b> / admin123<br/>• Passenger: <b>passenger</b> / bus123</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

def get_buses(source="", destination=""):
    sql = "SELECT * FROM buses WHERE active=1"
    args = []
    if source:
        sql += " AND lower(source)=lower(?)"; args.append(source)
    if destination:
        sql += " AND lower(destination)=lower(?)"; args.append(destination)
    sql += " ORDER BY departure"
    with connect() as con:
        return pd.read_sql_query(sql, con, params=args)

def passenger_page():
    user = st.session_state.user["username"]
    st.markdown(f"""
        <div style='margin-bottom: 2rem;'>
            <span class='badge badge-route'>PASSENGER CONSOLE</span>
            <h2 style='margin: 0.5rem 0 0.2rem 0;'>Welcome Back, {user}</h2>
            <p style='color: #64748b; margin: 0;'>Search active bus lines, verify pricing structures, and claim your digital ticket instantly.</p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔍 Find & Book Routes", "🎫 Your Digital Tickets"])
    with tab1:
        with connect() as con:
            locations = [r[0] for r in con.execute("SELECT source FROM buses UNION SELECT destination FROM buses ORDER BY 1").fetchall()]
        
        st.markdown("### Route Settings")
        col_search = st.container(border=True)
        with col_search:
            c1, c2, c3 = st.columns([1, 1, 1])
            source = c1.selectbox("Departure Station", locations, key="from")
            destinations = [x for x in locations if x != source]
            destination = c2.selectbox("Destination Station", destinations, key="to")
            travel_date = c3.date_input("Target Travel Date", min_value=date.today())
        
        st.write("")
        buses = get_buses(source, destination)
        if buses.empty:
            st.info("No active buses are currently listed for this path.")
        else:
            st.subheader("Available Scheduled Services")
            for _, bus in buses.iterrows():
                st.markdown(f"""
                    <div class='bus-card'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;'>
                            <div>
                                <span class='badge'>{bus['bus_number']}</span>
                                <span style='font-size: 1.15rem; font-weight: bold; margin-left: 10px; color: #1e293b;'>
                                    {bus['source']} → {bus['destination']}
                                </span>
                            </div>
                            <div style='font-size: 1.3rem; font-weight: 800; color: #2563eb;'>₹{bus['fare']:.0f} <span style='font-size: 0.8rem; font-weight: normal; color: #64748b;'>per seat</span></div>
                        </div>
                        <div style='display: flex; gap: 2rem; color: #475569; font-size: 0.95rem; margin-bottom: 0.5rem;'>
                            <div>🕒 <b>Departure:</b> {bus['departure']}</div>
                            <div>🏁 <b>Arrival:</b> {bus['arrival']}</div>
                            <div>💺 <b>Capacity:</b> {bus['seats']} seats total</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"Confirm Seats on {bus['bus_number']}"):
                    c_qty, c_btn = st.columns([2, 1])
                    count = c_qty.number_input("Number of Passenger Tickets", min_value=1, max_value=6, value=1, key=f"p{bus['id']}")
                    st.write(f"**Grand Total:** ₹{float(bus['fare'])*int(count):.2f}")
                    if c_btn.button("Book Ticket Now", key=f"book{bus['id']}", use_container_width=True):
                        booking = "SB-" + uuid.uuid4().hex[:8].upper()
                        with connect() as con:
                            con.execute("""INSERT INTO tickets(booking_code,username,bus_id,travel_date,passenger_count,total_fare,status,created_at)
                                           VALUES(?,?,?,?,?,?,?,?)""",
                                        (booking,user,int(bus["id"]),travel_date.isoformat(),int(count),
                                         float(bus["fare"])*int(count),"CONFIRMED",datetime.now().isoformat(timespec="minutes")))
                        st.success(f"Booking confirmed! Booking code: {booking}. Open 'Your Digital Tickets' to view it.")
    with tab2:
        with connect() as con:
            tickets = pd.read_sql_query("""SELECT t.booking_code, t.travel_date, b.bus_number, b.source, b.destination,
                         b.departure, t.passenger_count, t.total_fare, t.status, t.created_at
                         FROM tickets t JOIN buses b ON t.bus_id=b.id WHERE t.username=?
                         ORDER BY t.id DESC""", con, params=(user,))
        if tickets.empty:
            st.info("You have not booked any tickets yet.")
        else:
            st.dataframe(tickets, use_container_width=True, hide_index=True)
            for _, ticket in tickets.iterrows():
                with st.container(border=True):
                    st.subheader(f"🎫 {ticket['booking_code']}")
                    st.write(f"**Route:** {ticket['source']} → {ticket['destination']}  |  **Date:** {ticket['travel_date']}")
                    st.write(f"**Bus:** {ticket['bus_number']}  |  **Departure:** {ticket['departure']}")
                    st.write(f"**Passengers:** {ticket['passenger_count']}  |  **Total:** ₹{ticket['total_fare']:.2f}")
                    st.caption("Demo digital ticket. Payment gateway integration is not enabled in this prototype.")

def admin_page():
    st.title("Administrator Dashboard")
    with connect() as con:
        buses_df = pd.read_sql_query("SELECT id,bus_number,source,destination,departure,arrival,fare,seats,active FROM buses ORDER BY id",con)
        ticket_df = pd.read_sql_query("""SELECT t.booking_code,t.username,b.bus_number,b.source,b.destination,t.travel_date,
                                       t.passenger_count,t.total_fare,t.status,t.created_at
                                       FROM tickets t JOIN buses b ON t.bus_id=b.id ORDER BY t.id DESC""".strip(),con)
        user_count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    c1,c2,c3 = st.columns(3)
    c1.metric("Registered Users", user_count)
    c2.metric("Total Bookings", len(ticket_df))
    c3.metric("Total revenue (demo)", f"₹{ticket_df['total_fare'].sum():.0f}" if not ticket_df.empty else "₹0")
    
    t1,t2,t3 = st.tabs(["Manage Buses", "All Bookings", "Add Bus"])
    with t1:
        st.dataframe(buses_df, use_container_width=True, hide_index=True)
        with st.form("disable_bus"):
            bus_id = st.number_input("Bus ID to Activate/Deactivate", min_value=1, step=1)
            active = st.selectbox("Status", ["Active","Inactive"])
            submit = st.form_submit_button("Update Bus Status")
        if submit:
            with connect() as con:
                cur = con.execute("UPDATE buses SET active=? WHERE id=?", (1 if active=="Active" else 0, int(bus_id)))
            st.success("Bus status updated." if cur.rowcount else "Bus ID not found.")
    with t2:
        if ticket_df.empty: st.info("No bookings yet.")
        else:
            st.dataframe(ticket_df, use_container_width=True, hide_index=True)
            st.download_button("Download bookings CSV", ticket_df.to_csv(index=False).encode("utf-8"),
                               "smartbus_bookings.csv", "text/csv")
    with t3:
        with st.form("add_bus"):
            bus_no = st.text_input("Bus number (e.g. SB-106)")
            col1,col2 = st.columns(2)
            src = col1.text_input("Source")
            dst = col2.text_input("Destination")
            col3,col4 = st.columns(2)
            dep = col3.text_input("Departure (HH:MM)", value="08:00")
            arr = col4.text_input("Arrival (HH:MM)", value="09:00")
            col5,col6 = st.columns(2)
            fare = col5.number_input("Fare (₹)", min_value=0.0, value=100.0)
            seats = col6.number_input("Seats", min_value=1, value=40, step=1)
            add = st.form_submit_button("Add Bus Line")
        if add:
            if not all([bus_no.strip(),src.strip(),dst.strip(),dep.strip(),arr.strip()]) or src.lower()==dst.lower():
                st.error("Enter all fields and use different source and destination.")
            else:
                try:
                    with connect() as con:
                        con.execute("""INSERT INTO buses(bus_number,source,destination,departure,arrival,fare,seats,active)
                                       VALUES(?,?,?,?,?,?,?,1)""",
                                    (bus_no.strip(),src.strip(),dst.strip(),dep.strip(),arr.strip(),float(fare),int(seats)))
                    st.success("New Bus Line created.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Bus number already exists.")

def main():
    init_db()
    if "user" not in st.session_state:
        login_screen()
        return
    with st.sidebar:
        st.markdown("## 🚌 SmartBus")
        st.write(f"**User:** {st.session_state.user['username']}")
        st.write(f"**Role:** {st.session_state.user['role']}")
        if st.button("Logout", use_container_width=True):
            del st.session_state.user
            st.rerun()
    if st.session_state.user["role"] == "Admin":
        admin_page()
    else:
        passenger_page()

if __name__ == '__main__':
    main()
