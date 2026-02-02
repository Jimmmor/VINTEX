# Vinted Price Intelligence – Streamlit Dashboard (Dynamic)
# Stap 2: Dynamische zoekterm + dashboard

import streamlit as st
import requests
import sqlite3
from datetime import datetime
import pandas as pd

# ---------------- CONFIG ----------------
DB_NAME = "vinted.db"
COUNTRY = "be"
PER_PAGE = 50
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json",
}

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS items_snapshot (
            item_id INTEGER,
            title TEXT,
            price REAL,
            status TEXT,
            search_term TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

# ---------------- SCRAPER ----------------
def fetch_items(search_text, page=1):
    url = f"https://www.vinted.{COUNTRY}/api/v2/catalog/items"
    params = {
        "search_text": search_text,
        "page": page,
        "per_page": PER_PAGE,
    }
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json().get("items", [])

# ---------------- STORE ----------------
def store_items(items, search_term):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    ts = datetime.utcnow().isoformat()
    for item in items:
        c.execute(
            "INSERT INTO items_snapshot VALUES (?, ?, ?, ?, ?, ?)",
            (
                item["id"],
                item["title"],
                float(item["price"]["amount"]),
                item["status"],
                search_term,
                ts,
            ),
        )
    conn.commit()
    conn.close()

# ---------------- LOAD DATA ----------------
def load_data(search_term):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        "SELECT * FROM items_snapshot WHERE search_term = ?",
        conn,
        params=(search_term,),
    )
    conn.close()
    return df

# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title="Vinted Price Intelligence", layout="wide")
st.title("🧠 Vinted Price Intelligence Dashboard")

init_db()

search_term = st.text_input("Zoek product op Vinted", "airpods pro")

col1, col2 = st.columns(2)
with col1:
    if st.button("📥 Update data"):
        items = fetch_items(search_term)
        store_items(items, search_term)
        st.success(f"{len(items)} items opgeslagen")

with col2:
    st.info("Run dit meerdere keren per dag voor verkoopdetectie")

if search_term:
    df = load_data(search_term)

    if not df.empty:
        st.subheader("📊 Markt Overzicht")
        sold_df = df[df["status"] == "sold"]

        k1, k2, k3 = st.columns(3)
        k1.metric("Verkochte items", len(sold_df))
        k2.metric("Gemiddelde prijs", f"€{sold_df['price'].mean():.2f}" if not sold_df.empty else "–")
        k3.metric("Actieve listings", len(df[df["status"] == "available"]))

        st.subheader("💰 Prijsverdeling (verkocht)")
        st.bar_chart(sold_df["price"].value_counts().sort_index())

        st.subheader("📋 Ruwe data")
        st.dataframe(df.sort_values("timestamp", ascending=False))

    else:
        st.warning("Nog geen data voor deze zoekterm")
