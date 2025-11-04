# app.py
# Flask backend for FFC Small Aircraft Tracker
# Uses fetch_data.py for OpenSky API requests

# HOW TO RUN IN PYTHIN VM: 
# cd /workspaces/tracking-ffc-airplanes
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt
# cd airplane-tracker 
# python app.py


from flask import Flask, render_template, jsonify  # Import Flask modules for server, templates, and JSON
from flask_cors import CORS                        # Lets the frontend fetch data
from fetch_data import (                           # Import functions and data from fetch_data.py
    AIRCRAFT_MAP,             # Dictionary of aircraft registrations to ICAO24 codes
    get_aircraft_states,      # Function to get current aircraft states
    get_comprehensive_aircraft_data,  # Function to get current + flight history
    get_flight_history,       # Function to get flight history for one aircraft
    test_comprehensive_tracking  # Function to run a full test of current + history data
)
import time  # To get timestamps


# Initialize Flask app

app = Flask(__name__)  # Create a Flask app instance (starts the web server) 
CORS(app)              # CORS so frontend JS can call API routes without issues

# Routes

@app.route("/")
def index():
    """
    Homepage route.
    RN returns a simple JSON message indicating the API is running.
    """
    return jsonify({'message': 'FFC Aircraft Tracker API', 'status': 'running'})
    # return render_template("index.html") -> comment this back in when html is done to replace previous line


@app.route("/api/live/all")
def get_all_live_data():
    """
    Calls a function to get current data for all tracked planes.
    Loops through the planes and picks out useful info: location, altitude, speed, callsign, etc
    Only includes aircraft in AIRCRAFT_MAP
    Returns this information in JSON format, so the frontend can display it on a map
    """
    try:
        icao24_list = list(AIRCRAFT_MAP.values())  # Get list of ICAO24 codes we are tracking
        states = get_aircraft_states(icao24_list) # Call fetch_data function to get current states
        
        aircraft_data = []  # Prepare a list to hold aircraft info
        if states:  # Check if any aircraft data was returned
            for state in states:
                # Create a dictionary for each aircraft with relevant info
                aircraft_data.append({
                    'icao24': state[0],  # ICAO24 identifier
                    'callsign': state[1].strip() if state[1] else 'N/A',  # Flight callsign
                    'latitude': state[6],  # Latitude
                    'longitude': state[5],  # Longitude
                    'altitude': state[7],  # Altitude in feet
                    'velocity': state[9],  # Speed in knots
                    'heading': state[10],  # Heading in degrees
                    'vertical_rate': state[11],  # Climb/descent rate
                    'on_ground': state[8],  # Boolean if on ground
                    'last_contact': state[4]  # Timestamp of last contact
                })
        
        # Return JSON with timestamp, aircraft count, and aircraft data
        return jsonify({
            'timestamp': int(time.time()),  # Current server time
            'aircraft_count': len(aircraft_data),  # Number of tracked aircraft currently transmitting
            'aircraft': aircraft_data
        })
        
    except Exception as e:
        # If something goes wrong, return an error with HTTP status 500
        return jsonify({'error': str(e)}), 500


@app.route("/api/comprehensive/all")
def get_comprehensive_data():
    """
    Return both current state and flight history for all tracked aircraft.
    Uses OAuth2 token authentication for flight history.
    Returns everything in JSON
    """
    try:
        comprehensive_data = get_comprehensive_aircraft_data()  # Get data for all aircraft
        # Return JSON with timestamp and full data
        return jsonify({
            'timestamp': int(time.time()),
            'data': comprehensive_data
        })
    except Exception as e:
        # Return error if something fails
        return jsonify({'error': str(e)}), 500


@app.route("/api/history/<registration>")
def get_aircraft_history(registration):
    """
    Return flight history for a single aircraft by registration.
    Example: /api/history/N31401
    """
    try:
        if registration not in AIRCRAFT_MAP:  # Check if the aircraft is in our tracking list
            return jsonify({'error': 'Aircraft not in tracking list'}), 404
        
        icao24 = AIRCRAFT_MAP[registration]  # Get ICAO24 code for this registration
        flight_history = get_flight_history(icao24, hours=48)  # Get last 48 hours of flights
        
        # Return JSON with registration, ICAO24, flight history, and number of flights
        return jsonify({
            'registration': registration,
            'icao24': icao24,
            'flight_history': flight_history,
            'flight_count': len(flight_history)
        })
        
    except Exception as e:
        # Return error if something fails
        return jsonify({'error': str(e)}), 500

# Main entry point

if __name__ == "__main__":
    # Optional test?
    test_comprehensive_tracking()
    
    # Print info about server and endpoints
    print("\nStarting Flask server on http://localhost:5000")
    print("Available endpoints:")
    print("  /api/live/all - Current aircraft data only")
    print("  /api/comprehensive/all - Current + flight history")
    print("  /api/history/<registration> - Flight history for a specific aircraft")
    
    # Start Flask development server
    app.run(debug=True, host="0.0.0.0", port=5000)
