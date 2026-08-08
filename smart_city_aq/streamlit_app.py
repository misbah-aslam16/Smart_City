"""
streamlit_app.py — Main Entry Point for Streamlit Deployment
Smart City Air Quality Monitoring System — Pakistan
"""

import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

# Load local .env if exists (for local dev)
load_dotenv()

# Imports from local config.py
from config import AQI_COLORS, HEALTH_RISK_COLORS, CITIES

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart City AQI — Pakistan",
    page_icon="🌆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.main-title{font-size:2rem;font-weight:700;color:#1f2937;margin-bottom:.25rem}
.subtitle{font-size:1rem;color:#6b7280;margin-bottom:1.5rem}
.metric-card{background:white;border-radius:12px;padding:1.2rem 1rem;
  border-left:5px solid #3b82f6;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.metric-city{font-size:.85rem;color:#6b7280;font-weight:600}
.metric-value{font-size:2rem;color:#1f2937;font-weight:800}
.metric-label{font-size:.75rem;color:#9ca3af}
.risk-badge{display:inline-block;padding:2px 10px;border-radius:20px;
  font-size:.72rem;font-weight:600;color:white}
section[data-testid="stSidebar"]{background:#f8fafc}
</style>
""", unsafe_allow_html=True)


# ── Data loading ─────────────────────────────────────────────────────────────
def _sf_query(sql: str) -> pd.DataFrame:
    """Run a Snowflake query safely. Uses Streamlit Secrets if available, else Env vars."""
    try:
        import snowflake.connector
        
        # Priority: Streamlit Secrets > Environment Variables
        account = st.secrets.get("SNOWFLAKE_ACCOUNT") or os.getenv("SNOWFLAKE_ACCOUNT")
        user = st.secrets.get("SNOWFLAKE_USER") or os.getenv("SNOWFLAKE_USER")
        password = st.secrets.get("SNOWFLAKE_PASSWORD") or os.getenv("SNOWFLAKE_PASSWORD")
        role = st.secrets.get("SNOWFLAKE_ROLE") or os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
        warehouse = st.secrets.get("SNOWFLAKE_WAREHOUSE") or os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")

        if not all([account, user, password]):
            return pd.DataFrame() # Fallback to demo data if no creds

        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            role=role,
            warehouse=warehouse,
            database="AIR_QUALITY_DB",
            login_timeout=20,
            network_timeout=30,
        )
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0].lower() for d in cur.description]
        rows = cur.fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def get_gold() -> pd.DataFrame:
    df = _sf_query("""
        SELECT city, reading_date, avg_aqi, max_aqi, min_aqi,
               avg_pm25, avg_pm10, avg_no2, avg_co, avg_o3, avg_so2,
               dominant_risk, dominant_aqi_cat,
               reading_count, iot_count, openaq_count, lat, lon
        FROM AIR_QUALITY_DB.ANALYTICS.CITY_DAILY
        ORDER BY reading_date DESC, city
    """)
    if not df.empty:
        df["reading_date"] = pd.to_datetime(df["reading_date"])
        for c in ["avg_aqi","max_aqi","min_aqi","avg_pm25","avg_pm10",
                  "avg_no2","avg_co","avg_o3","avg_so2",
                  "reading_count","iot_count","openaq_count"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    return _demo_gold()


@st.cache_data(ttl=600, show_spinner=False)
def get_silver() -> pd.DataFrame:
    df = _sf_query("""
        SELECT source, city, zone_type, pm25, aqi_value,
               aqi_category, health_risk, reading_date
        FROM AIR_QUALITY_DB.CLEAN.AQI_CLEAN
        WHERE aqi_value >= 0
        LIMIT 2000
    """)
    if not df.empty:
        df["reading_date"] = pd.to_datetime(df["reading_date"], errors="coerce")
        df["aqi_value"]    = pd.to_numeric(df["aqi_value"],     errors="coerce")
        df["pm25"]         = pd.to_numeric(df["pm25"],          errors="coerce")
        return df
    return _demo_silver()


# ── Demo data ────────────────────────────────────────────────────────────────
def _demo_gold() -> pd.DataFrame:
    rng   = np.random.default_rng(7)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=14, freq="D")
    base  = {"Karachi":160,"Lahore":185,"Islamabad":90,"Peshawar":145,"Multan":135}

    def info(a):
        if a<=50:  return "Good","Low"
        if a<=100: return "Moderate","Moderate"
        if a<=150: return "Unhealthy for Sensitive Groups","Elevated"
        if a<=200: return "Unhealthy","High"
        if a<=300: return "Very Unhealthy","Very High"
        return "Hazardous","Critical"

    rows=[]
    for city,b in base.items():
        for d in dates:
            avg=float(np.clip(rng.normal(b,28),15,380))
            cat,risk=info(avg)
            rows.append({"city":city,"reading_date":d,
                "avg_aqi":round(avg,2),
                "max_aqi":int(np.clip(avg+rng.uniform(10,55),avg,500)),
                "min_aqi":int(np.clip(avg-rng.uniform(10,45),0,avg)),
                "avg_pm25":round(avg*.42,4),"avg_pm10":round(avg*.70,4),
                "avg_no2":round(float(rng.uniform(20,80)),4),
                "avg_co":round(float(rng.uniform(.5,6)),4),
                "avg_o3":round(float(rng.uniform(15,70)),4),
                "avg_so2":round(float(rng.uniform(5,60)),4),
                "dominant_risk":risk,"dominant_aqi_cat":cat,
                "reading_count":int(rng.integers(80,200)),
                "iot_count":int(rng.integers(40,110)),
                "openaq_count":int(rng.integers(10,50)),
                "lat":CITIES[city]["lat"],"lon":CITIES[city]["lon"]})
    return pd.DataFrame(rows)


def _demo_silver() -> pd.DataFrame:
    rng=np.random.default_rng(99)
    cats=["Good","Moderate","Unhealthy for Sensitive Groups",
          "Unhealthy","Very Unhealthy","Hazardous"]
    hmap={"Good":"Low","Moderate":"Moderate",
           "Unhealthy for Sensitive Groups":"Elevated",
           "Unhealthy":"High","Very Unhealthy":"Very High","Hazardous":"Critical"}
    dates=pd.date_range(end=pd.Timestamp.today(),periods=3,freq="D")
    rows=[]
    for city in CITIES:
        for date in dates:
            for _ in range(20):
                pm25=float(np.clip(rng.normal(120,60),5,400))
                aqi=int(np.clip(pm25*1.5,0,500))
                cat=cats[min(aqi//60,5)]
                rows.append({"source":rng.choice(["iot","openaq"]),
                    "city":city,"zone_type":rng.choice(["industrial","traffic","residential","park"]),
                    "pm25":round(pm25,4),"aqi_value":aqi,
                    "aqi_category":cat,"health_risk":hmap[cat],"reading_date":date})
    return pd.DataFrame(rows)


# ── Load data ────────────────────────────────────────────────────────────────
with st.spinner("Fetching live data..."):
    gold_df   = get_gold()
    silver_df = get_silver()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌆 Smart City AQI")
    st.markdown("**Pakistan Air Quality Monitor**")
    st.divider()

    all_cities  = sorted(gold_df["city"].unique()) if not gold_df.empty else list(CITIES.keys())
    sel_cities  = st.multiselect("🏙️ Cities", all_cities, default=all_cities)

    st.divider()
    min_d = gold_df["reading_date"].min() if not gold_df.empty else pd.Timestamp.today()
    max_d = gold_df["reading_date"].max() if not gold_df.empty else pd.Timestamp.today()
    dr    = st.date_input("📅 Date range", value=(min_d, max_d),
                          min_value=min_d, max_value=max_d)
    
    if isinstance(dr,(list,tuple)) and len(dr) > 0:
        d_start = pd.Timestamp(dr[0])
        d_end   = pd.Timestamp(dr[1]) if len(dr)>1 else d_start
    else:
        d_start = pd.Timestamp(dr)
        d_end = d_start

    st.divider()
    st.markdown("**Data sources**")
    st.markdown("🟢 IoT Simulator (10 sensors)\n\n🔵 OpenAQ V3 API")
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear(); st.rerun()

# ── Filter ───────────────────────────────────────────────────────────────────
filt = gold_df[
    (gold_df["city"].isin(sel_cities)) &
    (gold_df["reading_date"] >= d_start) &
    (gold_df["reading_date"] <= d_end)
].copy() if not gold_df.empty else pd.DataFrame()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🌆 Smart City Air Quality Monitoring</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Pakistan — Karachi · Lahore · Islamabad · Peshawar · Multan</p>', unsafe_allow_html=True)

# ── KPI Cards ────────────────────────────────────────────────────────────────
st.markdown("### 📊 Latest AQI — City Overview")
latest = (filt.sort_values("reading_date",ascending=False)
              .groupby("city").first().reset_index()
          if not filt.empty else pd.DataFrame())

if not latest.empty:
    cols = st.columns(len(latest))
    for i,row in latest.iterrows():
        aqi   = row.get("avg_aqi",0) or 0
        cat   = row.get("dominant_aqi_cat","Unknown")
        risk  = row.get("dominant_risk","Unknown")
        color = AQI_COLORS.get(cat,"#AAAAAA")
        rcol  = HEALTH_RISK_COLORS.get(risk,"#AAAAAA")
        with cols[i % len(cols)]:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color:{color}">
                <div class="metric-city">{row['city']}</div>
                <div class="metric-value" style="color:{color}">{int(aqi)}</div>
                <div class="metric-label">Avg AQI</div>
                <span class="risk-badge" style="background:{rcol}">{risk}</span>
            </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1: Bar + Line ────────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 📊 Average AQI by City")
    if not filt.empty:
        ca = filt.groupby("city")["avg_aqi"].mean().reset_index().sort_values("avg_aqi")
        fig = px.bar(ca, x="avg_aqi", y="city", orientation="h",
                     color="avg_aqi",
                     color_continuous_scale=["#00E400","#FFFF00","#FF7E00","#FF0000","#8F3F97","#7E0023"],
                     range_color=[0,400], labels={"avg_aqi":"Avg AQI","city":""}, height=300)
        fig.update_layout(margin=dict(l=0,r=0,t=10,b=10),
                          coloraxis_showscale=False,
                          plot_bgcolor="white",paper_bgcolor="white")
        fig.add_vline(x=150,line_dash="dash",line_color="#FF7E00")
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("#### 📈 AQI Trend Over Time")
    if not filt.empty:
        tr = filt.groupby(["reading_date","city"])["avg_aqi"].mean().reset_index()
        fig2 = px.line(tr, x="reading_date", y="avg_aqi", color="city",
                       markers=True, height=300,
                       labels={"avg_aqi":"Avg AQI","reading_date":"Date","city":"City"})
        fig2.update_layout(margin=dict(l=0,r=0,t=10,b=10),
                           plot_bgcolor="white",paper_bgcolor="white",
                           legend=dict(orientation="h",yanchor="bottom",y=1.02))
        for y0,y1,col in [(0,50,"#00E400"),(50,100,"#FFFF00"),(100,150,"#FF7E00"),
                           (150,200,"#FF0000"),(200,400,"#8F3F97")]:
            fig2.add_hrect(y0=y0,y1=y1,fillcolor=col,opacity=0.05,line_width=0)
        st.plotly_chart(fig2, use_container_width=True)

# ── Row 2: Pollutants + Pie ──────────────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown("#### 🏭 Avg Pollutants by City (µg/m³)")
    if not filt.empty:
        pcols = [c for c in ["avg_pm25","avg_pm10","avg_no2","avg_o3","avg_so2"] if c in filt.columns]
        if pcols:
            pm = filt.groupby("city")[pcols].mean().reset_index()
            pm = pm.melt(id_vars="city",var_name="Pollutant",value_name="µg/m³")
            pm["Pollutant"] = pm["Pollutant"].str.replace("avg_","").str.upper()
            fig3 = px.bar(pm,x="city",y="µg/m³",color="Pollutant",barmode="group",
                          height=300,color_discrete_sequence=px.colors.qualitative.Set2)
            fig3.update_layout(margin=dict(l=0,r=0,t=10,b=10),
                               plot_bgcolor="white",paper_bgcolor="white",
                               legend=dict(orientation="h",yanchor="bottom",y=1.02))
            st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.markdown("#### 🏥 Health Risk Distribution")
    if not filt.empty and "dominant_risk" in filt.columns:
        rc = filt["dominant_risk"].value_counts().reset_index()
        rc.columns = ["health_risk","count"]
        fig4 = px.pie(rc,names="health_risk",values="count",
                      color="health_risk",color_discrete_map=HEALTH_RISK_COLORS,
                      height=300,hole=0.4)
        fig4.update_layout(margin=dict(l=0,r=0,t=10,b=10),
                           legend=dict(orientation="h",yanchor="bottom",y=-0.2))
        fig4.update_traces(textposition="inside",textinfo="percent+label")
        st.plotly_chart(fig4, use_container_width=True)

# ── Raw data tables ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔬 Silver Layer — Raw Readings")
with st.expander("View / filter readings", expanded=False):
    if not silver_df.empty:
        sf = silver_df[silver_df["city"].isin(sel_cities)].copy()
        cc1,cc2,cc3 = st.columns(3)
        src  = cc1.selectbox("Source",  ["All"]+sorted(sf["source"].unique().tolist()))
        zone = cc2.selectbox("Zone",    ["All"]+sorted(sf["zone_type"].dropna().unique().tolist()))
        risk = cc3.selectbox("Risk",    ["All"]+sorted(sf["health_risk"].dropna().unique().tolist()))
        if src  != "All": sf = sf[sf["source"]=="iot" if src=="iot" else sf["source"]==src]
        if zone != "All": sf = sf[sf["zone_type"]==zone]
        if risk != "All": sf = sf[sf["health_risk"]==risk]
        show = [c for c in ["city","zone_type","source","pm25","aqi_value",
                              "aqi_category","health_risk","reading_date"] if c in sf.columns]
        st.dataframe(sf[show].head(500), use_container_width=True, height=320)
    else:
        st.info("No Silver data.")

st.markdown("### 🥇 Gold Layer — City Daily Summary")
with st.expander("View Gold table", expanded=False):
    if not filt.empty:
        show = [c for c in ["city","reading_date","avg_aqi","max_aqi","min_aqi",
                             "avg_pm25","dominant_risk","reading_count"] if c in filt.columns]
        st.dataframe(filt[show].sort_values(["reading_date","city"],ascending=[False,True]),
                     use_container_width=True, height=300)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#9ca3af;font-size:.8rem'>"
    "Smart City AQI · Pakistan · IoT Simulator + OpenAQ V3 · "
    "Snowflake Bronze→Silver→Gold</div>",
    unsafe_allow_html=True)
