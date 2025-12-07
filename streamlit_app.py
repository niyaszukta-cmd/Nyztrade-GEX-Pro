import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
import hashlib

# Import our custom modules
from gex_calculator import EnhancedGEXDEXCalculator, BlackScholesCalculator
from auth import check_password, get_user_tier

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="NYZTrade - Advanced GEX Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# AUTHENTICATION
# ============================================================================

if not check_password():
    st.stop()

user_tier = get_user_tier()

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
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<p class="main-header">📊 NYZTrade - Advanced GEX + DEX Analysis</p>', unsafe_allow_html=True)
st.markdown("**Real-time Gamma & Delta Exposure Analysis for Indian Markets**")

# User tier badge
if user_tier == "premium":
    st.sidebar.success("👑 **Premium Member**")
elif user_tier == "basic":
    st.sidebar.info("🆓 **Free Member** - Upgrade for full features!")
else:
    st.sidebar.warning("👤 **Guest Access** - Limited features")

# ============================================================================
# SIDEBAR CONTROLS
# ============================================================================

st.sidebar.header("⚙️ Dashboard Settings")

symbol = st.sidebar.selectbox(
    "Select Index",
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"],
    index=0,
    help="Choose the index to analyze"
)

strikes_range = st.sidebar.slider(
    "Strikes Range",
    min_value=5,
    max_value=20,
    value=12,
    help="Number of strikes around spot price"
)

expiry_index = st.sidebar.selectbox(
    "Expiry Selection",
    [0, 1, 2],
    format_func=lambda x: ["Current Weekly", "Next Weekly", "Monthly"][x],
    index=0
)

# Chart selection (Premium feature)
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Chart Selection")

if user_tier == "premium":
    show_gex = st.sidebar.checkbox("GEX Profile", value=True)
    show_dex = st.sidebar.checkbox("DEX Profile", value=True)
    show_gamma_flip = st.sidebar.checkbox("Gamma Flip Zones", value=True)
    show_hedging = st.sidebar.checkbox("Hedging Pressure", value=True)
    show_straddle = st.sidebar.checkbox("ATM Straddle", value=True)
    show_flow = st.sidebar.checkbox("Flow Analysis", value=True)
else:
    st.sidebar.info("🔒 Unlock all charts with Premium")
    show_gex = True
    show_dex = True
    show_gamma_flip = False
    show_hedging = False
    show_straddle = False
    show_flow = False

# Auto-refresh (Premium feature)
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
else:
    st.sidebar.info("🔒 Auto-refresh available in Premium")
    auto_refresh = False
    refresh_interval = 60

# Manual refresh
if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ============================================================================
# DATA FETCHING WITH CACHING
# ============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def fetch_data(symbol, strikes_range, expiry_index):
    """Fetch and calculate GEX/DEX data with caching"""
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

@st.cache_data(ttl=60, show_spinner=False)
def calculate_flow_metrics(df, futures_ltp):
    """Calculate flow metrics with caching"""
    try:
        from gex_calculator import calculate_dual_gex_dex_flow
        flow_metrics = calculate_dual_gex_dex_flow(df, futures_ltp)
        return flow_metrics
    except Exception as e:
        st.error(f"Flow calculation error: {e}")
        return None

@st.cache_data(ttl=60, show_spinner=False)
def detect_gamma_flips(df):
    """Detect gamma flip zones with caching"""
    try:
        from gex_calculator import detect_gamma_flip_zones
        return detect_gamma_flip_zones(df)
    except Exception as e:
        return []

# ============================================================================
# MAIN ANALYSIS
# ============================================================================

# Progress bar
progress_bar = st.progress(0)
status_text = st.empty()

status_text.text("🔄 Fetching live data...")
progress_bar.progress(20)

# Fetch data
df, futures_ltp, fetch_method, atm_info, error = fetch_data(symbol, strikes_range, expiry_index)

if error:
    st.error(f"❌ Error: {error}")
    st.stop()

if df is None or futures_ltp is None:
    st.error("❌ Failed to fetch data. Please try again.")
    st.stop()

progress_bar.progress(50)
status_text.text("📊 Calculating metrics...")

