from flask import Flask, render_template, jsonify
from flask_cors import CORS
import requests
import time
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# OpenSky Network API endpoints
OPENSKY_BASE_URL = "https://opensky-network.org/api"
OAUTH_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

# Your OpenSky OAuth2 credentials
CLIENT_ID = "ebastow-api-client"
CLIENT_SECRET = "mOwEN8G74OQOt4y68Cd3TaNeQHIE2doz"

AIRCRAFT_MAP = {
    "N31401": "a3581f",  
    "N773SP": "aa75ca",  
    "N41598": "a4ea67",  
    "N700ZG": "a956d4"   
}

# Global variables for token management
access_token = None
token_expiry = None

def get_oauth_token():
    """Get OAuth2 access token from OpenSky"""
    global access_token, token_expiry
    
    # Check if we have a valid token
    if access_token and token_expiry and time.time() < token_expiry:
        return access_token
    
    try:
        print("🔄 Requesting new OAuth2 token...")
        response = requests.post(
            OAUTH_TOKEN_URL,
            data={
                'grant_type': 'client_credentials',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access_token']
            # Token expires in 30 minutes, set expiry to 25 minutes for safety
            token_expiry = time.time() + (25 * 60)
            print("✅ OAuth2 token obtained successfully")
            return access_token
        else:
            print(f"❌ OAuth2 token request failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ OAuth2 token request failed: {e}")
        return None

def make_authenticated_request(url, params=None):
    """Make authenticated request to OpenSky API"""
    token = get_oauth_token()
    if not token:
        print("❌ No OAuth2 token available")
        return None
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print("🔄 Token expired, refreshing...")
            # Token might be expired, clear it and retry once
            global access_token
            access_token = None
            return make_authenticated_request(url, params)
        else:
            print(f"❌ Authenticated request failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Authenticated request failed: {e}")
        return None

def get_all_states():
    """Get current aircraft states from OpenSky (no auth needed)"""
    try:
        url = f"{OPENSKY_BASE_URL}/states/all"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"API request failed: {e}")
        return None

def get_aircraft_states(icao24_list):
    """Get current states for specific aircraft by ICAO24 codes"""
    try:
        url = f"{OPENSKY_BASE_URL}/states/all"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and 'states' in data:
                # Filter for our specific aircraft
                our_aircraft = []
                for state in data['states']:
                    if state and state[0].lower() in [icao.lower() for icao in icao24_list]:
                        our_aircraft.append(state)
                return our_aircraft
        return None
    except Exception as e:
        print(f"API request failed: {e}")
        return None

def get_flight_history(icao24, hours=48):
    """Get flight history with OAuth2 authentication"""
    try:
        end_time = int(time.time())
        start_time = end_time - (hours * 3600)
        
        url = f"{OPENSKY_BASE_URL}/flights/aircraft"
        params = {
            'icao24': icao24.lower(),
            'begin': start_time,
            'end': end_time
        }
        
        print(f"📡 Fetching flight history for {icao24}...")
        
        # Use authenticated request for flight history
        flights_data = make_authenticated_request(url, params)
        
        if flights_data is not None:
            print(f"✅ Found {len(flights_data)} flights for {icao24}")
            return flights_data
        else:
            print(f"❌ No flight history data for {icao24}")
            return []
            
    except Exception as e:
        print(f"❌ Flight history request failed for {icao24}: {e}")
        return []

def get_comprehensive_aircraft_data():
    """Get both current state and flight history for all tracked aircraft"""
    icao24_list = [icao.lower() for icao in AIRCRAFT_MAP.values()]
    current_states = get_aircraft_states(icao24_list)
    
    comprehensive_data = {}
    
    # Get current states
    if current_states:
        for state in current_states:
            icao24 = state[0].lower()
            comprehensive_data[icao24] = {
                'current_state': {
                    'icao24': state[0],
                    'callsign': state[1].strip() if state[1] else 'N/A',
                    'latitude': state[6],
                    'longitude': state[5],
                    'altitude': state[7],
                    'velocity': state[9],
                    'heading': state[10],
                    'vertical_rate': state[11],
                    'on_ground': state[8],
                    'last_contact': state[4],
                    'timestamp': int(time.time())
                },
                'flight_history': []
            }
    
    # Get flight history for all aircraft (even if not currently transmitting)
    for registration, icao24 in AIRCRAFT_MAP.items():
        icao24_lower = icao24.lower()
        
        # If we don't have current state for this aircraft, initialize it
        if icao24_lower not in comprehensive_data:
            comprehensive_data[icao24_lower] = {
                'current_state': None,
                'flight_history': []
            }
        
        # Get flight history with authentication
        flight_history = get_flight_history(icao24, hours=24)
        comprehensive_data[icao24_lower]['flight_history'] = flight_history
        
        # Add registration info
        comprehensive_data[icao24_lower]['registration'] = registration
        
        # Be respectful to the API
        time.sleep(1)
    
    return comprehensive_data

def test_comprehensive_tracking():
    """Test method that prints both current state and flight history"""
    print("=" * 80)
    print("🚀 FFC AIRCRAFT TRACKING - CURRENT STATE + 48H HISTORY")
    print("=" * 80)
    
    # Test OAuth2 authentication first
    print("\n1. TESTING OAUTH2 AUTHENTICATION...")
    token = get_oauth_token()
    if token:
        print("✅ OAuth2 authentication successful!")
    else:
        print("❌ OAuth2 authentication failed - flight history will not work")
        print("💡 Check your CLIENT_ID and CLIENT_SECRET")
        return
    
    # Test API connection
    print("\n2. TESTING OPENSKY API CONNECTION...")
    all_states = get_all_states()
    if all_states:
        total_aircraft = len(all_states['states']) if all_states and 'states' in all_states else 0
        print(f"✅ OpenSky API connected successfully!")
        print(f"📊 Total aircraft in system: {total_aircraft}")
    else:
        print("❌ Failed to connect to OpenSky API")
        return
    
    # Get comprehensive data
    print("\n3. FETCHING COMPREHENSIVE AIRCRAFT DATA...")
    comprehensive_data = get_comprehensive_aircraft_data()
    
    # Display results
    print("\n4. COMPREHENSIVE AIRCRAFT REPORT:")
    print("=" * 80)
    
    for icao24, data in comprehensive_data.items():
        registration = data.get('registration', 'Unknown')
        current_state = data['current_state']
        flight_history = data['flight_history']
        
        print(f"\n🛩️  AIRCRAFT: {registration} ({icao24})")
        print("-" * 50)
        
        # Current State
        if current_state:
            status = "ON GROUND" if current_state['on_ground'] else "IN FLIGHT"
            print(f"📡 CURRENT STATUS: {status}")
            print(f"   Callsign: {current_state['callsign']}")
            if current_state['latitude'] and current_state['longitude']:
                print(f"   Position: {current_state['latitude']:.4f}, {current_state['longitude']:.4f}")
            if current_state['altitude']:
                print(f"   Altitude: {current_state['altitude']} ft")
            if current_state['velocity']:
                print(f"   Speed: {current_state['velocity']} kts")
            if current_state['heading']:
                print(f"   Heading: {current_state['heading']}°")
            print(f"   Last Contact: {datetime.fromtimestamp(current_state['last_contact']).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("📡 CURRENT STATUS: NOT TRANSMITTING")
        
        # Flight History
        print(f"\n📅 FLIGHT HISTORY (Last 48 hours): {len(flight_history)} flights")
        if flight_history:
            for i, flight in enumerate(flight_history[:5], 1):  # Show last 5 flights
                print(f"   Flight #{i}:")
                print(f"     Callsign: {flight.get('callsign', 'N/A').strip()}")
                
                first_seen = flight.get('firstSeen')
                last_seen = flight.get('lastSeen')
                
                if first_seen:
                    print(f"     Departure: {datetime.fromtimestamp(first_seen).strftime('%Y-%m-%d %H:%M')}")
                if last_seen:
                    print(f"     Arrival: {datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M')}")
                
                print(f"     From: {flight.get('estDepartureAirport', 'N/A')}")
                print(f"     To: {flight.get('estArrivalAirport', 'N/A')}")
                if first_seen and last_seen:
                    duration_min = (last_seen - first_seen) // 60
                    print(f"     Duration: {duration_min} min")
                
            if len(flight_history) > 5:
                print(f"     ... and {len(flight_history) - 5} more flights")
        else:
            print("     No flight history found in the last 48 hours")
        
        print("-" * 50)
    
    # Summary
    print("\n5. SUMMARY:")
    print("=" * 50)
    current_count = sum(1 for data in comprehensive_data.values() if data['current_state'])
    history_counts = {icao: len(data['flight_history']) for icao, data in comprehensive_data.items()}
    total_flights = sum(history_counts.values())
    
    print(f"📊 Aircraft currently transmitting: {current_count}/{len(AIRCRAFT_MAP)}")
    print(f"📈 Total flights in last 48 hours: {total_flights}")
    for icao24, count in history_counts.items():
        reg = comprehensive_data[icao24].get('registration', icao24)
        print(f"   {reg}: {count} flights")
    
    print("=" * 80)
    print("🎯 COMPREHENSIVE TEST COMPLETE")
    print("=" * 80)

# Flask routes for web interface
@app.route('/')
def index():
    return jsonify({"message": "FFC Aircraft Tracker API", "status": "running"})

@app.route('/api/live/all')
def get_all_live_data():
    """Get current live data for all tracked aircraft"""
    try:
        icao24_list = list(AIRCRAFT_MAP.values())
        states = get_aircraft_states(icao24_list)
        
        aircraft_data = []
        if states:
            for state in states:
                aircraft_data.append({
                    'icao24': state[0],
                    'callsign': state[1].strip() if state[1] else 'N/A',
                    'latitude': state[6],
                    'longitude': state[5],
                    'altitude': state[7],
                    'velocity': state[9],
                    'heading': state[10],
                    'vertical_rate': state[11],
                    'on_ground': state[8],
                    'last_contact': state[4]
                })
        
        return jsonify({
            'timestamp': int(time.time()),
            'aircraft_count': len(aircraft_data),
            'aircraft': aircraft_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/comprehensive/all')
def get_comprehensive_data():
    """Get both current state and flight history for all aircraft"""
    try:
        comprehensive_data = get_comprehensive_aircraft_data()
        return jsonify({
            'timestamp': int(time.time()),
            'data': comprehensive_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/<registration>')
def get_aircraft_history(registration):
    """Get flight history for a specific aircraft"""
    try:
        if registration not in AIRCRAFT_MAP:
            return jsonify({'error': 'Aircraft not in tracking list'}), 404
            
        icao24 = AIRCRAFT_MAP[registration]
        flight_history = get_flight_history(icao24, hours=48)
        
        return jsonify({
            'registration': registration,
            'icao24': icao24,
            'flight_history': flight_history,
            'flight_count': len(flight_history)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run the comprehensive test
    test_comprehensive_tracking()
    
    # Then start the Flask server
    print("\nStarting Flask server on http://localhost:5000")
    print("Available endpoints:")
    print("  /api/live/all - Current aircraft data only")
    print("  /api/comprehensive/all - Current + flight history")
    print("  /api/history/<registration> - Flight history for specific aircraft")
    app.run(debug=True, port=5000)