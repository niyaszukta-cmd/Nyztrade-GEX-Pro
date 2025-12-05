import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import hashlib
import hmac
import pytz

# Try importing calculator
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
    premium_users = ["premium", "niyas"]
    
    return "premium" if username in premium_users else "basic"

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
# SESSION STATE INITIALIZATION FOR TIME MACHINE
# ============================================================================

def init_time_machine_state():
    """Initialize all Time Machine session state variables"""
    defaults = {
        'data_snapshots': {},
        'snapshot_times': [],
        'selected_time_index': None,
        'is_live_mode': True,
        'last_capture_time': None,
        'auto_capture': True,
        'capture_interval': 3,
        'force_capture': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_time_machine_state()

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
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
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
    .time-machine-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .live-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #00ff88;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    .historical-indicator {
        color: #ffa500;
        font-weight: bold;
    }
    @keyframes pulse {
        0% { opacity: 1; box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
        50% { opacity: 0.7; box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
        100% { opacity: 1; box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TIME MACHINE FUNCTIONS
# ============================================================================

def capture_snapshot(df, futures_ltp, fetch_method, atm_info, flow_metrics):
    """Capture current data as a snapshot for Time Machine"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).replace(microsecond=0)
    
    # Check capture interval
    if st.session_state.last_capture_time:
        elapsed = (now - st.session_state.last_capture_time).total_seconds() / 60
        if elapsed < st.session_state.capture_interval:
            return False
    
    # Store snapshot
    st.session_state.data_snapshots[now] = {
        'df': df.copy(),
        'futures_ltp': futures_ltp,
        'fetch_method': fetch_method,
        'atm_info': atm_info.copy() if atm_info else None,
        'flow_metrics': flow_metrics.copy() if flow_metrics else None
    }
    
    # Add to times list
    if now not in st.session_state.snapshot_times:
        st.session_state.snapshot_times.append(now)
        st.session_state.snapshot_times.sort()
    
    st.session_state.last_capture_time = now
    
    # Limit to 500 snapshots (memory management)
    while len(st.session_state.snapshot_times) > 500:
        oldest = st.session_state.snapshot_times.pop(0)
        st.session_state.data_snapshots.pop(oldest, None)
    
    return True


def render_time_machine():
    """Render the Time Machine UI with slider"""
    st.markdown("---")
    
    # Header row
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown("### ⏰ Time Machine - Backtest Mode")
    
    with col2:
        if st.session_state.is_live_mode:
            st.markdown('<span class="live-indicator"></span> **LIVE**', unsafe_allow_html=True)
        else:
            st.markdown('<span class="historical-indicator">📜 HISTORICAL</span>', unsafe_allow_html=True)
    
    with col3:
        if not st.session_state.is_live_mode:
            if st.button("🔴 Go Live", use_container_width=True, key="go_live_btn"):
                st.session_state.is_live_mode = True
                st.session_state.selected_time_index = None
                st.rerun()
    
    # No snapshots yet
    if not st.session_state.snapshot_times:
        st.info("📝 No historical data yet. Snapshots will be captured automatically every few minutes.")
        
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
    first_time = st.session_state.snapshot_times[0]
    last_time = st.session_state.snapshot_times[-1]
    
    st.caption(f"📊 **{len(st.session_state.snapshot_times)} snapshots** | {first_time.strftime('%I:%M %p')} → {last_time.strftime('%I:%M %p')}")
    
    # Time Slider
    if len(st.session_state.snapshot_times) > 1:
        time_labels = [t.strftime('%I:%M %p') for t in st.session_state.snapshot_times]
        
        current_idx = st.session_state.selected_time_index
        if current_idx is None:
            current_idx = len(st.session_state.snapshot_times) - 1
        
        selected_idx = st.select_slider(
            "🕐 Select Time Point",
            options=list(range(len(st.session_state.snapshot_times))),
            value=current_idx,
            format_func=lambda x: time_labels[x],
            key="time_slider"
        )
        
        # If not at latest, switch to historical mode
        if selected_idx != len(st.session_state.snapshot_times) - 1:
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
                if st.button(label, key=f"preset_{minutes}", use_container_width=True):
                    if minutes == 9999:
                        target_idx = 0
                    else:
                        ist = pytz.timezone('Asia/Kolkata')
                        target_time = datetime.now(ist) - timedelta(minutes=minutes)
                        # Find closest snapshot
                        target_idx = min(
                            range(len(st.session_state.snapshot_times)),
                            key=lambda i: abs((st.session_state.snapshot_times[i] - target_time).total_seconds())
                        )
                    st.session_state.selected_time_index = target_idx
                    st.session_state.is_live_mode = False
                    st.rerun()
    
    # Capture Settings Expander
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
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.data_snapshots = {}
                st.session_state.snapshot_times = []
                st.session_state.selected_time_index = None
                st.session_state.is_live_mode = True
                st.rerun()
    
    # Return historical data if in historical mode
    if not st.session_state.is_live_mode and st.session_state.selected_time_index is not None:
        selected_time = st.session_state.snapshot_times[st.session_state.selected_time_index]
        return st.session_state.data_snapshots.get(selected_time)
    
    return None


def create_history_chart():
    """Create intraday price and GEX flow history chart"""
    if len(st.session_state.snapshot_times) < 2:
        return None
    
    times = []
    prices = []
    gex_values = []
    
    for t in st.session_state.snapshot_times:
        if t in st.session_state.data_snapshots:
            snapshot = st.session_state.data_snapshots[t]
            times.append(t)
            prices.append(snapshot['futures_ltp'])
            
            # Get GEX total from flow_metrics or calculate from df
            if snapshot.get('flow_metrics') and 'gex_near_total' in snapshot['flow_metrics']:
                gex_values.append(snapshot['flow_metrics']['gex_near_total'])
            else:
                gex_values.append(float(snapshot['df']['Net_GEX_B'].sum()))
    
    if len(times) < 2:
        return None
    
    # Create subplot with price on top, GEX below
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
            hovertemplate='%{x|%I:%M %p}<br>GEX: %{y:.4f}B<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Mark selected time if in historical mode
    if not st.session_state.is_live_mode and st.session_state.selected_time_index is not None:
        selected_time = st.session_state.snapshot_times[st.session_state.selected_time_index]
        if selected_time in st.session_state.data_snapshots:
            selected_price = st.session_state.data_snapshots[selected_time]['futures_ltp']
            fig.add_vline(x=selected_time, line_dash="dash", line_color="orange", line_width=2)
            fig.add_annotation(
                x=selected_time, y=selected_price,
                text="📍 Selected",
                showarrow=True, arrowhead=2,
                row=1, col=1
            )
    
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
st.markdown("**Real-time Gamma & Delta Exposure Analysis for Indian Markets | With Time Machine Backtest**")

# User badge
if user_tier == "premium":
    st.sidebar.success("👑 **Premium Member**")
else:
    st.sidebar.info(f"🆓 **Free Member** | User: {st.session_state.get('authenticated_user', 'guest')}")

# Logout button
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

# Time Machine Stats in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("⏰ Time Machine Stats")

if st.session_state.snapshot_times:
    st.sidebar.metric("Snapshots", len(st.session_state.snapshot_times))
    st.sidebar.caption(f"First: {st.session_state.snapshot_times[0].strftime('%I:%M %p')}")
    st.sidebar.caption(f"Last: {st.session_state.snapshot_times[-1].strftime('%I:%M %p')}")
else:
    st.sidebar.info("No snapshots yet")

# Manual Capture Button
if st.sidebar.button("📸 Capture Now", use_container_width=True, type="primary"):
    st.session_state.force_capture = True

# Auto-refresh
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Auto-Refresh")

if user_tier == "premium":
    auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=False)
    if auto_refresh:
        refresh_interval = st.sidebar.slider(
            "Interval (seconds)",
            min_value=30,
            max_value=300,
            value=60,
            step=30
        )
        
        if 'countdown_start' not in st.session_state:
            st.session_state.countdown_start = time.time()
        
        elapsed = time.time() - st.session_state.countdown_start
        remaining = max(0, refresh_interval - int(elapsed))
        
        countdown_placeholder = st.sidebar.empty()
        countdown_placeholder.markdown(f'<div class="countdown-timer">⏱️ Next refresh: {remaining}s</div>', unsafe_allow_html=True)
else:
    st.sidebar.info("🔒 Auto-refresh: Premium only")
    auto_refresh = False
    refresh_interval = 60

# Manual refresh
if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    st.cache_data.clear()
    if 'countdown_start' in st.session_state:
        st.session_state.countdown_start = time.time()
    st.rerun()

# ============================================================================
# TIME MACHINE UI
# ============================================================================

historical_data = render_time_machine()

# Display History Chart if we have snapshots
if len(st.session_state.snapshot_times) >= 2:
    history_chart = create_history_chart()
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
# MAIN ANALYSIS - LOAD DATA
# ============================================================================

st.markdown("---")

# Check if we're viewing historical data
if historical_data and not st.session_state.is_live_mode:
    # Use historical data
    df = historical_data['df']
    futures_ltp = historical_data['futures_ltp']
    fetch_method = historical_data['fetch_method']
    atm_info = historical_data['atm_info']
    flow_metrics = historical_data['flow_metrics']
    
    is_historical = True
    hist_time = st.session_state.snapshot_times[st.session_state.selected_time_index]
    
    st.warning(f"📜 **HISTORICAL MODE** - Viewing data from {hist_time.strftime('%I:%M:%S %p IST')}")
else:
    # Fetch live data
    is_historical = False
    hist_time = None
    
    with st.spinner(f"🔄 Fetching live {symbol} data..."):
        df, futures_ltp, fetch_method, atm_info, error = fetch_data(symbol, strikes_range, expiry_index)
    
    if error:
        st.error(f"❌ Error: {error}")
        st.info("""
        **Troubleshooting:**
        1. Make sure gex_calculator.py is uploaded
        2. Check requirements.txt includes: streamlit pandas numpy plotly scipy requests pytz
        3. Wait 1-2 minutes for dependencies
        """)
        st.stop()
    
    if df is None:
        st.error("❌ Failed to fetch data")
        st.stop()
    
    # Calculate flow metrics for live data
    try:
        flow_metrics = calculate_dual_gex_dex_flow(df, futures_ltp)
    except Exception as e:
        flow_metrics = None
    
    # Auto-capture snapshot
    if st.session_state.auto_capture or st.session_state.force_capture:
        if capture_snapshot(df, futures_ltp, fetch_method, atm_info, flow_metrics):
            st.toast("📸 Snapshot captured!", icon="✅")
        st.session_state.force_capture = False
    
    st.success(f"🔴 **LIVE MODE** - Real-time data via {fetch_method}")

# ============================================================================
# KEY METRICS
# ============================================================================

st.subheader("📊 Key Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_gex = float(df['Net_GEX_B'].sum())
    st.metric(
        "Total Net GEX",
        f"{total_gex:.4f}B",
        delta="Bullish" if total_gex > 0 else "Volatile"
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
# FLOW METRICS
# ============================================================================

if flow_metrics:
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        gex_bias = flow_metrics['gex_near_bias']
        if "BULLISH" in gex_bias:
            st.markdown(f'<div class="success-box"><b>GEX:</b> {gex_bias}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="warning-box"><b>GEX:</b> {gex_bias}</div>', unsafe_allow_html=True)
    
    with col2:
        dex_bias = flow_metrics['dex_near_bias']
        st.info(f"**DEX Bias:** {dex_bias}")
    
    with col3:
        combined_bias = flow_metrics['combined_bias']
        st.info(f"**Combined:** {combined_bias}")
else:
    st.warning("Flow metrics unavailable")

# ============================================================================
# GAMMA FLIP ZONES
# ============================================================================

try:
    gamma_flip_zones = detect_gamma_flip_zones(df)
    if gamma_flip_zones:
        st.warning(f"⚡ **{len(gamma_flip_zones)} Gamma Flip Zone(s) Detected!**")
except:
    gamma_flip_zones = []

# ============================================================================
# CHARTS
# ============================================================================

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 GEX Profile", "📈 DEX Profile", "🎯 Hedging Pressure", "📋 Data Table", "💡 Strategies"])

# TAB 1: GEX Profile
with tab1:
    mode_text = f"[HISTORICAL - {hist_time.strftime('%I:%M %p')}]" if is_historical else "[LIVE]"
    st.subheader(f"NYZTrade - {symbol} Gamma Exposure Profile {mode_text}")
    
    fig = go.Figure()
    
    colors = ['green' if x > 0 else 'red' for x in df['Net_GEX_B']]
    
    fig.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Net_GEX_B'],
        orientation='h',
        marker_color=colors,
        name='Net GEX',
        hovertemplate='<b>Strike:</b> %{y}<br><b>Net GEX:</b> %{x:.4f}B<extra></extra>'
    ))
    
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
    
    if total_gex > 0.5:
        st.success("🟢 **Strong Positive GEX**: Sideways to bullish market expected")
    elif total_gex < -0.5:
        st.error("🔴 **Negative GEX**: High volatility expected")
    else:
        st.warning("⚖️ **Neutral GEX**: Mixed signals")

# TAB 2: DEX Profile
with tab2:
    mode_text = f"[HISTORICAL - {hist_time.strftime('%I:%M %p')}]" if is_historical else "[LIVE]"
    st.subheader(f"NYZTrade - {symbol} Delta Exposure Profile {mode_text}")
    
    fig2 = go.Figure()
    
    dex_colors = ['green' if x > 0 else 'red' for x in df['Net_DEX_B']]
    
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
    mode_text = f"[HISTORICAL - {hist_time.strftime('%I:%M %p')}]" if is_historical else "[LIVE]"
    st.subheader(f"NYZTrade - {symbol} Hedging Pressure Index {mode_text}")
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Hedging_Pressure'],
        orientation='h',
        marker=dict(
            color=df['Hedging_Pressure'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Pressure", x=1.15)
        ),
        name='Hedging Pressure',
        hovertemplate='<b>Strike:</b> %{y}<br><b>Pressure:</b> %{x:.2f}%<extra></extra>'
    ))
    
    max_pressure = df['Hedging_Pressure'].abs().max()
    max_vol = df['Total_Volume'].max()
    
    if max_vol > 0:
        vol_scale = (max_pressure * 0.3) / max_vol
        scaled_volume = df['Total_Volume'] * vol_scale
        
        fig3.add_trace(go.Scatter(
            y=df['Strike'],
            x=scaled_volume,
            mode='lines+markers',
            line=dict(color='cyan', width=2),
            marker=dict(size=4),
            name='Volume',
            hovertemplate='<b>Strike:</b> %{y}<br><b>Volume:</b> %{customdata:,.0f}<extra></extra>',
            customdata=df['Total_Volume']
        ))
    
    fig3.add_hline(
        y=futures_ltp,
        line_dash="dash",
        line_color="blue",
        line_width=3
    )
    
    fig3.update_layout(
        height=600,
        xaxis_title="Hedging Pressure (%)",
        yaxis_title="Strike Price",
        template='plotly_white'
    )
    
    st.plotly_chart(fig3, use_container_width=True)
    
    st.info("💡 **Hedging Pressure**: +100% = Max support | -100% = High volatility zone")

# TAB 4: Data Table
with tab4:
    st.subheader("Strike-wise Analysis")
    
    if is_historical:
        st.caption(f"📜 Historical data from {hist_time.strftime('%I:%M:%S %p IST')}")
    
    display_cols = ['Strike', 'Call_OI', 'Put_OI', 'Net_GEX_B', 'Net_DEX_B', 'Hedging_Pressure', 'Total_Volume']
    display_df = df[display_cols].copy()
    
    for col in ['Call_OI', 'Put_OI', 'Total_Volume']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{int(x):,}")
    
    if 'Hedging_Pressure' in display_df.columns:
        display_df['Hedging_Pressure'] = display_df['Hedging_Pressure'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    csv = df.to_csv(index=False)
    timestamp = hist_time.strftime('%Y%m%d_%H%M') if is_historical else get_ist_time().strftime('%Y%m%d_%H%M')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"NYZTrade_{symbol}_{timestamp}.csv",
        mime="text/csv",
        use_container_width=True
    )

# TAB 5: Strategies
with tab5:
    st.subheader("💡 Trading Strategies")
    
    if is_historical:
        st.info(f"📜 Strategies based on historical data from {hist_time.strftime('%I:%M %p IST')}")
    
    if flow_metrics and atm_info:
        gex_bias_val = flow_metrics['gex_near_total']
        dex_bias_val = flow_metrics['dex_near_total']
        
        st.markdown("### 📊 Current Market Setup")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("GEX Flow", f"{gex_bias_val:.2f}")
            st.metric("DEX Flow", f"{dex_bias_val:.2f}")
        with col2:
            st.metric("ATM Strike", f"{atm_info['atm_strike']}")
            st.metric("Straddle Premium", f"₹{atm_info['atm_straddle_premium']:.2f}")
        
        st.markdown("---")
        
        # Strong Positive GEX
        if gex_bias_val > 50:
            st.success("### 🟢 Strong Positive GEX - Sideways/Bullish")
            
            st.markdown("#### Strategy 1: Iron Condor")
            st.code(f"""
Sell {symbol} {int(futures_ltp)} CE
Buy  {symbol} {int(futures_ltp + 200)} CE
Sell {symbol} {int(futures_ltp)} PE
Buy  {symbol} {int(futures_ltp - 200)} PE

Max Profit: Premium collected
Risk: MODERATE
Best: Price stays {int(futures_ltp - 100)} to {int(futures_ltp + 100)}
            """)
            
            st.markdown("#### Strategy 2: Short Straddle")
            st.code(f"""
Sell {symbol} {atm_info['atm_strike']} CE + PE

Premium: ₹{atm_info['atm_straddle_premium']:.2f}
Risk: HIGH - Use stops
Exit if price moves ₹{atm_info['atm_straddle_premium']*0.5:.2f}
            """)
        
        # Negative GEX
        elif gex_bias_val < -50:
            st.error("### 🔴 Negative GEX - High Volatility")
            
            st.markdown("#### Strategy: Long Straddle")
            st.code(f"""
Buy {symbol} {atm_info['atm_strike']} CE + PE

Cost: ₹{atm_info['atm_straddle_premium']:.2f}
Upper BE: {atm_info['atm_strike'] + atm_info['atm_straddle_premium']:.0f}
Lower BE: {atm_info['atm_strike'] - atm_info['atm_straddle_premium']:.0f}
Risk: HIGH - Needs big move
            """)
        
        # Neutral
        else:
            st.warning("### ⚖️ Neutral/Mixed Signals")
            
            if dex_bias_val > 20:
                st.markdown("#### Bull Call Spread")
                st.code(f"""
Buy  {symbol} {int(futures_ltp)} CE
Sell {symbol} {int(futures_ltp + 100)} CE
Risk: MODERATE
                """)
            elif dex_bias_val < -20:
                st.markdown("#### Bear Put Spread")
                st.code(f"""
Buy  {symbol} {int(futures_ltp)} PE
Sell {symbol} {int(futures_ltp - 100)} PE
Risk: MODERATE
                """)
            else:
                st.info("⏸️ **Wait for Clarity** - Mixed signals, stay cautious")
        
        st.markdown("---")
        st.markdown("### ⚠️ Risk Rules")
        st.markdown("""
1. Max 2% capital per trade
2. Always use stops
3. Monitor theta decay
4. Take profit at 50-70% max
5. Avoid tight stops near gamma flip zones
        """)
        
        if user_tier != "premium":
            st.info("🔒 Premium: Backtested parameters coming soon")
    
    else:
        st.warning("Metrics unavailable")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

ist_time = get_ist_time()

with col1:
    st.info(f"⏰ {ist_time.strftime('%H:%M:%S')} IST")

with col2:
    st.info(f"📅 {ist_time.strftime('%d %b %Y')}")

with col3:
    if is_historical:
        st.warning(f"📜 Historical: {hist_time.strftime('%I:%M %p')}")
    else:
        st.success(f"🔴 Live: {symbol}")

with col4:
    if gamma_flip_zones:
        st.warning(f"⚡ {len(gamma_flip_zones)} Flip(s)")
    else:
        st.success("✅ No Flips")

st.markdown(f"**💡 NYZTrade YouTube | Data: {fetch_method} | Snapshots: {len(st.session_state.snapshot_times)}**")

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









GEX CALC 

"""
================================================================================
NYZTrade - Enhanced GEX + DEX Calculator
================================================================================
Complete calculator with:
- Proper Groww.in futures price fetching
- NSE Option Chain data
- Black-Scholes Greeks calculation
- GEX/DEX computation
- Flow metrics analysis
- Gamma flip detection

Author: NYZTrade
================================================================================
"""

import requests
import pandas as pd
import numpy as np
import re
import json
from datetime import datetime, timedelta
from scipy.stats import norm
import warnings
import time

warnings.filterwarnings('ignore')


# ============================================================================
# BLACK-SCHOLES CALCULATOR
# ============================================================================

class BlackScholesCalculator:
    """Calculate option Greeks using Black-Scholes model"""
    
    @staticmethod
    def calculate_d1(S, K, T, r, sigma):
        """Calculate d1 parameter"""
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0
        try:
            d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            return d1
        except:
            return 0

    @staticmethod
    def calculate_d2(S, K, T, r, sigma):
        """Calculate d2 parameter"""
        if T <= 0 or sigma <= 0:
            return 0
        try:
            d1 = BlackScholesCalculator.calculate_d1(S, K, T, r, sigma)
            d2 = d1 - sigma * np.sqrt(T)
            return d2
        except:
            return 0

    @staticmethod
    def calculate_gamma(S, K, T, r, sigma):
        """Calculate option gamma"""
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0
        try:
            d1 = BlackScholesCalculator.calculate_d1(S, K, T, r, sigma)
            n_prime_d1 = norm.pdf(d1)
            gamma = n_prime_d1 / (S * sigma * np.sqrt(T))
            return gamma
        except:
            return 0

    @staticmethod
    def calculate_call_delta(S, K, T, r, sigma):
        """Calculate call option delta"""
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0
        try:
            d1 = BlackScholesCalculator.calculate_d1(S, K, T, r, sigma)
            return norm.cdf(d1)
        except:
            return 0

    @staticmethod
    def calculate_put_delta(S, K, T, r, sigma):
        """Calculate put option delta"""
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0
        try:
            d1 = BlackScholesCalculator.calculate_d1(S, K, T, r, sigma)
            return norm.cdf(d1) - 1
        except:
            return 0

    @staticmethod
    def calculate_vega(S, K, T, r, sigma):
        """Calculate option vega"""
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0
        try:
            d1 = BlackScholesCalculator.calculate_d1(S, K, T, r, sigma)
            vega = S * norm.pdf(d1) * np.sqrt(T) / 100
            return vega
        except:
            return 0


# ============================================================================
# GROWW FUTURES FETCHER
# ============================================================================

class GrowwFuturesFetcher:
    """Fetch futures price from Groww.in"""
    
    def __init__(self):
        self.base_url = "https://groww.in"
        self.api_base = "https://groww.in/v1/api/stocks_fo_data/v1"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://groww.in',
            'Referer': 'https://groww.in/derivatives',
        }
        
        # Symbol mapping for Groww
        self.symbol_map = {
            'NIFTY': {'groww': 'NIFTY', 'display': 'NIFTY 50'},
            'BANKNIFTY': {'groww': 'BANKNIFTY', 'display': 'BANK NIFTY'},
            'FINNIFTY': {'groww': 'FINNIFTY', 'display': 'FIN NIFTY'},
            'MIDCPNIFTY': {'groww': 'MIDCPNIFTY', 'display': 'MIDCAP NIFTY'}
        }
    
    def get_futures_price(self, symbol, expiry_date=None):
        """
        Fetch futures price from Groww.in
        
        Args:
            symbol: Index symbol (NIFTY, BANKNIFTY, etc.)
            expiry_date: Expiry date string (DD-MMM-YYYY format)
        
        Returns:
            tuple: (futures_price, fetch_method) or (None, error_message)
        """
        
        groww_symbol = self.symbol_map.get(symbol, {}).get('groww', symbol)
        
        # Method 1: Try Groww Derivatives API
        price = self._fetch_from_derivatives_api(groww_symbol, expiry_date)
        if price:
            return price, "Groww API"
        
        # Method 2: Try Groww Futures page scraping
        price = self._fetch_from_futures_page(groww_symbol)
        if price:
            return price, "Groww Page"
        
        # Method 3: Try alternate Groww endpoint
        price = self._fetch_from_contract_api(groww_symbol, expiry_date)
        if price:
            return price, "Groww Contract"
        
        return None, "Groww fetch failed"
    
    def _fetch_from_derivatives_api(self, symbol, expiry_date=None):
        """Fetch from Groww derivatives API"""
        try:
            # Get futures chain
            url = f"{self.api_base}/derivatives/futures/contracts/{symbol}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Find current month futures
                if isinstance(data, list) and len(data) > 0:
                    # Get first (current) contract
                    contract = data[0]
                    if 'ltp' in contract:
                        return float(contract['ltp'])
                    if 'lastPrice' in contract:
                        return float(contract['lastPrice'])
                
                # If dict response
                if isinstance(data, dict):
                    if 'ltp' in data:
                        return float(data['ltp'])
                    if 'lastPrice' in data:
                        return float(data['lastPrice'])
                    
                    # Check for contracts array
                    contracts = data.get('contracts', data.get('futuresContracts', []))
                    if contracts and len(contracts) > 0:
                        # Find matching expiry or use first
                        for contract in contracts:
                            if expiry_date and contract.get('expiryDate') == expiry_date:
                                return float(contract.get('ltp', contract.get('lastPrice', 0)))
                        
                        # Use first contract
                        first = contracts[0]
                        return float(first.get('ltp', first.get('lastPrice', 0)))
            
            return None
        except Exception as e:
            return None
    
    def _fetch_from_futures_page(self, symbol):
        """Scrape futures price from Groww futures page"""
        try:
            url = f"{self.base_url}/futures/{symbol.lower()}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                # Try to extract price from page content
                patterns = [
                    r'"ltp"\s*:\s*([0-9]+\.?[0-9]*)',
                    r'"lastPrice"\s*:\s*([0-9]+\.?[0-9]*)',
                    r'"close"\s*:\s*([0-9]+\.?[0-9]*)',
                    r'"currentPrice"\s*:\s*([0-9]+\.?[0-9]*)',
                    r'data-ltp="([0-9]+\.?[0-9]*)"',
                    r'price.*?([0-9]{4,6}\.[0-9]{1,2})',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        for match in matches:
                            price = float(match)
                            # Validate price range
                            if self._validate_price(symbol, price):
                                return price
            
            return None
        except Exception as e:
            return None
    
    def _fetch_from_contract_api(self, symbol, expiry_date=None):
        """Fetch from Groww contract-specific API"""
        try:
            # Try getting the current month expiry contract
            url = f"{self.api_base}/contract/stock/{symbol}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'ltp' in data:
                    return float(data['ltp'])
                
                # Try futures specific endpoint
                futures_data = data.get('futures', {})
                if futures_data:
                    contracts = futures_data.get('contracts', [])
                    if contracts:
                        return float(contracts[0].get('ltp', 0))
            
            return None
        except Exception as e:
            return None
    
    def _validate_price(self, symbol, price):
        """Validate if price is within expected range"""
        ranges = {
            'NIFTY': (20000, 30000),
            'BANKNIFTY': (45000, 60000),
            'FINNIFTY': (20000, 28000),
            'MIDCPNIFTY': (10000, 16000)
        }
        min_p, max_p = ranges.get(symbol.upper(), (5000, 100000))
        return min_p < price < max_p


# ============================================================================
# NSE DATA FETCHER
# ============================================================================

class NSEDataFetcher:
    """Fetch option chain data from NSE India"""
    
    def __init__(self):
        self.base_url = "https://www.nseindia.com"
        self.option_chain_url = "https://www.nseindia.com/api/option-chain-indices"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.cookies_set = False

    def initialize_session(self):
        """Initialize session with NSE website"""
        try:
            response = self.session.get(self.base_url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                self.session.headers.update({
                    'Accept': 'application/json, text/plain, */*',
                    'Referer': 'https://www.nseindia.com/option-chain',
                    'X-Requested-With': 'XMLHttpRequest',
                })
                self.cookies_set = True
                time.sleep(0.5)
                return True, "Session initialized"
            else:
                return False, f"Status {response.status_code}"
                
        except Exception as e:
            return False, str(e)

    def fetch_option_chain(self, symbol="NIFTY"):
        """Fetch option chain data from NSE"""
        if not self.cookies_set:
            success, msg = self.initialize_session()
            if not success:
                return None, msg
        
        try:
            url = f"{self.option_chain_url}?symbol={symbol}"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 401:
                self.cookies_set = False
                success, msg = self.initialize_session()
                if success:
                    response = self.session.get(url, timeout=15)
                else:
                    return None, msg
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'records' in data:
                        return data, None
                    else:
                        return None, "Invalid response format"
                except json.JSONDecodeError:
                    return None, "JSON decode error"
            else:
                return None, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            return None, "Timeout"
        except Exception as e:
            return None, str(e)

    def get_contract_specs(self, symbol):
        """Get contract specifications"""
        specs = {
            'NIFTY': {'lot_size': 25, 'strike_interval': 50},
            'BANKNIFTY': {'lot_size': 15, 'strike_interval': 100},
            'FINNIFTY': {'lot_size': 40, 'strike_interval': 50},
            'MIDCPNIFTY': {'lot_size': 75, 'strike_interval': 25}
        }
        return specs.get(symbol, specs['NIFTY'])


# ============================================================================
# ENHANCED GEX DEX CALCULATOR
# ============================================================================

class EnhancedGEXDEXCalculator:
    """
    Enhanced GEX + DEX Calculator with:
    - Groww.in futures fetching
    - NSE option chain data
    - Multiple expiry support
    - Proper Greeks calculation
    """
    
    def __init__(self):
        self.nse_fetcher = NSEDataFetcher()
        self.groww_fetcher = GrowwFuturesFetcher()
        self.bs_calc = BlackScholesCalculator()
        self.risk_free_rate = 0.07
        self.use_demo_data = False

    def calculate_time_to_expiry(self, expiry_str):
        """Calculate time to expiry in years"""
        try:
            expiry = datetime.strptime(expiry_str, "%d-%b-%Y")
            days = (expiry - datetime.now()).days
            T = max(days / 365, 1/365)
            return T, max(days, 1)
        except:
            return 7/365, 7

    def fetch_and_calculate_gex_dex(self, symbol="NIFTY", strikes_range=12, expiry_index=0):
        """
        Main function to fetch data and calculate GEX/DEX
        
        Args:
            symbol: Index symbol
            strikes_range: Number of strikes on each side of ATM
            expiry_index: 0=Current Weekly, 1=Next Weekly, 2=Monthly
        
        Returns:
            tuple: (df, futures_ltp, fetch_method, atm_info)
        """
        
        # Initialize NSE session
        success, msg = self.nse_fetcher.initialize_session()
        if not success:
            self.use_demo_data = True
            return self._generate_demo_data(symbol, strikes_range)
        
        # Fetch option chain
        data, error = self.nse_fetcher.fetch_option_chain(symbol)
        
        if error or not data:
            self.use_demo_data = True
            return self._generate_demo_data(symbol, strikes_range)
        
        try:
            records = data['records']
            spot_price = records.get('underlyingValue', 0)
            timestamp = records.get('timestamp', datetime.now().strftime('%d-%b-%Y %H:%M:%S'))
            expiry_dates = records.get('expiryDates', [])
            
            if not expiry_dates or spot_price == 0:
                return self._generate_demo_data(symbol, strikes_range)
            
            # Select expiry based on index
            # 0 = Current Weekly, 1 = Next Weekly, 2 = Monthly (usually last Thursday)
            selected_expiry = expiry_dates[min(expiry_index, len(expiry_dates) - 1)]
            
            T, days_to_expiry = self.calculate_time_to_expiry(selected_expiry)
            
            # Get futures price from Groww.in
            futures_ltp, fetch_method = self.groww_fetcher.get_futures_price(symbol, selected_expiry)
            
            # Fallback methods if Groww fails
            if futures_ltp is None:
                # Try Put-Call Parity
                futures_ltp = self._calculate_futures_from_pcp(records, spot_price, selected_expiry)
                if futures_ltp:
                    fetch_method = "Put-Call Parity"
                else:
                    # Cost of Carry model
                    futures_ltp = spot_price * np.exp(self.risk_free_rate * days_to_expiry / 365)
                    fetch_method = "Cost of Carry"
            
            # Get contract specs
            specs = self.nse_fetcher.get_contract_specs(symbol)
            lot_size = specs['lot_size']
            strike_interval = specs['strike_interval']
            
            # Process option chain data
            all_strikes = []
            processed = set()
            atm_strike = None
            min_diff = float('inf')
            atm_call_premium = 0
            atm_put_premium = 0
            
            for item in records.get('data', []):
                if item.get('expiryDate') != selected_expiry:
                    continue
                
                strike = item.get('strikePrice', 0)
                if strike == 0 or strike in processed:
                    continue
                
                processed.add(strike)
                
                # Filter by strikes range
                distance = abs(strike - futures_ltp) / strike_interval
                if distance > strikes_range:
                    continue
                
                ce = item.get('CE', {})
                pe = item.get('PE', {})
                
                # Extract data
                call_oi = ce.get('openInterest', 0) or 0
                put_oi = pe.get('openInterest', 0) or 0
                call_oi_change = ce.get('changeinOpenInterest', 0) or 0
                put_oi_change = pe.get('changeinOpenInterest', 0) or 0
                call_volume = ce.get('totalTradedVolume', 0) or 0
                put_volume = pe.get('totalTradedVolume', 0) or 0
                call_iv = ce.get('impliedVolatility', 0) or 15
                put_iv = pe.get('impliedVolatility', 0) or 15
                call_ltp = ce.get('lastPrice', 0) or 0
                put_ltp = pe.get('lastPrice', 0) or 0
                
                # Track ATM strike
                diff = abs(strike - futures_ltp)
                if diff < min_diff:
                    min_diff = diff
                    atm_strike = strike
                    atm_call_premium = call_ltp
                    atm_put_premium = put_ltp
                
                # Calculate Greeks
                call_iv_dec = max(call_iv / 100, 0.05)
                put_iv_dec = max(put_iv / 100, 0.05)
                
                call_gamma = self.bs_calc.calculate_gamma(futures_ltp, strike, T, self.risk_free_rate, call_iv_dec)
                put_gamma = self.bs_calc.calculate_gamma(futures_ltp, strike, T, self.risk_free_rate, put_iv_dec)
                call_delta = self.bs_calc.calculate_call_delta(futures_ltp, strike, T, self.risk_free_rate, call_iv_dec)
                put_delta = self.bs_calc.calculate_put_delta(futures_ltp, strike, T, self.risk_free_rate, put_iv_dec)
                
                # Calculate GEX (in Billions)
                gex_mult = futures_ltp * futures_ltp * lot_size / 1_000_000_000
                call_gex = call_oi * call_gamma * gex_mult
                put_gex = -put_oi * put_gamma * gex_mult
                
                # Calculate DEX (in Billions)
                dex_mult = futures_ltp * lot_size / 1_000_000_000
                call_dex = call_oi * call_delta * dex_mult
                put_dex = put_oi * put_delta * dex_mult
                
                # Flow calculations
                call_flow_gex = call_oi_change * call_gamma * gex_mult
                put_flow_gex = -put_oi_change * put_gamma * gex_mult
                call_flow_dex = call_oi_change * call_delta * dex_mult
                put_flow_dex = put_oi_change * put_delta * dex_mult
                
                all_strikes.append({
                    'Strike': strike,
                    'Call_OI': call_oi,
                    'Put_OI': put_oi,
                    'Call_OI_Change': call_oi_change,
                    'Put_OI_Change': put_oi_change,
                    'Call_Volume': call_volume,
                    'Put_Volume': put_volume,
                    'Call_IV': call_iv,
                    'Put_IV': put_iv,
                    'Call_LTP': call_ltp,
                    'Put_LTP': put_ltp,
                    'Call_Gamma': call_gamma,
                    'Put_Gamma': put_gamma,
                    'Call_Delta': call_delta,
                    'Put_Delta': put_delta,
                    'Call_GEX': call_gex,
                    'Put_GEX': put_gex,
                    'Net_GEX': call_gex + put_gex,
                    'Call_DEX': call_dex,
                    'Put_DEX': put_dex,
                    'Net_DEX': call_dex + put_dex,
                    'Call_Flow_GEX': call_flow_gex,
                    'Put_Flow_GEX': put_flow_gex,
                    'Net_Flow_GEX': call_flow_gex + put_flow_gex,
                    'Call_Flow_DEX': call_flow_dex,
                    'Put_Flow_DEX': put_flow_dex,
                    'Net_Flow_DEX': call_flow_dex + put_flow_dex
                })
            
            if not all_strikes:
                return self._generate_demo_data(symbol, strikes_range)
            
            # Create DataFrame
            df = pd.DataFrame(all_strikes).sort_values('Strike').reset_index(drop=True)
            
            # Add _B suffix columns
            for col in ['Call_GEX', 'Put_GEX', 'Net_GEX', 'Call_DEX', 'Put_DEX', 'Net_DEX',
                        'Call_Flow_GEX', 'Put_Flow_GEX', 'Net_Flow_GEX',
                        'Call_Flow_DEX', 'Put_Flow_DEX', 'Net_Flow_DEX']:
                df[f'{col}_B'] = df[col]
            
            df['Total_Volume'] = df['Call_Volume'] + df['Put_Volume']
            df['Total_OI'] = df['Call_OI'] + df['Put_OI']
            
            # Hedging Pressure
            max_gex = df['Net_GEX_B'].abs().max()
            df['Hedging_Pressure'] = (df['Net_GEX_B'] / max_gex * 100) if max_gex > 0 else 0
            
            # ATM info
            atm_info = {
                'atm_strike': atm_strike or df.iloc[len(df)//2]['Strike'],
                'atm_call_premium': atm_call_premium,
                'atm_put_premium': atm_put_premium,
                'atm_straddle_premium': atm_call_premium + atm_put_premium,
                'spot_price': spot_price,
                'expiry_date': selected_expiry,
                'days_to_expiry': days_to_expiry,
                'timestamp': timestamp,
                'expiry_index': expiry_index,
                'all_expiries': expiry_dates
            }
            
            return df, futures_ltp, fetch_method, atm_info
            
        except Exception as e:
            return self._generate_demo_data(symbol, strikes_range)

    def _calculate_futures_from_pcp(self, records, spot_price, expiry_date):
        """Calculate synthetic futures from Put-Call Parity"""
        try:
            atm_strike = None
            min_diff = float('inf')
            ce_data = None
            pe_data = None
            
            for item in records.get('data', []):
                if item.get('expiryDate') != expiry_date:
                    continue
                
                strike = item.get('strikePrice', 0)
                diff = abs(strike - spot_price)
                
                if diff < min_diff:
                    min_diff = diff
                    atm_strike = strike
                    ce_data = item.get('CE', {})
                    pe_data = item.get('PE', {})
            
            if atm_strike and ce_data and pe_data:
                call_price = ce_data.get('lastPrice', 0)
                put_price = pe_data.get('lastPrice', 0)
                
                if call_price > 0 and put_price > 0:
                    # F = K + (C - P) for near-term
                    futures = atm_strike + (call_price - put_price)
                    return futures
            
            return None
        except:
            return None

    def _generate_demo_data(self, symbol="NIFTY", strikes_range=12):
        """Generate demo data when live data unavailable"""
        np.random.seed(int(datetime.now().timestamp()) % 10000)
        
        spot_prices = {
            'NIFTY': 24250 + np.random.randn() * 50,
            'BANKNIFTY': 51850 + np.random.randn() * 100,
            'FINNIFTY': 23150 + np.random.randn() * 50,
            'MIDCPNIFTY': 12450 + np.random.randn() * 25
        }
        
        spot_price = spot_prices.get(symbol, 24250)
        specs = self.nse_fetcher.get_contract_specs(symbol)
        lot_size = specs['lot_size']
        strike_interval = specs['strike_interval']
        
        futures_ltp = spot_price * 1.0008
        atm_strike = round(spot_price / strike_interval) * strike_interval
        T = 7 / 365
        
        all_strikes = []
        
        for i in range(-strikes_range, strikes_range + 1):
            strike = atm_strike + (i * strike_interval)
            dist = abs(i)
            
            base_oi = 400000 + np.random.randint(-100000, 100000)
            if i < 0:
                call_oi = int(base_oi * (0.4 + 0.2 * np.random.random()) * max(0.2, 1 - dist * 0.08))
                put_oi = int(base_oi * (1.1 + 0.3 * np.random.random()) * max(0.3, 1 - dist * 0.05))
            else:
                call_oi = int(base_oi * (1.1 + 0.3 * np.random.random()) * max(0.3, 1 - dist * 0.05))
                put_oi = int(base_oi * (0.4 + 0.2 * np.random.random()) * max(0.2, 1 - dist * 0.08))
            
            call_oi_change = int((np.random.random() - 0.5) * call_oi * 0.15)
            put_oi_change = int((np.random.random() - 0.5) * put_oi * 0.15)
            call_volume = int(call_oi * (0.05 + 0.1 * np.random.random()))
            put_volume = int(put_oi * (0.05 + 0.1 * np.random.random()))
            
            base_iv = 13 + dist * 0.35 + np.random.random() * 1.5
            call_iv = base_iv + (0.8 if i > 0 else -0.3)
            put_iv = base_iv + (0.8 if i < 0 else -0.3)
            
            if strike < spot_price:
                call_ltp = max(5, spot_price - strike + np.random.random() * 20)
                put_ltp = max(1, np.random.random() * 30 * max(0.1, 1 - dist * 0.12))
            else:
                call_ltp = max(1, np.random.random() * 30 * max(0.1, 1 - dist * 0.12))
                put_ltp = max(5, strike - spot_price + np.random.random() * 20)
            
            call_iv_dec = call_iv / 100
            put_iv_dec = put_iv / 100
            
            call_gamma = self.bs_calc.calculate_gamma(futures_ltp, strike, T, self.risk_free_rate, call_iv_dec)
            put_gamma = self.bs_calc.calculate_gamma(futures_ltp, strike, T, self.risk_free_rate, put_iv_dec)
            call_delta = self.bs_calc.calculate_call_delta(futures_ltp, strike, T, self.risk_free_rate, call_iv_dec)
            put_delta = self.bs_calc.calculate_put_delta(futures_ltp, strike, T, self.risk_free_rate, put_iv_dec)
            
            gex_mult = futures_ltp * futures_ltp * lot_size / 1_000_000_000
            dex_mult = futures_ltp * lot_size / 1_000_000_000
            
            call_gex = call_oi * call_gamma * gex_mult
            put_gex = -put_oi * put_gamma * gex_mult
            call_dex = call_oi * call_delta * dex_mult
            put_dex = put_oi * put_delta * dex_mult
            
            call_flow_gex = call_oi_change * call_gamma * gex_mult
            put_flow_gex = -put_oi_change * put_gamma * gex_mult
            call_flow_dex = call_oi_change * call_delta * dex_mult
            put_flow_dex = put_oi_change * put_delta * dex_mult
            
            all_strikes.append({
                'Strike': strike,
                'Call_OI': call_oi, 'Put_OI': put_oi,
                'Call_OI_Change': call_oi_change, 'Put_OI_Change': put_oi_change,
                'Call_Volume': call_volume, 'Put_Volume': put_volume,
                'Call_IV': round(call_iv, 2), 'Put_IV': round(put_iv, 2),
                'Call_LTP': round(call_ltp, 2), 'Put_LTP': round(put_ltp, 2),
                'Call_Gamma': call_gamma, 'Put_Gamma': put_gamma,
                'Call_Delta': call_delta, 'Put_Delta': put_delta,
                'Call_GEX': call_gex, 'Put_GEX': put_gex, 'Net_GEX': call_gex + put_gex,
                'Call_DEX': call_dex, 'Put_DEX': put_dex, 'Net_DEX': call_dex + put_dex,
                'Call_Flow_GEX': call_flow_gex, 'Put_Flow_GEX': put_flow_gex, 'Net_Flow_GEX': call_flow_gex + put_flow_gex,
                'Call_Flow_DEX': call_flow_dex, 'Put_Flow_DEX': put_flow_dex, 'Net_Flow_DEX': call_flow_dex + put_flow_dex
            })
        
        df = pd.DataFrame(all_strikes).sort_values('Strike').reset_index(drop=True)
        
        for col in ['Call_GEX', 'Put_GEX', 'Net_GEX', 'Call_DEX', 'Put_DEX', 'Net_DEX',
                    'Call_Flow_GEX', 'Put_Flow_GEX', 'Net_Flow_GEX',
                    'Call_Flow_DEX', 'Put_Flow_DEX', 'Net_Flow_DEX']:
            df[f'{col}_B'] = df[col]
        
        df['Total_Volume'] = df['Call_Volume'] + df['Put_Volume']
        df['Total_OI'] = df['Call_OI'] + df['Put_OI']
        
        max_gex = df['Net_GEX_B'].abs().max()
        df['Hedging_Pressure'] = (df['Net_GEX_B'] / max_gex * 100) if max_gex > 0 else 0
        
        atm_row = df[df['Strike'] == atm_strike]
        if len(atm_row) > 0:
            atm_row = atm_row.iloc[0]
        else:
            atm_row = df.iloc[len(df)//2]
        
        # Next Thursday for expiry
        today = datetime.now()
        days_to_thu = (3 - today.weekday()) % 7
        if days_to_thu == 0:
            days_to_thu = 7
        next_thu = today + timedelta(days=days_to_thu)
        
        atm_info = {
            'atm_strike': atm_strike,
            'atm_call_premium': atm_row['Call_LTP'],
            'atm_put_premium': atm_row['Put_LTP'],
            'atm_straddle_premium': atm_row['Call_LTP'] + atm_row['Put_LTP'],
            'spot_price': round(spot_price, 2),
            'expiry_date': next_thu.strftime("%d-%b-%Y"),
            'days_to_expiry': days_to_thu,
            'timestamp': datetime.now().strftime('%d-%b-%Y %H:%M:%S'),
            'expiry_index': 0,
            'all_expiries': [next_thu.strftime("%d-%b-%Y")]
        }
        
        return df, round(futures_ltp, 2), "Demo Data", atm_info


# ============================================================================
# FLOW METRICS CALCULATION - UPDATED TERMINOLOGY
# ============================================================================

def calculate_dual_gex_dex_flow(df, futures_ltp):
    """
    Calculate comprehensive GEX and DEX flow metrics
    
    Updated Terminology:
    - Positive GEX = "Volatility Dampening" (MMs buy dips, sell rallies)
    - Negative GEX = "Volatility Amplifying" (MMs amplify moves)
    """
    df_unique = df.drop_duplicates(subset=['Strike']).sort_values('Strike').reset_index(drop=True)
    
    # GEX Flow - 5 positive + 5 negative closest to spot
    pos_gex = df_unique[df_unique['Net_GEX_B'] > 0].copy()
    if len(pos_gex) > 0:
        pos_gex['Dist'] = abs(pos_gex['Strike'] - futures_ltp)
        pos_gex = pos_gex.nsmallest(5, 'Dist')
    
    neg_gex = df_unique[df_unique['Net_GEX_B'] < 0].copy()
    if len(neg_gex) > 0:
        neg_gex['Dist'] = abs(neg_gex['Strike'] - futures_ltp)
        neg_gex = neg_gex.nsmallest(5, 'Dist')
    
    gex_near_pos = float(pos_gex['Net_GEX_B'].sum()) if len(pos_gex) > 0 else 0
    gex_near_neg = float(neg_gex['Net_GEX_B'].sum()) if len(neg_gex) > 0 else 0
    gex_near_total = gex_near_pos + gex_near_neg
    
    gex_total_pos = float(df_unique[df_unique['Net_GEX_B'] > 0]['Net_GEX_B'].sum())
    gex_total_neg = float(df_unique[df_unique['Net_GEX_B'] < 0]['Net_GEX_B'].sum())
    gex_total_all = gex_total_pos + gex_total_neg
    
    # DEX Flow
    above = df_unique[df_unique['Strike'] > futures_ltp].head(5)
    below = df_unique[df_unique['Strike'] < futures_ltp].tail(5)
    
    dex_near_pos = float(above['Net_DEX_B'].sum()) if len(above) > 0 else 0
    dex_near_neg = float(below['Net_DEX_B'].sum()) if len(below) > 0 else 0
    dex_near_total = dex_near_pos + dex_near_neg
    
    dex_total_pos = float(df_unique[df_unique['Net_DEX_B'] > 0]['Net_DEX_B'].sum())
    dex_total_neg = float(df_unique[df_unique['Net_DEX_B'] < 0]['Net_DEX_B'].sum())
    dex_total_all = dex_total_pos + dex_total_neg
    
    # Key Levels
    max_call_oi_strike = df_unique.loc[df_unique['Call_OI'].idxmax(), 'Strike'] if len(df_unique) > 0 else 0
    max_put_oi_strike = df_unique.loc[df_unique['Put_OI'].idxmax(), 'Strike'] if len(df_unique) > 0 else 0
    max_gex_strike = df_unique.loc[df_unique['Net_GEX_B'].abs().idxmax(), 'Strike'] if len(df_unique) > 0 else 0
    
    # PCR
    total_call_oi = df_unique['Call_OI'].sum()
    total_put_oi = df_unique['Put_OI'].sum()
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1
    
    # ==========================================
    # UPDATED BIAS TERMINOLOGY
    # ==========================================
    # Positive GEX = Volatility Dampening (market makers stabilize)
    # Negative GEX = Volatility Amplifying (market makers amplify moves)
    
    def get_gex_bias(val, threshold=50):
        """Get GEX bias with volatility terminology"""
        if val > threshold:
            return "🟢 STRONG VOL DAMPENING", "#00d4aa"
        elif val > 0:
            return "🟢 VOL DAMPENING", "#55efc4"
        elif val < -threshold:
            return "🔴 STRONG VOL AMPLIFYING", "#ff6b6b"
        elif val < 0:
            return "🔴 VOL AMPLIFYING", "#fab1a0"
        return "⚪ NEUTRAL", "#b2bec3"
    
    def get_dex_bias(val, threshold=50):
        """Get DEX bias - directional bias"""
        if val > threshold:
            return "🟢 STRONG BULLISH", "#00d4aa"
        elif val > 0:
            return "🟢 BULLISH", "#55efc4"
        elif val < -threshold:
            return "🔴 STRONG BEARISH", "#ff6b6b"
        elif val < 0:
            return "🔴 BEARISH", "#fab1a0"
        return "⚪ NEUTRAL", "#b2bec3"
    
    def get_combined_bias(gex_val, dex_val):
        """Get combined bias"""
        combined = (gex_val + dex_val) / 2
        
        # GEX dominant scenarios
        if gex_val > 50:
            if dex_val > 20:
                return "🟢 DAMPENING + BULLISH", "#00d4aa"
            elif dex_val < -20:
                return "🟡 DAMPENING + BEARISH", "#ffeaa7"
            else:
                return "🟢 VOL DAMPENING", "#55efc4"
        elif gex_val < -50:
            if dex_val > 20:
                return "⚡ AMPLIFYING + BULLISH", "#fd79a8"
            elif dex_val < -20:
                return "🔴 AMPLIFYING + BEARISH", "#ff6b6b"
            else:
                return "🔴 VOL AMPLIFYING", "#fab1a0"
        else:
            if dex_val > 30:
                return "🟢 BULLISH BIAS", "#55efc4"
            elif dex_val < -30:
                return "🔴 BEARISH BIAS", "#fab1a0"
            return "⚪ NEUTRAL", "#b2bec3"
    
    gex_bias, gex_color = get_gex_bias(gex_near_total)
    dex_bias, dex_color = get_dex_bias(dex_near_total)
    combined_bias, combined_color = get_combined_bias(gex_near_total, dex_near_total)
    
    return {
        'gex_near_positive': gex_near_pos,
        'gex_near_negative': gex_near_neg,
        'gex_near_total': gex_near_total,
        'gex_total_positive': gex_total_pos,
        'gex_total_negative': gex_total_neg,
        'gex_total_all': gex_total_all,
        'gex_near_bias': gex_bias,
        'gex_near_color': gex_color,
        'dex_near_positive': dex_near_pos,
        'dex_near_negative': dex_near_neg,
        'dex_near_total': dex_near_total,
        'dex_total_positive': dex_total_pos,
        'dex_total_negative': dex_total_neg,
        'dex_total_all': dex_total_all,
        'dex_near_bias': dex_bias,
        'dex_near_color': dex_color,
        'combined_signal': (gex_near_total + dex_near_total) / 2,
        'combined_bias': combined_bias,
        'combined_color': combined_color,
        'max_call_oi_strike': max_call_oi_strike,
        'max_put_oi_strike': max_put_oi_strike,
        'max_gex_strike': max_gex_strike,
        'pcr': pcr,
        'total_call_oi': total_call_oi,
        'total_put_oi': total_put_oi
    }


# ============================================================================
# GAMMA FLIP ZONE DETECTION
# ============================================================================

def detect_gamma_flip_zones(df):
    """
    Detect gamma flip zones where GEX changes sign
    These are areas of potential high volatility/instability
    """
    flip_zones = []
    
    df_sorted = df.sort_values('Strike').reset_index(drop=True)
    
    for i in range(len(df_sorted) - 1):
        current_gex = df_sorted.loc[i, 'Net_GEX_B']
        next_gex = df_sorted.loc[i + 1, 'Net_GEX_B']
        
        # Check for sign change
        if (current_gex > 0 and next_gex < 0) or (current_gex < 0 and next_gex > 0):
            lower_strike = df_sorted.loc[i, 'Strike']
            upper_strike = df_sorted.loc[i + 1, 'Strike']
            
            # Determine flip type
            if current_gex > 0:
                flip_type = "DAMPENING → AMPLIFYING"
            else:
                flip_type = "AMPLIFYING → DAMPENING"
            
            flip_zones.append({
                'lower_strike': lower_strike,
                'upper_strike': upper_strike,
                'flip_type': flip_type,
                'gex_below': current_gex,
                'gex_above': next_gex
            })
    
    return flip_zones


# ============================================================================
# MAIN - FOR TESTING
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("NYZTrade - Enhanced GEX + DEX Calculator")
    print("=" * 60)
    
    calculator = EnhancedGEXDEXCalculator()
    
    for symbol in ['NIFTY', 'BANKNIFTY']:
        print(f"\n📊 Fetching {symbol}...")
        
        df, futures_ltp, fetch_method, atm_info = calculator.fetch_and_calculate_gex_dex(
            symbol=symbol,
            strikes_range=10,
            expiry_index=0
        )
        
        if df is not None:
            print(f"✅ Futures: ₹{futures_ltp:,.2f} ({fetch_method})")
            print(f"   ATM Strike: {atm_info['atm_strike']}")
            print(f"   Straddle: ₹{atm_info['atm_straddle_premium']:.2f}")
            print(f"   Expiry: {atm_info['expiry_date']}")
            
            flow = calculate_dual_gex_dex_flow(df, futures_ltp)
            print(f"   GEX Bias: {flow['gex_near_bias']}")
            print(f"   DEX Bias: {flow['dex_near_bias']}")
            print(f"   Combined: {flow['combined_bias']}")
            
            flips = detect_gamma_flip_zones(df)
            if flips:
                print(f"   ⚡ {len(flips)} Gamma Flip Zone(s)")
        else:
            print(f"❌ Failed to fetch data")
    
    print("\n" + "=" * 60)
