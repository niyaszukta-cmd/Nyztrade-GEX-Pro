"""
================================================================================
NYZTrade - ULTRA UI GEX + DEX Dashboard
================================================================================
Premium Design Features:
- Glass morphism effects
- Neon gradients
- Smooth animations
- Dark theme with accents
- Real-time data indicators
- Professional trading terminal aesthetic

Author: NYZTrade
================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import pytz

# Import live data module
try:
    from live_data import LiveGEXDEXCalculator, calculate_flow_metrics, detect_gamma_flips
    LIVE_MODULE_OK = True
except Exception as e:
    LIVE_MODULE_OK = False
    IMPORT_ERR = str(e)

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="NYZTrade Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ULTRA CSS - GLASS MORPHISM + NEON THEME
# ============================================================================

st.markdown("""
<style>
    /* Import premium fonts */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
    
    /* Root variables */
    :root {
        --neon-cyan: #00f5ff;
        --neon-pink: #ff00ff;
        --neon-green: #39ff14;
        --neon-orange: #ff6600;
        --dark-bg: #0a0a0f;
        --card-bg: rgba(20, 20, 35, 0.85);
        --glass-border: rgba(255, 255, 255, 0.1);
    }
    
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0f0f1a 100%);
        background-attachment: fixed;
    }
    
    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0a0a0f;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #00f5ff, #ff00ff);
        border-radius: 4px;
    }
    
    /* Main header */
    .ultra-header {
        font-family: 'Orbitron', monospace;
        font-size: 3rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(90deg, #00f5ff, #ff00ff, #00f5ff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradient-shift 3s ease infinite;
        text-shadow: 0 0 30px rgba(0, 245, 255, 0.5);
        margin-bottom: 0.5rem;
        letter-spacing: 4px;
    }
    
    @keyframes gradient-shift {
        0% { background-position: 0% center; }
        50% { background-position: 100% center; }
        100% { background-position: 0% center; }
    }
    
    .sub-header {
        font-family: 'Rajdhani', sans-serif;
        font-size: 1.1rem;
        color: rgba(255, 255, 255, 0.6);
        text-align: center;
        letter-spacing: 3px;
        text-transform: uppercase;
    }
    
    /* Glass card */
    .glass-card {
        background: rgba(20, 20, 35, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(0, 245, 255, 0.3);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.4),
            0 0 20px rgba(0, 245, 255, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }
    
    /* Metric card */
    .metric-card {
        background: linear-gradient(145deg, rgba(30, 30, 50, 0.9), rgba(15, 15, 25, 0.9));
        border: 1px solid rgba(0, 245, 255, 0.2);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00f5ff, #ff00ff);
    }
    
    .metric-label {
        font-family: 'Rajdhani', sans-serif;
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.5);
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.3rem;
    }
    
    .metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #fff;
    }
    
    .metric-delta {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }
    
    .delta-up { color: #39ff14; }
    .delta-down { color: #ff4757; }
    
    /* Live indicator */
    .live-pulse {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(57, 255, 20, 0.15);
        border: 1px solid rgba(57, 255, 20, 0.4);
        padding: 6px 16px;
        border-radius: 20px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.9rem;
        color: #39ff14;
    }
    
    .live-dot {
        width: 10px;
        height: 10px;
        background: #39ff14;
        border-radius: 50%;
        animation: pulse 1.5s ease infinite;
        box-shadow: 0 0 10px #39ff14;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
    }
    
    /* Historical indicator */
    .hist-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255, 165, 0, 0.15);
        border: 1px solid rgba(255, 165, 0, 0.4);
        padding: 6px 16px;
        border-radius: 20px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.9rem;
        color: #ffa500;
    }
    
    /* Bias boxes */
    .dampening-box {
        background: linear-gradient(135deg, rgba(57, 255, 20, 0.2), rgba(0, 212, 170, 0.2));
        border: 1px solid rgba(57, 255, 20, 0.4);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    
    .dampening-box h3 {
        font-family: 'Orbitron', monospace;
        color: #39ff14;
        margin: 0 0 0.5rem 0;
        font-size: 1.1rem;
    }
    
    .dampening-box p {
        font-family: 'Rajdhani', sans-serif;
        color: rgba(255, 255, 255, 0.8);
        margin: 0;
    }
    
    .amplifying-box {
        background: linear-gradient(135deg, rgba(255, 71, 87, 0.2), rgba(255, 0, 102, 0.2));
        border: 1px solid rgba(255, 71, 87, 0.4);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    
    .amplifying-box h3 {
        font-family: 'Orbitron', monospace;
        color: #ff4757;
        margin: 0 0 0.5rem 0;
        font-size: 1.1rem;
    }
    
    .amplifying-box p {
        font-family: 'Rajdhani', sans-serif;
        color: rgba(255, 255, 255, 0.8);
        margin: 0;
    }
    
    .bullish-box {
        background: linear-gradient(135deg, rgba(0, 245, 255, 0.15), rgba(0, 212, 170, 0.15));
        border: 1px solid rgba(0, 245, 255, 0.3);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    
    .bearish-box {
        background: linear-gradient(135deg, rgba(255, 102, 0, 0.15), rgba(255, 71, 87, 0.15));
        border: 1px solid rgba(255, 102, 0, 0.3);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(10, 10, 15, 0.98), rgba(20, 20, 35, 0.98));
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-family: 'Rajdhani', sans-serif;
    }
    
    /* Buttons */
    .stButton > button {
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        letter-spacing: 1px;
        background: linear-gradient(135deg, rgba(0, 245, 255, 0.2), rgba(255, 0, 255, 0.2));
        border: 1px solid rgba(0, 245, 255, 0.4);
        color: #00f5ff;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 245, 255, 0.4), rgba(255, 0, 255, 0.4));
        border-color: #00f5ff;
        box-shadow: 0 0 20px rgba(0, 245, 255, 0.4);
        transform: translateY(-2px);
    }
    
    /* Select boxes */
    [data-testid="stSelectbox"] {
        font-family: 'Rajdhani', sans-serif;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(20, 20, 35, 0.5);
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        letter-spacing: 1px;
        background: transparent;
        border-radius: 8px;
        color: rgba(255, 255, 255, 0.6);
        border: 1px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 245, 255, 0.2), rgba(255, 0, 255, 0.2));
        border: 1px solid rgba(0, 245, 255, 0.4);
        color: #00f5ff;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        background: rgba(30, 30, 50, 0.5);
        border-radius: 8px;
    }
    
    /* Time machine section */
    .time-machine-header {
        font-family: 'Orbitron', monospace;
        font-size: 1.5rem;
        color: #ff00ff;
        margin: 1rem 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Quick jump buttons */
    .quick-jump-btn {
        font-family: 'Share Tech Mono', monospace;
        background: rgba(255, 0, 255, 0.1);
        border: 1px solid rgba(255, 0, 255, 0.3);
        color: #ff00ff;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .quick-jump-btn:hover {
        background: rgba(255, 0, 255, 0.3);
        box-shadow: 0 0 15px rgba(255, 0, 255, 0.3);
    }
    
    /* Status log */
    .status-log {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.8rem;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 8px;
        padding: 1rem;
        max-height: 200px;
        overflow-y: auto;
    }
    
    .status-log .success { color: #39ff14; }
    .status-log .warning { color: #ffa500; }
    .status-log .error { color: #ff4757; }
    .status-log .info { color: #00f5ff; }
    
    /* Gamma flip warning */
    .gamma-flip-alert {
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.15), rgba(255, 165, 0, 0.15));
        border: 1px solid rgba(255, 215, 0, 0.4);
        border-left: 4px solid #ffd700;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Rajdhani', sans-serif;
    }
    
    /* Footer */
    .ultra-footer {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.4);
        text-align: center;
        padding: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        margin-top: 2rem;
    }
    
    /* Animations */
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 5px currentColor; }
        50% { box-shadow: 0 0 20px currentColor, 0 0 30px currentColor; }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-in {
        animation: slideIn 0.5s ease forwards;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# AUTHENTICATION
# ============================================================================

def check_password():
    """Returns True if user has entered correct password"""
    
    def password_entered():
        username = st.session_state.get("username", "").strip().lower()
        password = st.session_state.get("password", "")
        
        users = {
            "demo": "demo123",
            "premium": "premium123", 
            "niyas": "nyztrade123"
        }
        
        if username in users and password == users[username]:
            st.session_state["password_correct"] = True
            st.session_state["authenticated_user"] = username
            if "password" in st.session_state:
                del st.session_state["password"]
            return
        
        st.session_state["password_correct"] = False
    
    if "password_correct" not in st.session_state:
        st.markdown('<h1 class="ultra-header">NYZTrade</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Advanced Options Analytics Terminal</p>', unsafe_allow_html=True)
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 1.5, 1])
        
        with col2:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("### 🔐 Secure Login")
            st.text_input("Username", key="username", placeholder="Enter username")
            st.text_input("Password", type="password", key="password", placeholder="Enter password")
            st.button("🚀 Access Terminal", on_click=password_entered, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.info("""
            **Demo Access:**  
            `demo` / `demo123`  
            
            **Premium Access:**  
            `premium` / `premium123`
            """)
        
        return False
    
    elif not st.session_state.get("password_correct", False):
        st.markdown('<h1 class="ultra-header">NYZTrade</h1>', unsafe_allow_html=True)
        st.error("❌ Invalid credentials")
        
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.text_input("Username", key="username", placeholder="Enter username")
            st.text_input("Password", type="password", key="password", placeholder="Enter password")
            st.button("🚀 Access Terminal", on_click=password_entered, use_container_width=True)
        
        return False
    
    return True

def get_user_tier():
    username = st.session_state.get("authenticated_user", "guest")
    return "premium" if username in ["premium", "niyas"] else "basic"

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    defaults = {
        'snapshots_by_config': {},
        'current_config_key': None,
        'selected_time_index': None,
        'is_live_mode': True,
        'last_capture_time': None,
        'auto_capture': True,
        'capture_interval': 3,
        'force_capture': False,
        'calculator': None,
        'status_messages': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Check auth first
if not check_password():
    st.stop()

# Initialize
init_session_state()
user_tier = get_user_tier()

# Initialize calculator
if st.session_state.calculator is None and LIVE_MODULE_OK:
    st.session_state.calculator = LiveGEXDEXCalculator()

# ============================================================================
# TIME MACHINE FUNCTIONS
# ============================================================================

def get_config_key(symbol, expiry_index):
    return f"{symbol}_{expiry_index}"

def get_current_snapshots():
    key = st.session_state.current_config_key
    if key and key in st.session_state.snapshots_by_config:
        return st.session_state.snapshots_by_config[key]
    return {'times': [], 'data': {}}

def capture_snapshot(df, futures_ltp, fetch_method, atm_info, flow_metrics, symbol, expiry_index):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).replace(microsecond=0)
    
    if st.session_state.last_capture_time:
        elapsed = (now - st.session_state.last_capture_time).total_seconds() / 60
        if elapsed < st.session_state.capture_interval and not st.session_state.force_capture:
            return False
    
    config_key = get_config_key(symbol, expiry_index)
    
    if config_key not in st.session_state.snapshots_by_config:
        st.session_state.snapshots_by_config[config_key] = {'times': [], 'data': {}}
    
    config = st.session_state.snapshots_by_config[config_key]
    
    config['data'][now] = {
        'df': df.copy(),
        'futures_ltp': futures_ltp,
        'fetch_method': fetch_method,
        'atm_info': atm_info.copy() if atm_info else None,
        'flow_metrics': flow_metrics.copy() if flow_metrics else None,
        'symbol': symbol,
        'expiry_index': expiry_index
    }
    
    if now not in config['times']:
        config['times'].append(now)
        config['times'].sort()
    
    st.session_state.last_capture_time = now
    st.session_state.force_capture = False
    
    while len(config['times']) > 500:
        oldest = config['times'].pop(0)
        config['data'].pop(oldest, None)
    
    return True

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<h1 class="ultra-header">NYZTrade Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Real-Time Gamma & Delta Exposure Analysis</p>', unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # User badge
    if user_tier == "premium":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #ffd700, #ff8c00); padding: 10px 15px; border-radius: 10px; text-align: center; margin-bottom: 1rem;">
            <span style="font-family: 'Orbitron', monospace; color: #000; font-weight: bold;">👑 PREMIUM</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: rgba(100, 100, 100, 0.3); padding: 10px 15px; border-radius: 10px; text-align: center; margin-bottom: 1rem;">
            <span style="font-family: 'Rajdhani', sans-serif; color: #aaa;">🆓 Free Tier</span>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("🚪 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    
    symbol = st.selectbox(
        "📊 Index",
        ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"],
        index=0
    )
    
    strikes_range = st.slider(
        "📏 Strikes Range",
        min_value=5,
        max_value=20,
        value=12
    )
    
    expiry_index = st.selectbox(
        "📅 Expiry",
        [0, 1, 2],
        format_func=lambda x: ["Current Weekly", "Next Weekly", "Monthly"][x],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### ⏰ Time Machine")
    
    config_key = get_config_key(symbol, expiry_index)
    st.session_state.current_config_key = config_key
    
    config = st.session_state.snapshots_by_config.get(config_key, {'times': []})
    snapshot_count = len(config.get('times', []))
    
    st.metric("📸 Snapshots", snapshot_count)
    
    if snapshot_count > 0:
        st.caption(f"First: {config['times'][0].strftime('%I:%M %p')}")
        st.caption(f"Last: {config['times'][-1].strftime('%I:%M %p')}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.auto_capture = st.checkbox("Auto", value=st.session_state.auto_capture)
    with col2:
        st.session_state.capture_interval = st.selectbox(
            "Int",
            [1, 2, 3, 5],
            index=2,
            format_func=lambda x: f"{x}m",
            label_visibility="collapsed"
        )
    
    if st.button("📸 Capture Now", use_container_width=True, type="primary"):
        st.session_state.force_capture = True
    
    st.markdown("---")
    
    if user_tier == "premium":
        auto_refresh = st.checkbox("🔄 Auto-Refresh", value=False)
        if auto_refresh:
            refresh_interval = st.slider("Interval (sec)", 30, 180, 60, step=30)
            
            if 'countdown_start' not in st.session_state:
                st.session_state.countdown_start = time.time()
            
            elapsed = time.time() - st.session_state.countdown_start
            remaining = max(0, refresh_interval - int(elapsed))
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea, #764ba2); padding: 10px; border-radius: 8px; text-align: center;">
                <span style="font-family: 'Orbitron', monospace; color: white; font-size: 1.2rem;">⏱️ {remaining}s</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        auto_refresh = False
        refresh_interval = 60
        st.info("🔒 Auto-refresh: Premium")
    
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        if 'countdown_start' in st.session_state:
            st.session_state.countdown_start = time.time()
        st.rerun()

# ============================================================================
# MAIN CONTENT - TIME MACHINE UI
# ============================================================================

st.markdown("---")

# Time Machine Section
expiry_labels = {0: "Current Weekly", 1: "Next Weekly", 2: "Monthly"}

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    st.markdown(f'<div class="time-machine-header">⏰ Time Machine - {symbol} ({expiry_labels[expiry_index]})</div>', unsafe_allow_html=True)

with col2:
    if st.session_state.is_live_mode:
        st.markdown('<div class="live-pulse"><div class="live-dot"></div>LIVE</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="hist-badge">📜 HISTORICAL</div>', unsafe_allow_html=True)

with col3:
    if not st.session_state.is_live_mode:
        if st.button("🔴 Go Live", key="go_live"):
            st.session_state.is_live_mode = True
            st.session_state.selected_time_index = None
            st.rerun()

# Snapshot slider
config = get_current_snapshots()
snapshot_times = config.get('times', [])
historical_data = None

if snapshot_times:
    st.caption(f"📊 **{len(snapshot_times)} snapshots** | {snapshot_times[0].strftime('%I:%M %p')} → {snapshot_times[-1].strftime('%I:%M %p')}")
    
    if len(snapshot_times) > 1:
        time_labels = [t.strftime('%I:%M %p') for t in snapshot_times]
        
        current_idx = st.session_state.selected_time_index
        if current_idx is None or current_idx >= len(snapshot_times):
            current_idx = len(snapshot_times) - 1
        
        selected_idx = st.select_slider(
            "🕐 Select Time Point",
            options=list(range(len(snapshot_times))),
            value=current_idx,
            format_func=lambda x: time_labels[x]
        )
        
        if selected_idx != len(snapshot_times) - 1:
            st.session_state.is_live_mode = False
            st.session_state.selected_time_index = selected_idx
        
        # Quick jump buttons
        st.markdown("**⚡ Quick Jump:**")
        qcols = st.columns(7)
        presets = [("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60), ("2h", 120), ("3h", 180), ("Start", 9999)]
        
        for idx, (label, minutes) in enumerate(presets):
            with qcols[idx]:
                if st.button(label, key=f"qj_{label}", use_container_width=True):
                    if minutes == 9999:
                        target_idx = 0
                    else:
                        ist = pytz.timezone('Asia/Kolkata')
                        target_time = datetime.now(ist) - timedelta(minutes=minutes)
                        target_idx = min(
                            range(len(snapshot_times)),
                            key=lambda i: abs((snapshot_times[i] - target_time).total_seconds())
                        )
                    st.session_state.selected_time_index = target_idx
                    st.session_state.is_live_mode = False
                    st.rerun()
        
        # Get historical data if in historical mode
        if not st.session_state.is_live_mode and st.session_state.selected_time_index is not None:
            if st.session_state.selected_time_index < len(snapshot_times):
                selected_time = snapshot_times[st.session_state.selected_time_index]
                historical_data = config['data'].get(selected_time)
else:
    st.info("📝 No snapshots yet. Data will be captured automatically.")

# ============================================================================
# DATA FETCHING
# ============================================================================

st.markdown("---")

if historical_data and not st.session_state.is_live_mode:
    # Using historical data
    df = historical_data['df']
    futures_ltp = historical_data['futures_ltp']
    fetch_method = historical_data['fetch_method']
    atm_info = historical_data['atm_info']
    flow_metrics = historical_data['flow_metrics']
    
    is_historical = True
    hist_time = snapshot_times[st.session_state.selected_time_index]
    
    st.markdown(f"""
    <div class="hist-badge" style="width: 100%; text-align: center; padding: 15px;">
        📜 HISTORICAL MODE - Viewing data from {hist_time.strftime('%I:%M:%S %p IST')}
    </div>
    """, unsafe_allow_html=True)
    
else:
    # Fetch live data
    is_historical = False
    hist_time = None
    
    if not LIVE_MODULE_OK:
        st.error(f"❌ Live data module error: {IMPORT_ERR}")
        st.info("Make sure `live_data.py` is in the same folder as this file.")
        st.stop()
    
    with st.spinner(f"🔄 Fetching live {symbol} data..."):
        calc = st.session_state.calculator
        df, futures_ltp, fetch_method, atm_info, error = calc.fetch_live_data(
            symbol=symbol,
            strikes_range=strikes_range,
            expiry_index=expiry_index
        )
    
    # Show status log in expander
    with st.expander("📋 Connection Status Log"):
        status_log = calc.get_status_log()
        for log in status_log:
            if "SUCCESS" in log:
                st.markdown(f'<span class="status-log success">{log}</span>', unsafe_allow_html=True)
            elif "WARNING" in log:
                st.markdown(f'<span class="status-log warning">{log}</span>', unsafe_allow_html=True)
            elif "ERROR" in log:
                st.markdown(f'<span class="status-log error">{log}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="status-log info">{log}</span>', unsafe_allow_html=True)
    
    if error:
        st.error(f"❌ {error}")
        st.warning("""
        **Troubleshooting:**
        1. **Cloud Server Issue**: NSE blocks cloud server IPs. Try running locally.
        2. **Run locally**: `pip install streamlit pandas numpy plotly scipy requests pytz`
        3. **Then**: `streamlit run app.py`
        4. **VPN**: Try using an Indian VPN if running from outside India.
        """)
        st.stop()
    
    if df is None:
        st.error("❌ Failed to fetch data")
        st.stop()
    
    # Calculate flow metrics
    try:
        flow_metrics = calculate_flow_metrics(df, futures_ltp)
    except Exception as e:
        flow_metrics = None
    
    # Auto capture
    if st.session_state.auto_capture or st.session_state.force_capture:
        if capture_snapshot(df, futures_ltp, fetch_method, atm_info, flow_metrics, symbol, expiry_index):
            st.toast("📸 Snapshot captured!", icon="✅")
    
    st.markdown(f"""
    <div class="live-pulse" style="width: 100%; justify-content: center; padding: 15px;">
        <div class="live-dot"></div>
        LIVE DATA - {symbol} ({expiry_labels[expiry_index]}) via {fetch_method}
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# KEY METRICS
# ============================================================================

st.markdown("### 📊 Key Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

total_gex = float(df['Net_GEX_B'].sum())
call_gex = float(df['Call_GEX'].sum())
put_gex = float(df['Put_GEX'].sum())

with col1:
    delta_class = "delta-up" if total_gex > 0 else "delta-down"
    delta_text = "DAMPENING" if total_gex > 0 else "AMPLIFYING"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Net GEX</div>
        <div class="metric-value">{total_gex:.2f}</div>
        <div class="metric-delta {delta_class}">{delta_text}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Call GEX</div>
        <div class="metric-value" style="color: #39ff14;">{call_gex:.4f}B</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Put GEX</div>
        <div class="metric-value" style="color: #ff4757;">{put_gex:.4f}B</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Futures LTP</div>
        <div class="metric-value" style="color: #00f5ff;">₹{futures_ltp:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    straddle = atm_info['atm_straddle_premium'] if atm_info else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">ATM Straddle</div>
        <div class="metric-value" style="color: #ff00ff;">₹{straddle:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# FLOW ANALYSIS
# ============================================================================

if flow_metrics:
    st.markdown("---")
    st.markdown("### 📈 Flow Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        gex_bias = flow_metrics['gex_bias']
        gex_val = flow_metrics['gex_near_total']
        
        if "DAMPENING" in gex_bias:
            st.markdown(f"""
            <div class="dampening-box">
                <h3>GEX: {gex_bias}</h3>
                <p>Near-term: {gex_val:.2f}</p>
                <p style="font-size: 0.85rem; opacity: 0.7;">Market makers will stabilize price</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="amplifying-box">
                <h3>GEX: {gex_bias}</h3>
                <p>Near-term: {gex_val:.2f}</p>
                <p style="font-size: 0.85rem; opacity: 0.7;">Market makers will amplify moves</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        dex_bias = flow_metrics['dex_bias']
        dex_val = flow_metrics['dex_near_total']
        
        if "BULLISH" in dex_bias:
            st.markdown(f"""
            <div class="bullish-box">
                <h3 style="color: #00f5ff;">DEX: {dex_bias}</h3>
                <p style="color: #fff;">Near-term: {dex_val:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="bearish-box">
                <h3 style="color: #ff6600;">DEX: {dex_bias}</h3>
                <p style="color: #fff;">Near-term: {dex_val:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        combined = flow_metrics['combined_bias']
        st.markdown(f"""
        <div class="glass-card" style="text-align: center;">
            <div style="font-family: 'Rajdhani', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.9rem;">COMBINED SIGNAL</div>
            <div style="font-family: 'Orbitron', monospace; color: #fff; font-size: 1.1rem; margin-top: 0.5rem;">{combined}</div>
            <div style="font-family: 'Share Tech Mono', monospace; color: #00f5ff; margin-top: 0.5rem;">
                Signal: {flow_metrics['combined_signal']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# GAMMA FLIP ZONES
# ============================================================================

try:
    gamma_flips = detect_gamma_flips(df)
    if gamma_flips:
        st.markdown(f"""
        <div class="gamma-flip-alert">
            <strong>⚡ {len(gamma_flips)} Gamma Flip Zone(s) Detected!</strong> - High volatility transition areas
        </div>
        """, unsafe_allow_html=True)
        
        for flip in gamma_flips:
            st.caption(f"  • {flip['lower']} - {flip['upper']}: {flip['type']}")
except:
    gamma_flips = []

# ============================================================================
# CHARTS
# ============================================================================

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📊 GEX Profile", "📈 DEX Profile", "🎯 Hedging Pressure", "📋 Data Table"])

# Chart template
chart_template = dict(
    paper_bgcolor='rgba(10, 10, 15, 0.8)',
    plot_bgcolor='rgba(10, 10, 15, 0.8)',
    font=dict(family='Rajdhani, sans-serif', color='rgba(255,255,255,0.8)'),
    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.1)'),
    yaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.1)')
)

with tab1:
    mode_text = f"[HISTORICAL - {hist_time.strftime('%I:%M %p')}]" if is_historical else "[LIVE]"
    st.subheader(f"{symbol} Gamma Exposure {mode_text}")
    
    fig = go.Figure()
    
    colors = ['#39ff14' if x > 0 else '#ff4757' for x in df['Net_GEX_B']]
    
    fig.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Net_GEX_B'],
        orientation='h',
        marker_color=colors,
        marker_line_color=colors,
        marker_line_width=1,
        name='Net GEX',
        hovertemplate='<b>Strike:</b> %{y}<br><b>Net GEX:</b> %{x:.4f}B<extra></extra>'
    ))
    
    # Gamma flip zones
    if gamma_flips:
        max_gex = df['Net_GEX_B'].abs().max()
        for flip in gamma_flips:
            fig.add_shape(
                type="rect",
                y0=flip['lower'],
                y1=flip['upper'],
                x0=-max_gex * 1.5,
                x1=max_gex * 1.5,
                fillcolor="rgba(255, 215, 0, 0.15)",
                layer="below",
                line_width=0
            )
    
    fig.add_hline(
        y=futures_ltp,
        line_dash="dash",
        line_color="#00f5ff",
        line_width=3,
        annotation_text=f"Futures: ₹{futures_ltp:,.2f}",
        annotation_font_color="#00f5ff"
    )
    
    fig.update_layout(
        height=600,
        xaxis_title="Net GEX (Billions)",
        yaxis_title="Strike Price",
        hovermode='closest',
        **chart_template
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Interpretation
    if total_gex > 100:
        st.success("🟢 **Strong Volatility Dampening**: MMs will aggressively buy dips and sell rallies. Expect tight range.")
    elif total_gex > 0:
        st.info("🟢 **Mild Dampening**: Some price stabilization expected.")
    elif total_gex > -100:
        st.warning("🔴 **Mild Amplifying**: MMs may amplify moves. Trade with caution.")
    else:
        st.error("🔴 **Strong Volatility Amplifying**: High volatility! MMs will amplify directional moves.")

with tab2:
    st.subheader(f"{symbol} Delta Exposure")
    
    fig2 = go.Figure()
    
    dex_colors = ['#00f5ff' if x > 0 else '#ff6600' for x in df['Net_DEX_B']]
    
    fig2.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Net_DEX_B'],
        orientation='h',
        marker_color=dex_colors,
        name='Net DEX',
        hovertemplate='<b>Strike:</b> %{y}<br><b>Net DEX:</b> %{x:.4f}B<extra></extra>'
    ))
    
    fig2.add_hline(y=futures_ltp, line_dash="dash", line_color="#ff00ff", line_width=3)
    
    fig2.update_layout(
        height=600,
        xaxis_title="Net DEX (Billions)",
        yaxis_title="Strike Price",
        **chart_template
    )
    
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader(f"{symbol} Hedging Pressure Index")
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Hedging_Pressure'],
        orientation='h',
        marker=dict(
            color=df['Hedging_Pressure'],
            colorscale=[[0, '#ff4757'], [0.5, '#ffd700'], [1, '#39ff14']],
            showscale=True,
            colorbar=dict(title="Pressure %", tickfont=dict(color='white'))
        ),
        name='Hedging Pressure',
        hovertemplate='<b>Strike:</b> %{y}<br><b>Pressure:</b> %{x:.2f}%<extra></extra>'
    ))
    
    fig3.add_hline(y=futures_ltp, line_dash="dash", line_color="#00f5ff", line_width=3)
    
    fig3.update_layout(
        height=600,
        xaxis_title="Hedging Pressure (%)",
        yaxis_title="Strike Price",
        **chart_template
    )
    
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    st.subheader("Strike-wise Analysis")
    
    display_cols = ['Strike', 'Call_OI', 'Put_OI', 'Call_IV', 'Put_IV', 'Net_GEX_B', 'Net_DEX_B', 'Hedging_Pressure']
    display_df = df[[c for c in display_cols if c in df.columns]].copy()
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    csv = df.to_csv(index=False)
    timestamp_str = hist_time.strftime('%Y%m%d_%H%M') if hist_time else get_ist_time().strftime('%Y%m%d_%H%M')
    
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"NYZTrade_{symbol}_exp{expiry_index}_{timestamp_str}.csv",
        mime="text/csv",
        use_container_width=True
    )

# ============================================================================
# FOOTER
# ============================================================================

ist_time = get_ist_time()

st.markdown(f"""
<div class="ultra-footer">
    <span>⏰ {ist_time.strftime('%H:%M:%S')} IST</span> | 
    <span>📅 Expiry: {atm_info.get('expiry_date', 'N/A') if atm_info else 'N/A'}</span> | 
    <span>{'📜 Historical' if is_historical else '🔴 Live'}: {symbol}</span> | 
    <span>💡 NYZTrade YouTube</span>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# AUTO-REFRESH
# ============================================================================

if auto_refresh and user_tier == "premium" and st.session_state.is_live_mode:
    elapsed = time.time() - st.session_state.countdown_start
    if elapsed >= refresh_interval:
        st.session_state.countdown_start = time.time()
        st.rerun()
    else:
        time.sleep(1)
        st.rerun()