# Calculate metrics
flow_metrics = calculate_flow_metrics(df, futures_ltp)
gamma_flip_zones = detect_gamma_flips(df) if show_gamma_flip else []

progress_bar.progress(80)
status_text.text("📈 Rendering charts...")

# ============================================================================
# KEY METRICS DISPLAY
# ============================================================================

st.markdown("---")
st.subheader("📊 Key Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_gex = float(df['Net_GEX_B'].sum())
    st.metric(
        "Total Net GEX",
        f"{total_gex:.4f}B",
        delta="Bullish" if total_gex > 0 else "Volatile",
        delta_color="normal" if total_gex > 0 else "inverse"
    )

with col2:
    call_gex = float(df['Call_GEX'].sum())
    st.metric(
        "Call GEX",
        f"{call_gex:.4f}B",
        delta=f"{(call_gex/abs(total_gex)*100):.1f}%" if total_gex != 0 else "0%"
    )

with col3:
    put_gex = float(df['Put_GEX'].sum())
    st.metric(
        "Put GEX",
        f"{put_gex:.4f}B",
        delta=f"{(put_gex/abs(total_gex)*100):.1f}%" if total_gex != 0 else "0%"
    )

with col4:
    st.metric(
        "Futures LTP",
        f"₹{futures_ltp:,.2f}",
        delta=fetch_method
    )

with col5:
    if atm_info:
        st.metric(
            "ATM Straddle",
            f"₹{atm_info['atm_straddle_premium']:.2f}",
            delta=f"Strike: {atm_info['atm_strike']}"
        )

# ============================================================================
# BIAS INTERPRETATION
# ============================================================================

if flow_metrics:
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        gex_bias = flow_metrics['gex_near_bias']
        if "BULLISH" in gex_bias or "Bullish" in gex_bias:
            st.markdown(f'<div class="success-box"><b>GEX Bias:</b> {gex_bias}</div>', unsafe_allow_html=True)
        elif "VOLATILITY" in gex_bias or "Volatility" in gex_bias:
            st.markdown(f'<div class="warning-box"><b>GEX Bias:</b> {gex_bias}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="info-box"><b>GEX Bias:</b> {gex_bias}</div>', unsafe_allow_html=True)
    
    with col2:
        dex_bias = flow_metrics['dex_near_bias']
        if "BULLISH" in dex_bias or "Bullish" in dex_bias:
            st.markdown(f'<div class="success-box"><b>DEX Bias:</b> {dex_bias}</div>', unsafe_allow_html=True)
        elif "BEARISH" in dex_bias or "Bearish" in dex_bias:
            st.markdown(f'<div class="warning-box"><b>DEX Bias:</b> {dex_bias}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="info-box"><b>DEX Bias:</b> {dex_bias}</div>', unsafe_allow_html=True)
    
    with col3:
        combined_bias = flow_metrics['combined_bias']
        st.markdown(f'<div class="info-box"><b>Combined:</b> {combined_bias}</div>', unsafe_allow_html=True)

# ============================================================================
# GAMMA FLIP ZONES ALERT
# ============================================================================

if gamma_flip_zones and show_gamma_flip:
    st.markdown("---")
    st.warning(f"⚡ **{len(gamma_flip_zones)} Gamma Flip Zone(s) Detected!** High volatility zones identified.")
    
    with st.expander("📍 View Gamma Flip Details"):
        for idx, zone in enumerate(gamma_flip_zones, 1):
            st.write(f"**Zone #{idx}**: {zone['lower_strike']:.0f} - {zone['upper_strike']:.0f} (Flip at ~{zone['flip_strike']:.2f})")

# ============================================================================
# CHARTS
# ============================================================================

progress_bar.progress(90)

st.markdown("---")

# Create tabs
tabs = []
tab_names = []

if show_gex:
    tab_names.append("📊 GEX Profile")
if show_dex:
    tab_names.append("📈 DEX Profile")
if show_flow:
    tab_names.append("🔄 Flow Analysis")
if show_hedging:
    tab_names.append("🎯 Hedging Pressure")
if show_straddle and atm_info:
    tab_names.append("💰 ATM Straddle")

tab_names.append("📋 Data Table")
tab_names.append("💡 Trading Strategies")

tabs = st.tabs(tab_names)
tab_idx = 0

# GEX Profile Chart
if show_gex:
    with tabs[tab_idx]:
        st.subheader(f"NYZTrade - {symbol} Gamma Exposure Profile")
        
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
        
        # Add gamma flip zones
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
                
                fig.add_annotation(
                    y=zone['flip_strike'],
                    x=0,
                    text="🔄 Γ-Flip",
                    showarrow=True,
                    arrowhead=2,
                    font=dict(size=10, color="orange")
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
        
        # Interpretation
        if total_gex > 0.5:
            st.success("🟢 **Strong Positive GEX**: Market expected to be sideways to bullish. Consider selling premium strategies (Iron Condor, Credit Spreads).")
        elif total_gex < -0.5:
            st.error("🔴 **Negative GEX**: High volatility expected. Consider buying volatility (Long Straddle, Long Options).")
        else:
            st.warning("⚖️ **Neutral GEX**: Mixed signals. Follow DEX bias for direction or wait for clearer setup.")
    
    tab_idx += 1

# DEX Profile Chart
if show_dex:
    with tabs[tab_idx]:
        st.subheader(f"NYZTrade - {symbol} Delta Exposure Profile")
        
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
            line_width=3,
            annotation_text=f"Futures: {futures_ltp:,.2f}"
        )
        
        fig2.update_layout(
            height=600,
            xaxis_title="Net DEX (Billions)",
            yaxis_title="Strike Price",
            template='plotly_white',
            hovermode='closest'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        total_dex = float(df['Net_DEX_B'].sum())
        if total_dex > 0.2:
            st.success("🟢 **Bullish DEX**: Market makers have bullish positioning. Upside bias expected.")
        elif total_dex < -0.2:
            st.error("🔴 **Bearish DEX**: Market makers have bearish positioning. Downside bias expected.")
        else:
            st.info("⚖️ **Neutral DEX**: No strong directional bias from delta exposure.")
    
    tab_idx += 1

# Flow Analysis Chart (Premium)
if show_flow:
    with tabs[tab_idx]:
        st.subheader(f"NYZTrade - {symbol} Flow Analysis")
        
        fig3 = make_subplots(
            rows=1, cols=2,
            subplot_titles=('GEX Flow (OI Changes)', 'DEX Flow')
        )
        
        # GEX Flow
        flow_colors = ['green' if x > 0 else 'red' for x in df['Net_Flow_GEX_B']]
        fig3.add_trace(
            go.Bar(y=df['Strike'], x=df['Net_Flow_GEX_B'], orientation='h',
                   marker_color=flow_colors, name='GEX Flow'),
            row=1, col=1
        )
        
        # DEX Flow
        dex_flow_colors = ['green' if x > 0 else 'red' for x in df['Net_Flow_DEX_B']]
        fig3.add_trace(
            go.Bar(y=df['Strike'], x=df['Net_Flow_DEX_B'], orientation='h',
                   marker_color=dex_flow_colors, name='DEX Flow'),
            row=1, col=2
        )
        
        fig3.add_hline(y=futures_ltp, line_dash="dash", line_color="blue", row=1, col=1)
        fig3.add_hline(y=futures_ltp, line_dash="dash", line_color="blue", row=1, col=2)
        
        fig3.update_layout(height=600, showlegend=False, template='plotly_white')
        
        st.plotly_chart(fig3, use_container_width=True)
    
    tab_idx += 1

# Hedging Pressure Chart (Premium)
if show_hedging:
    with tabs[tab_idx]:
        st.subheader(f"NYZTrade - {symbol} Hedging Pressure Index")
        
        fig4 = go.Figure()
        
        fig4.add_trace(go.Bar(
            y=df['Strike'],
            x=df['Hedging_Pressure'],
            orientation='h',
            marker=dict(
                color=df['Hedging_Pressure'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Pressure %")
            ),
            hovertemplate='<b>Strike:</b> %{y}<br><b>Pressure:</b> %{x:.2f}%<extra></extra>'
        ))
        
        fig4.add_hline(
            y=futures_ltp,
            line_dash="dash",
            line_color="blue",
            line_width=3
        )
        
        fig4.update_layout(
            height=600,
            xaxis_title="Hedging Pressure (%)",
            yaxis_title="Strike Price",
            template='plotly_white'
        )
        
        st.plotly_chart(fig4, use_container_width=True)
        
        st.info("💡 **Hedging Pressure**: Normalized measure of market maker hedging activity. Extreme values indicate strong support/resistance.")
    
    tab_idx += 1

# ATM Straddle Chart (Premium)
if show_straddle and atm_info:
    with tabs[tab_idx]:
        st.subheader(f"NYZTrade - {symbol} ATM Straddle Analysis")
        
        atm_strike = atm_info['atm_strike']
        atm_straddle_premium = atm_info['atm_straddle_premium']
        
        # Create payoff diagram
        strike_range = np.linspace(atm_strike * 0.90, atm_strike * 1.10, 100)
        call_payoff = np.maximum(strike_range - atm_strike, 0) - atm_info['atm_call_premium']
        put_payoff = np.maximum(atm_strike - strike_range, 0) - atm_info['atm_put_premium']
        straddle_payoff = call_payoff + put_payoff
        
        fig5 = go.Figure()
        
        fig5.add_trace(go.Scatter(
            x=strike_range, y=straddle_payoff,
            name='Straddle P&L', mode='lines',
            line=dict(color='purple', width=3)
        ))
        
        fig5.add_trace(go.Scatter(
            x=strike_range, y=call_payoff,
            name='Call P&L', mode='lines',
            line=dict(color='green', width=2, dash='dot')
        ))
        
        fig5.add_trace(go.Scatter(
            x=strike_range, y=put_payoff,
            name='Put P&L', mode='lines',
            line=dict(color='red', width=2, dash='dot')
        ))
        
        fig5.add_hline(y=0, line_dash="dash", line_color="gray")
        fig5.add_vline(x=atm_strike, line_dash="solid", line_color="blue",
                      annotation_text=f"ATM: {atm_strike}")
        fig5.add_vline(x=atm_strike + atm_straddle_premium, line_dash="dash",
                      line_color="orange", annotation_text="Upper BE")
        fig5.add_vline(x=atm_strike - atm_straddle_premium, line_dash="dash",
                      line_color="orange", annotation_text="Lower BE")
        fig5.add_vline(x=futures_ltp, line_dash="solid", line_color="red",
                      annotation_text=f"Current: {futures_ltp:.0f}")
        
        fig5.update_layout(
            height=600,
            xaxis_title="Underlying Price",
            yaxis_title="Profit/Loss (₹)",
            template='plotly_white'
        )
        
        st.plotly_chart(fig5, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Straddle Cost", f"₹{atm_straddle_premium:.2f}")
        with col2:
            st.metric("Upper Breakeven", f"{atm_strike + atm_straddle_premium:.0f}")
        with col3:
            st.metric("Lower Breakeven", f"{atm_strike - atm_straddle_premium:.0f}")
    
    tab_idx += 1

# Data Table
with tabs[tab_idx]:
    st.subheader("Strike-wise Complete Analysis")
    
    # Select columns to display
    display_cols = ['Strike', 'Call_OI', 'Put_OI', 'Call_Volume', 'Put_Volume',
                   'Call_GEX', 'Put_GEX', 'Net_GEX_B', 'Call_DEX', 'Put_DEX',
                   'Net_DEX_B', 'Hedging_Pressure']
    
    display_df = df[display_cols].copy()
    
    # Format numbers
    for col in ['Call_OI', 'Put_OI', 'Call_Volume', 'Put_Volume']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{int(x):,}")
    
    for col in ['Call_GEX', 'Put_GEX', 'Net_GEX_B', 'Call_DEX', 'Put_DEX', 'Net_DEX_B']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.4f}")
    
    if 'Hedging_Pressure' in display_df.columns:
        display_df['Hedging_Pressure'] = display_df['Hedging_Pressure'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # Download buttons
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Complete Data (CSV)",
            data=csv,
            file_name=f"NYZTrade_{symbol}_GEX_Analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        if user_tier == "premium":
            # Excel download for premium users
            st.info("📊 Excel export coming soon!")
        else:
            st.info("🔒 Excel export available in Premium")

tab_idx += 1

# Trading Strategies
with tabs[tab_idx]:
    st.subheader("💡 Recommended Trading Strategies")
    
    if flow_metrics:
        gex_bias = flow_metrics['gex_near_total']
        dex_bias = flow_metrics['dex_near_total']
        
        # Strategy recommendations based on bias
        if gex_bias > 50:
            st.success("### 🦅 Iron Condor Strategy")
            st.write("**Rationale**: Strong positive GEX indicates sideways market")
            st.code(f"""
Setup: Sell {symbol} {int(futures_ltp)} CE + Buy {int(futures_ltp+200)} CE
       Sell {symbol} {int(futures_ltp)} PE + Buy {int(futures_ltp-200)} PE
Max Profit: Net Premium Received
Max Loss: Strike Width - Premium
Risk: ⚠️ MODERATE
            """)
            
        elif gex_bias < -50:
            st.error("### 🎭 Long Straddle Strategy")
            st.write("**Rationale**: Negative GEX indicates high volatility expected")
            if atm_info:
                st.code(f"""
Setup: Buy {symbol} {atm_info['atm_strike']} CE + {atm_info['atm_strike']} PE
Cost: ₹{atm_info['atm_straddle_premium']:.2f}
Max Profit: Unlimited
Max Loss: ₹{atm_info['atm_straddle_premium']:.2f}
Risk: ⚠️ HIGH (Needs big move)
                """)
        else:
            if dex_bias > 20:
                st.info("### 📈 Bull Call Spread")
                st.write("**Rationale**: Neutral GEX with bullish DEX")
                st.code(f"""
Setup: Buy {symbol} {int(futures_ltp)} CE
       Sell {symbol} {int(futures_ltp+100)} CE
Risk: ✅ MODERATE
                """)
            elif dex_bias < -20:
                st.info("### 📉 Bear Put Spread")
                st.write("**Rationale**: Neutral GEX with bearish DEX")
                st.code(f"""
Setup: Buy {symbol} {int(futures_ltp)} PE
       Sell {symbol} {int(futures_ltp-100)} PE
Risk: ✅ MODERATE
                """)
            else:
                st.warning("### ⏸️ Wait for Clarity")
                st.write("**Current market structure shows mixed signals. Best to stay in cash or very small positions.**")
        
        # Risk Management
        st.markdown("---")
        st.subheader("⚠️ Risk Management Rules")
        st.markdown("""
        1. **Position Sizing**: Never risk more than 2% of capital per trade
        2. **Stop Loss**: Always use defined risk strategies or strict stop losses
        3. **Time Decay**: Monitor theta - don't hold options too close to expiry
        4. **Exit Rules**: Take profit at 50-70% of max profit for spreads
        5. **Gamma Flip Zones**: Avoid tight stops near these high-volatility areas
        """)
        
        if user_tier != "premium":
            st.info("🔒 Unlock detailed strategy parameters and backtesting with Premium!")

# Clear progress
progress_bar.progress(100)
status_text.text("✅ Dashboard loaded successfully!")
time.sleep(0.5)
progress_bar.empty()
status_text.empty()

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info(f"⏰ Updated: {datetime.now().strftime('%H:%M:%S')}")

with col2:
    st.info(f"📊 Symbol: {symbol}")

with col3:
    st.info(f"🔧 Source: {fetch_method}")

with col4:
    if gamma_flip_zones:
        st.warning(f"⚡ {len(gamma_flip_zones)} Flip Zone(s)")
    else:
        st.success("✅ No Flip Zones")

st.markdown("**💡 Subscribe to NYZTrade on YouTube for more trading analytics!**")

# ============================================================================
# AUTO-REFRESH
# ============================================================================

if auto_refresh and user_tier == "premium":
    time.sleep(refresh_interval)
    st.rerun()
