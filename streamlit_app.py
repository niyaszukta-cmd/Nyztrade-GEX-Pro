"""
================================================================================
NYZTrade - Advanced GEX + DEX Analysis Dashboard
================================================================================
With Time Machine that works for ALL expiries (Weekly, Next Weekly, Monthly)
Updated Terminology:
- Positive GEX = Volatility Dampening
- Negative GEX = Volatility Amplifying

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

# Import calculator
try:
    from gex_calculator import EnhancedGEXDEXCalculator, calculate_dual_gex_dex_flow, detect_gamma_flip_zones
    CALCULATOR_AVAILABLE = True
except Exception as e:
    CALCULATOR_AVAILABLE = False
    IMPORT_ERROR = str(e)

# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

def check_password():
    """Returns True if user has entered correct password"""
    
    def password_entered():
        username = st.session_state["username"].strip().lower()
        password = st.session_state["password"]
        
        users = {
            "demo": "demo123",
            "premium": "premium123",
            "niyas": "nyztrade123"
        }
        
        if username in users and password == users[username]:
            st.session_state["password_correct"] = True
            st.session_state["authenticated_user"] = username
            del st.session_state["password"]
            return
        
        st.session_state["password_correct"] = False
        st.session_state["authenticated_user"] = None
    
    if "password_correct" not in st.session_state:
        st.markdown("## 🔐 NYZTrade Dashboard Login")
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.text_input("Username", key="username", placeholder="Enter username")
            st.text_input("Password", type="password", key="password", placeholder="Enter password")
            st.button("Login", on_click=password_entered, use_container_width=True)
            
            st.markdown("---")
            st.info("""
            **Demo Credentials:**
            - Free: `demo` / `demo123`
            - Premium: `premium` / `premium123`
            
            **Contact**: Subscribe to NYZTrade YouTube
            """)
        
        return False
    
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔐 NYZTrade Dashboard Login")
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.error("😕 Incorrect username or password")
            st.text_input("Username", key="username", placeholder="Enter username")
            st.text_input("Password", type="password", key="password", placeholder="Enter password")
            st.button("Login", on_click=password_entered, use_container_width=True)
        
        return False
    
    return True

def get_user_tier():
    if "authenticated_user" not in st.session_state:
        return "guest"
    username = st.session_state["authenticated_user"]
    return "premium" if username in ["premium", "niyas"] else "basic"

def get_ist_time():
    """Get current time in IST"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="NYZTrade - GEX Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check auth
if not check_password():
    st.stop()

user_tier = get_user_tier()

# ============================================================================
# SESSION STATE INITIALIZATION - FIXED FOR MULTIPLE EXPIRIES
# ============================================================================

