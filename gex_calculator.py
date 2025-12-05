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