def init_session_state():
    """Initialize all session state variables with expiry-specific storage"""
    defaults = {
        # Time Machine data - stored per symbol+expiry combination
        'snapshots_by_config': {},  # Key: "SYMBOL_EXPIRY_INDEX" -> {times: [], data: {}}
        'current_config_key': None,
        'selected_time_index': None,
        'is_live_mode': True,
        'last_capture_time': None,
        'auto_capture': True,
        'capture_interval': 3,
        'force_capture': False,
        # Settings
        'previous_symbol': None,
        'previous_expiry': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .danger-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .countdown-timer {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .time-machine-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #333;
    }
    .live-badge {
        background: linear-gradient(90deg, #00b894, #00cec9);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .hist-badge {
        background: linear-gradient(90deg, #fdcb6e, #e17055);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .dampening-box {
        background: linear-gradient(135deg, #00b894, #00cec9);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .amplifying-box {
        background: linear-gradient(135deg, #e74c3c, #c0392b);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TIME MACHINE FUNCTIONS - FIXED FOR MULTIPLE EXPIRIES
# ============================================================================

def get_config_key(symbol, expiry_index):
    """Generate unique key for symbol+expiry combination"""
    return f"{symbol}_{expiry_index}"

def get_current_snapshots():
    """Get snapshots for current symbol+expiry configuration"""
    key = st.session_state.current_config_key
    if key and key in st.session_state.snapshots_by_config:
        return st.session_state.snapshots_by_config[key]
    return {'times': [], 'data': {}}

def capture_snapshot(df, futures_ltp, fetch_method, atm_info, flow_metrics, symbol, expiry_index):
    """Capture snapshot for specific symbol+expiry configuration"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).replace(microsecond=0)
    
    # Check capture interval
    if st.session_state.last_capture_time:
        elapsed = (now - st.session_state.last_capture_time).total_seconds() / 60
        if elapsed < st.session_state.capture_interval and not st.session_state.force_capture:
            return False
    
    # Get config key
    config_key = get_config_key(symbol, expiry_index)
    
    # Initialize if needed
    if config_key not in st.session_state.snapshots_by_config:
        st.session_state.snapshots_by_config[config_key] = {'times': [], 'data': {}}
    
    config = st.session_state.snapshots_by_config[config_key]
    
    # Store snapshot
    config['data'][now] = {
        'df': df.copy(),
        'futures_ltp': futures_ltp,
        'fetch_method': fetch_method,
        'atm_info': atm_info.copy() if atm_info else None,
        'flow_metrics': flow_metrics.copy() if flow_metrics else None,
        'symbol': symbol,
        'expiry_index': expiry_index
    }
    
    # Add to times list
    if now not in config['times']:
        config['times'].append(now)
        config['times'].sort()
    
    st.session_state.last_capture_time = now
    st.session_state.force_capture = False
    
    # Limit to 500 snapshots per config
    while len(config['times']) > 500:
        oldest = config['times'].pop(0)
        config['data'].pop(oldest, None)
    
    return True

def render_time_machine(symbol, expiry_index):
    """Render Time Machine UI for specific symbol+expiry"""
    st.markdown("---")
    
    # Update current config key
    config_key = get_config_key(symbol, expiry_index)
    
    # Check if config changed
    if st.session_state.current_config_key != config_key:
        st.session_state.current_config_key = config_key
        st.session_state.selected_time_index = None
        st.session_state.is_live_mode = True
    
    # Get snapshots for this config
    config = get_current_snapshots()
    snapshot_times = config.get('times', [])
    snapshot_data = config.get('data', {})
    
    # Expiry labels
    expiry_labels = {0: "Current Weekly", 1: "Next Weekly", 2: "Monthly"}
    expiry_label = expiry_labels.get(expiry_index, f"Expiry {expiry_index}")
    
    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown(f"### ⏰ Time Machine - {symbol} ({expiry_label})")
    
    with col2:
        if st.session_state.is_live_mode:
            st.markdown('<span class="live-badge">🟢 LIVE</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="hist-badge">📜 HISTORY</span>', unsafe_allow_html=True)
    
    with col3:
        if not st.session_state.is_live_mode:
            if st.button("🔴 Go Live", use_container_width=True, key="go_live_btn"):
                st.session_state.is_live_mode = True
                st.session_state.selected_time_index = None
                st.rerun()
    
    # No snapshots yet
    if not snapshot_times:
        st.info(f"📝 No snapshots yet for {symbol} ({expiry_label}). Data will be captured automatically.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.auto_capture = st.checkbox(
                "🔄 Auto-capture enabled",
                value=st.session_state.auto_capture,
                key="auto_cap_empty"
            )
        with col2:
            st.session_state.capture_interval = st.selectbox(
                "Capture interval",
                options=[1, 2, 3, 5, 10],
                index=[1, 2, 3, 5, 10].index(st.session_state.capture_interval) if st.session_state.capture_interval in [1, 2, 3, 5, 10] else 2,
                format_func=lambda x: f"{x} min",
                key="interval_empty"
            )
        return None
    
    # Show time range info
    first_time = snapshot_times[0]
    last_time = snapshot_times[-1]
    
    st.caption(f"📊 **{len(snapshot_times)} snapshots** for {symbol} ({expiry_label}) | {first_time.strftime('%I:%M %p')} → {last_time.strftime('%I:%M %p')}")
    
    # Time Slider
    if len(snapshot_times) > 1:
        time_labels = [t.strftime('%I:%M %p') for t in snapshot_times]
        
        current_idx = st.session_state.selected_time_index
        if current_idx is None or current_idx >= len(snapshot_times):
            current_idx = len(snapshot_times) - 1
        
        selected_idx = st.select_slider(
            "🕐 Select Time Point",
            options=list(range(len(snapshot_times))),
            value=current_idx,
            format_func=lambda x: time_labels[x],
            key="time_slider"
        )
        
        # If not at latest, switch to historical mode
        if selected_idx != len(snapshot_times) - 1:
            st.session_state.is_live_mode = False
            st.session_state.selected_time_index = selected_idx
        
        # Quick Jump Buttons
        st.markdown("**⚡ Quick Jump:**")
        cols = st.columns(8)
        presets = [
            ("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60),
            ("2h", 120), ("3h", 180), ("Start", 9999)
        ]
        
        for idx, (label, minutes) in enumerate(presets):
            with cols[idx]:
                if st.button(label, key=f"preset_{label}_{config_key}", use_container_width=True):
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
    
    # Capture Settings
    with st.expander("⚙️ Capture Settings"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.session_state.auto_capture = st.checkbox(
                "🔄 Auto-capture",
                value=st.session_state.auto_capture,
                key="auto_cap_settings"
            )
        
        with col2:
            st.session_state.capture_interval = st.selectbox(
                "Interval",
                options=[1, 2, 3, 5, 10],
                index=[1, 2, 3, 5, 10].index(st.session_state.capture_interval) if st.session_state.capture_interval in [1, 2, 3, 5, 10] else 2,
                format_func=lambda x: f"{x} min",
                key="interval_settings"
            )
        
        with col3:
            if st.button("🗑️ Clear This Config", use_container_width=True):
                if config_key in st.session_state.snapshots_by_config:
                    st.session_state.snapshots_by_config[config_key] = {'times': [], 'data': {}}
                st.session_state.selected_time_index = None
                st.session_state.is_live_mode = True
                st.rerun()
        
        # Show all configs
        st.markdown("**📁 All Stored Configurations:**")
        for key in st.session_state.snapshots_by_config:
            count = len(st.session_state.snapshots_by_config[key].get('times', []))
            if count > 0:
                parts = key.split('_')
                sym = parts[0]
                exp = int(parts[1]) if len(parts) > 1 else 0
                exp_lbl = expiry_labels.get(exp, f"Exp {exp}")
                st.caption(f"• {sym} ({exp_lbl}): {count} snapshots")
    
    # Return historical data if in historical mode
    if not st.session_state.is_live_mode and st.session_state.selected_time_index is not None:
        if st.session_state.selected_time_index < len(snapshot_times):
            selected_time = snapshot_times[st.session_state.selected_time_index]
            return snapshot_data.get(selected_time)
    
    return None


def create_history_chart(symbol, expiry_index):
    """Create intraday history chart for specific config"""
    config = get_current_snapshots()
    snapshot_times = config.get('times', [])
    snapshot_data = config.get('data', {})
    
    if len(snapshot_times) < 2:
        return None
    
    times = []
    prices = []
    gex_values = []
    
    for t in snapshot_times:
        if t in snapshot_data:
            snap = snapshot_data[t]
            times.append(t)
            prices.append(snap['futures_ltp'])
            
            if snap.get('flow_metrics') and 'gex_near_total' in snap['flow_metrics']:
                gex_values.append(snap['flow_metrics']['gex_near_total'])
            else:
                gex_values.append(float(snap['df']['Net_GEX_B'].sum()))
    
    if len(times) < 2:
        return None
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.08,
        subplot_titles=('📈 Futures Price', '📊 GEX Flow')
    )
    
    # Price line
    fig.add_trace(
        go.Scatter(
            x=times, y=prices,
            mode='lines+markers',
            line=dict(color='#6c5ce7', width=2),
            marker=dict(size=5),
            name='Futures',
            hovertemplate='%{x|%I:%M %p}<br>₹%{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # GEX bars
    gex_colors = ['#00d4aa' if x > 0 else '#ff6b6b' for x in gex_values]
    fig.add_trace(
        go.Bar(
            x=times, y=gex_values,
            marker_color=gex_colors,
            name='GEX Flow',
            hovertemplate='%{x|%I:%M %p}<br>GEX: %{y:.2f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Mark selected time
    if not st.session_state.is_live_mode and st.session_state.selected_time_index is not None:
        if st.session_state.selected_time_index < len(snapshot_times):
            selected_time = snapshot_times[st.session_state.selected_time_index]
            fig.add_vline(x=selected_time, line_dash="dash", line_color="orange", line_width=2)
    
    fig.update_layout(
        height=300,
        showlegend=False,
        template='plotly_dark',
        margin=dict(l=50, r=50, t=50, b=30),
        paper_bgcolor='rgba(26, 26, 46, 0.8)',
        plot_bgcolor='rgba(26, 26, 46, 0.8)'
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    
    return fig


# ============================================================================
# HEADER
# ============================================================================

st.markdown('<p class="main-header">📊 NYZTrade - Advanced GEX + DEX Analysis</p>', unsafe_allow_html=True)
st.markdown("**Real-time Gamma & Delta Exposure Analysis | Time Machine for All Expiries**")

# User badge
if user_tier == "premium":
    st.sidebar.success("👑 **Premium Member**")
else:
    st.sidebar.info(f"🆓 **Free Member** | User: {st.session_state.get('authenticated_user', 'guest')}")

# Logout
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ============================================================================
# SIDEBAR CONTROLS
# ============================================================================

st.sidebar.header("⚙️ Dashboard Settings")

symbol = st.sidebar.selectbox(
    "Select Index",
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"],
    index=0
)

strikes_range = st.sidebar.slider(
    "Strikes Range",
    min_value=5,
    max_value=20,
    value=12
)

expiry_index = st.sidebar.selectbox(
    "Expiry Selection",
    [0, 1, 2],
    format_func=lambda x: ["Current Weekly", "Next Weekly", "Monthly"][x],
    index=0
)

# Time Machine Stats
st.sidebar.markdown("---")
st.sidebar.subheader("⏰ Time Machine Stats")

config_key = get_config_key(symbol, expiry_index)
config = st.session_state.snapshots_by_config.get(config_key, {'times': []})
snapshot_count = len(config.get('times', []))

if snapshot_count > 0:
    st.sidebar.metric("Snapshots", snapshot_count)
    st.sidebar.caption(f"First: {config['times'][0].strftime('%I:%M %p')}")
    st.sidebar.caption(f"Last: {config['times'][-1].strftime('%I:%M %p')}")
else:
    st.sidebar.info("No snapshots for this config")

# Manual Capture
if st.sidebar.button("📸 Capture Now", use_container_width=True, type="primary"):
    st.session_state.force_capture = True

# Auto-refresh (Premium)
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Auto-Refresh")

if user_tier == "premium":
    auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=False)
    if auto_refresh:
        refresh_interval = st.sidebar.slider("Interval (sec)", 30, 300, 60, step=30)
        
        if 'countdown_start' not in st.session_state:
            st.session_state.countdown_start = time.time()
        
        elapsed = time.time() - st.session_state.countdown_start
        remaining = max(0, refresh_interval - int(elapsed))
        st.sidebar.markdown(f'<div class="countdown-timer">⏱️ {remaining}s</div>', unsafe_allow_html=True)
else:
    st.sidebar.info("🔒 Auto-refresh: Premium only")
    auto_refresh = False
    refresh_interval = 60

# Manual Refresh
if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    st.cache_data.clear()
    if 'countdown_start' in st.session_state:
        st.session_state.countdown_start = time.time()
    st.rerun()

# ============================================================================
# TIME MACHINE UI
# ============================================================================

historical_data = render_time_machine(symbol, expiry_index)

# History Chart
config = get_current_snapshots()
if len(config.get('times', [])) >= 2:
    history_chart = create_history_chart(symbol, expiry_index)
    if history_chart:
        st.plotly_chart(history_chart, use_container_width=True)

# ============================================================================
# DATA FETCHING
# ============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def fetch_data(symbol, strikes_range, expiry_index):
    if not CALCULATOR_AVAILABLE:
        return None, None, None, None, f"Calculator not available: {IMPORT_ERROR}"
    
    try:
        calculator = EnhancedGEXDEXCalculator()
        df, futures_ltp, fetch_method, atm_info = calculator.fetch_and_calculate_gex_dex(
            symbol=symbol,
            strikes_range=strikes_range,
            expiry_index=expiry_index
        )
        return df, futures_ltp, fetch_method, atm_info, None
    except Exception as e:
        return None, None, None, None, str(e)

# ============================================================================
# MAIN ANALYSIS
# ============================================================================

st.markdown("---")

# Check if viewing historical data
if historical_data and not st.session_state.is_live_mode:
    df = historical_data['df']
    futures_ltp = historical_data['futures_ltp']
    fetch_method = historical_data['fetch_method']
    atm_info = historical_data['atm_info']
    flow_metrics = historical_data['flow_metrics']
    
    is_historical = True
    config = get_current_snapshots()
    hist_time = config['times'][st.session_state.selected_time_index]
    
    st.warning(f"📜 **HISTORICAL MODE** - Viewing {symbol} data from {hist_time.strftime('%I:%M:%S %p IST')}")
else:
    is_historical = False
    hist_time = None
    
    with st.spinner(f"🔄 Fetching live {symbol} data..."):
        df, futures_ltp, fetch_method, atm_info, error = fetch_data(symbol, strikes_range, expiry_index)
    
    if error:
        st.error(f"❌ Error: {error}")
        st.info("""
        **Troubleshooting:**
        1. Make sure gex_calculator.py is in the same folder
        2. Check requirements.txt includes all dependencies
        3. Try refreshing the page
        """)
        st.stop()
    
    if df is None:
        st.error("❌ Failed to fetch data")
        st.stop()
    
    # Calculate flow metrics
    try:
        flow_metrics = calculate_dual_gex_dex_flow(df, futures_ltp)
    except Exception as e:
        flow_metrics = None
    
    # Auto-capture
    if st.session_state.auto_capture or st.session_state.force_capture:
        if capture_snapshot(df, futures_ltp, fetch_method, atm_info, flow_metrics, symbol, expiry_index):
            st.toast("📸 Snapshot captured!", icon="✅")
    
    expiry_labels = {0: "Current Weekly", 1: "Next Weekly", 2: "Monthly"}
    st.success(f"🔴 **LIVE MODE** - {symbol} ({expiry_labels.get(expiry_index, '')}) via {fetch_method}")

# ============================================================================
# KEY METRICS
# ============================================================================

st.subheader("📊 Key Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_gex = float(df['Net_GEX_B'].sum())
    st.metric(
        "Total Net GEX",
        f"{total_gex:.2f}",
        delta="Dampening" if total_gex > 0 else "Amplifying"
    )

with col2:
    call_gex = float(df['Call_GEX'].sum())
    st.metric("Call GEX", f"{call_gex:.4f}B")

with col3:
    put_gex = float(df['Put_GEX'].sum())
    st.metric("Put GEX", f"{put_gex:.4f}B")

with col4:
    st.metric("Futures LTP", f"₹{futures_ltp:,.2f}")

with col5:
    if atm_info:
        st.metric("ATM Straddle", f"₹{atm_info['atm_straddle_premium']:.2f}")

# ============================================================================
# FLOW METRICS WITH UPDATED TERMINOLOGY
# ============================================================================

if flow_metrics:
    st.markdown("---")
    st.subheader("📈 Flow Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        gex_bias = flow_metrics['gex_near_bias']
        gex_val = flow_metrics['gex_near_total']
        
        if "DAMPENING" in gex_bias:
            st.markdown(f"""
            <div class="dampening-box">
                <h4>GEX: {gex_bias}</h4>
                <p>Near-term: {gex_val:.2f}</p>
                <small>Market makers will stabilize price</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="amplifying-box">
                <h4>GEX: {gex_bias}</h4>
                <p>Near-term: {gex_val:.2f}</p>
                <small>Market makers will amplify moves</small>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        dex_bias = flow_metrics['dex_near_bias']
        dex_val = flow_metrics['dex_near_total']
        
        if "BULLISH" in dex_bias:
            st.markdown(f'<div class="success-box"><b>DEX:</b> {dex_bias}<br>Value: {dex_val:.2f}</div>', unsafe_allow_html=True)
        elif "BEARISH" in dex_bias:
            st.markdown(f'<div class="danger-box"><b>DEX:</b> {dex_bias}<br>Value: {dex_val:.2f}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="warning-box"><b>DEX:</b> {dex_bias}<br>Value: {dex_val:.2f}</div>', unsafe_allow_html=True)
    
    with col3:
        combined_bias = flow_metrics['combined_bias']
        combined_val = flow_metrics['combined_signal']
        st.info(f"**Combined:** {combined_bias}\n\nSignal: {combined_val:.2f}")

# ============================================================================
# GAMMA FLIP ZONES
# ============================================================================

gamma_flip_zones = []
try:
    gamma_flip_zones = detect_gamma_flip_zones(df)
    if gamma_flip_zones:
        st.warning(f"⚡ **{len(gamma_flip_zones)} Gamma Flip Zone(s) Detected!** - High volatility areas")
        for zone in gamma_flip_zones:
            st.caption(f"  • {zone['lower_strike']} - {zone['upper_strike']}: {zone['flip_type']}")
except:
    pass

# ============================================================================
# CHARTS
# ============================================================================

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 GEX Profile", "📈 DEX Profile", "🎯 Hedging Pressure", "📋 Data Table", "💡 Strategies"])

# TAB 1: GEX Profile
with tab1:
    mode_text = f"[HISTORICAL - {hist_time.strftime('%I:%M %p')}]" if is_historical else "[LIVE]"
    st.subheader(f"{symbol} Gamma Exposure Profile {mode_text}")
    
    fig = go.Figure()
    
    # Colors based on volatility impact
    colors = ['#00d4aa' if x > 0 else '#ff6b6b' for x in df['Net_GEX_B']]
    
    fig.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Net_GEX_B'],
        orientation='h',
        marker_color=colors,
        name='Net GEX',
        hovertemplate='<b>Strike:</b> %{y}<br><b>Net GEX:</b> %{x:.4f}B<extra></extra>'
    ))
    
    # Gamma flip zones
    if gamma_flip_zones:
        max_gex = df['Net_GEX_B'].abs().max()
        for zone in gamma_flip_zones:
            fig.add_shape(
                type="rect",
                y0=zone['lower_strike'],
                y1=zone['upper_strike'],
                x0=-max_gex * 1.5,
                x1=max_gex * 1.5,
                fillcolor="yellow",
                opacity=0.2,
                layer="below",
                line_width=0
            )
    
    fig.add_hline(
        y=futures_ltp,
        line_dash="dash",
        line_color="blue",
        line_width=3,
        annotation_text=f"Futures: {futures_ltp:,.2f}"
    )
    
    fig.update_layout(
        height=600,
        xaxis_title="Net GEX (Billions)",
        yaxis_title="Strike Price",
        template='plotly_white',
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Updated interpretation
    if total_gex > 50:
        st.success("🟢 **Strong Volatility Dampening**: Market makers will buy dips and sell rallies. Expect range-bound/sideways action.")
    elif total_gex > 0:
        st.info("🟢 **Mild Volatility Dampening**: Some stabilization expected, but moves still possible.")
    elif total_gex > -50:
        st.warning("🔴 **Mild Volatility Amplifying**: Market makers may amplify moves. Stay cautious.")
    else:
        st.error("🔴 **Strong Volatility Amplifying**: High volatility expected! Market makers will amplify directional moves.")

# TAB 2: DEX Profile
with tab2:
    mode_text = f"[HISTORICAL]" if is_historical else "[LIVE]"
    st.subheader(f"{symbol} Delta Exposure Profile {mode_text}")
    
    fig2 = go.Figure()
    
    dex_colors = ['#00d4aa' if x > 0 else '#ff6b6b' for x in df['Net_DEX_B']]
    
    fig2.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Net_DEX_B'],
        orientation='h',
        marker_color=dex_colors,
        name='Net DEX',
        hovertemplate='<b>Strike:</b> %{y}<br><b>Net DEX:</b> %{x:.4f}B<extra></extra>'
    ))
    
    fig2.add_hline(
        y=futures_ltp,
        line_dash="dash",
        line_color="blue",
        line_width=3
    )
    
    fig2.update_layout(
        height=600,
        xaxis_title="Net DEX (Billions)",
        yaxis_title="Strike Price",
        template='plotly_white'
    )
    
    st.plotly_chart(fig2, use_container_width=True)

# TAB 3: Hedging Pressure
with tab3:
    st.subheader(f"{symbol} Hedging Pressure Index")
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Hedging_Pressure'],
        orientation='h',
        marker=dict(
            color=df['Hedging_Pressure'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Pressure %")
        ),
        name='Hedging Pressure',
        hovertemplate='<b>Strike:</b> %{y}<br><b>Pressure:</b> %{x:.2f}%<extra></extra>'
    ))
    
    fig3.add_hline(y=futures_ltp, line_dash="dash", line_color="blue", line_width=3)
    
    fig3.update_layout(
        height=600,
        xaxis_title="Hedging Pressure (%)",
        yaxis_title="Strike Price",
        template='plotly_white'
    )
    
    st.plotly_chart(fig3, use_container_width=True)
    
    st.info("""
    **Hedging Pressure Interpretation:**
    - **+100%**: Maximum dampening - Strong support level
    - **-100%**: Maximum amplifying - High volatility zone
    - **0%**: Neutral - No significant hedging activity
    """)

# TAB 4: Data Table
with tab4:
    st.subheader("Strike-wise Analysis")
    
    if is_historical:
        st.caption(f"📜 Historical data from {hist_time.strftime('%I:%M:%S %p IST')}")
    
    display_cols = ['Strike', 'Call_OI', 'Put_OI', 'Net_GEX_B', 'Net_DEX_B', 'Hedging_Pressure', 'Total_Volume']
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

# TAB 5: Strategies
with tab5:
    st.subheader("💡 Trading Strategies Based on GEX/DEX")
    
    if is_historical:
        st.info(f"📜 Strategies based on historical data from {hist_time.strftime('%I:%M %p IST')}")
    
    if flow_metrics and atm_info:
        gex_val = flow_metrics['gex_near_total']
        dex_val = flow_metrics['dex_near_total']
        
        st.markdown("### 📊 Current Market Setup")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("GEX Flow", f"{gex_val:.2f}", "Dampening" if gex_val > 0 else "Amplifying")
            st.metric("DEX Flow", f"{dex_val:.2f}", "Bullish" if dex_val > 0 else "Bearish")
        with col2:
            st.metric("ATM Strike", f"{atm_info['atm_strike']}")
            st.metric("Straddle Premium", f"₹{atm_info['atm_straddle_premium']:.2f}")
        
        st.markdown("---")
        
        # Strategy recommendations based on volatility regime
        if gex_val > 50:
            st.success("### 🟢 Volatility Dampening Regime")
            st.markdown("""
            **Market Behavior:** Range-bound, mean-reverting
            
            **Recommended Strategies:**
            """)
            
            st.code(f"""
Strategy 1: Iron Condor (High Probability)
------------------------------------------
Sell {symbol} {int(futures_ltp + 100)} CE
Buy  {symbol} {int(futures_ltp + 200)} CE  
Sell {symbol} {int(futures_ltp - 100)} PE
Buy  {symbol} {int(futures_ltp - 200)} PE

Expected Range: {int(futures_ltp - 100)} to {int(futures_ltp + 100)}
Risk: MODERATE | Reward: Premium collected
            """)
            
            st.code(f"""
Strategy 2: Short Straddle (Aggressive)
---------------------------------------
Sell {symbol} {atm_info['atm_strike']} CE
Sell {symbol} {atm_info['atm_strike']} PE

Premium: ₹{atm_info['atm_straddle_premium']:.2f}
Max Profit: At ATM strike
Risk: UNLIMITED - Use strict stops!
            """)
            
        elif gex_val < -50:
            st.error("### 🔴 Volatility Amplifying Regime")
            st.markdown("""
            **Market Behavior:** Trending, breakout-prone
            
            **Recommended Strategies:**
            """)
            
            st.code(f"""
Strategy 1: Long Straddle (Volatility Play)
-------------------------------------------
Buy {symbol} {atm_info['atm_strike']} CE
Buy {symbol} {atm_info['atm_strike']} PE

Cost: ₹{atm_info['atm_straddle_premium']:.2f}
Upper BE: {atm_info['atm_strike'] + atm_info['atm_straddle_premium']:.0f}
Lower BE: {atm_info['atm_strike'] - atm_info['atm_straddle_premium']:.0f}
Risk: Premium paid | Reward: UNLIMITED
            """)
            
            if dex_val > 20:
                st.code(f"""
Strategy 2: Bull Call Spread (Directional)
------------------------------------------
Buy  {symbol} {int(futures_ltp)} CE
Sell {symbol} {int(futures_ltp + 150)} CE

Bias: BULLISH (DEX confirms)
Risk: DEFINED
                """)
            elif dex_val < -20:
                st.code(f"""
Strategy 2: Bear Put Spread (Directional)
-----------------------------------------
Buy  {symbol} {int(futures_ltp)} PE
Sell {symbol} {int(futures_ltp - 150)} PE

Bias: BEARISH (DEX confirms)
Risk: DEFINED
                """)
        else:
            st.warning("### ⚖️ Neutral/Transitional Regime")
            st.markdown("""
            **Market Behavior:** Mixed signals, wait for clarity
            
            **Recommended:** Wait for stronger GEX signal or trade with tight stops
            """)
        
        st.markdown("---")
        st.markdown("### ⚠️ Risk Management Rules")
        st.markdown("""
        1. **Position Size:** Max 2% capital per trade
        2. **Stop Loss:** Always use - especially in amplifying regime
        3. **Theta Decay:** Monitor time decay in long positions
        4. **Gamma Flip Zones:** Avoid tight stops near flip zones
        5. **Take Profit:** 50-70% of max profit for credit strategies
        """)
    else:
        st.warning("Flow metrics unavailable")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

ist_time = get_ist_time()

with col1:
    st.info(f"⏰ {ist_time.strftime('%H:%M:%S')} IST")

with col2:
    if atm_info:
        st.info(f"📅 Expiry: {atm_info.get('expiry_date', 'N/A')}")

with col3:
    if is_historical:
        st.warning(f"📜 Historical: {hist_time.strftime('%I:%M %p')}")
    else:
        st.success(f"🔴 Live: {symbol}")

with col4:
    if gamma_flip_zones:
        st.warning(f"⚡ {len(gamma_flip_zones)} Flip Zone(s)")
    else:
        st.success("✅ No Flip Zones")

st.markdown(f"**💡 NYZTrade YouTube | Data: {fetch_method} | Config: {symbol}_Exp{expiry_index}**")

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
