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
import os
import threading 
from flask import Flask, render_template, jsonify, request   # Import Flask modules for server, templates, and JSON
from flask_cors import CORS                        # Lets the frontend fetch data
from fetch_data import (                           # Import functions and data from fetch_data.py
    AIRCRAFT_MAP,             # Dictionary of aircraft registrations to ICAO24 codes
    get_aircraft_states,      # Function to get current aircraft states
    get_comprehensive_aircraft_data,  # Function to get current + flight history
    get_flight_history,       # Function to get flight history for one aircraft
    test_comprehensive_tracking  # Function to run a full test of current + history data
)
import time  # To get timestamps

# Import the database
try:
    from database import db
    DATABASE_AVAILABLE = True
except ImportError:
    print("⚠️  Database module not available - running without database features")
    DATABASE_AVAILABLE = False


# Initialize Flask app

app = Flask(__name__)  # Create a Flask app instance (starts the web server) 
CORS(app)              # CORS so frontend JS can call API routes without issues

# Debug: Print current directory and template path
print(f"Current working directory: {os.getcwd()}")
print(f"Template folder path: {app.template_folder}")
print(f"Templates exist: {os.path.exists('templates')}")
if os.path.exists('templates'):
    print(f"Files in templates: {os.listdir('templates')}")

def background_cleanup():
    """Background task to clean up old data every hour"""
    while True:
        time.sleep(3600)  # Run every hour
        try:
            if DATABASE_AVAILABLE:
                deleted_count = db.cleanup_old_data()
                print(f"🔄 Database cleanup completed. Removed {deleted_count} old records.")
        except Exception as e:
            print(f"❌ Database cleanup error: {e}")

# Start background cleanup thread if database is available
if DATABASE_AVAILABLE:
    cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
    cleanup_thread.start()
    print("✅ Database background cleanup started")

# Routes

@app.route("/")
def index():
    """
    Homepage route.
    RN returns a simple JSON message indicating the API is running.
    """
    #return jsonify({'message': 'FFC Aircraft Tracker API', 'status': 'running'}) -> comment this back in when html is done to replace previous line
    print("Rendering index.html...")
    return render_template("index.html") 


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

        # Save to database if available
        if DATABASE_AVAILABLE and aircraft_data:
            try:
                db.save_aircraft_status(aircraft_data)
            except Exception as e:
                print(f"⚠️  Could not save to database: {e}")
        
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

        # Process and store flight data in database if available
        if DATABASE_AVAILABLE:
            try:
                process_flight_data(comprehensive_data)
            except Exception as e:
                print(f"⚠️  Could not process flight data: {e}")

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
    
# NEW DATABASE ENDPOINTS

@app.route("/api/database/flights/recent")
def get_recent_flights():
    """Get recent flights from database"""
    if not DATABASE_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
        
    try:
        hours = request.args.get('hours', 48, type=int)
        flights = db.get_recent_flights(hours)
        return jsonify({
            'timestamp': int(time.time()),
            'flights': flights,
            'count': len(flights)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/database/aircraft/<registration>/history")
def get_database_aircraft_history(registration):
    """Get aircraft flight history from database"""
    if not DATABASE_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
        
    try:
        hours = request.args.get('hours', 48, type=int)
        flights = db.get_aircraft_flight_history(registration, hours)
        
        # Get statistics if available
        stats = {}
        try:
            stats = db.get_aircraft_stats(registration)
        except:
            pass  # Stats are optional
        
        return jsonify({
            'registration': registration,
            'flights': flights,
            'stats': stats,
            'count': len(flights)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/database/stats")
def get_database_stats():
    """Get overall database statistics"""
    if not DATABASE_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
        
    try:
        # Get recent flight count from database
        recent_flights = db.get_recent_flights(hours=48)
        
        return jsonify({
            'timestamp': int(time.time()),
            'total_tracked_aircraft': len(AIRCRAFT_MAP),
            'recent_flights_count': len(recent_flights),
            'database_available': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_flight_data(comprehensive_data):
    """Process flight data and store in database"""
    try:
        for icao24, data in comprehensive_data.items():
            if data.get('flight_history'):
                for flight in data['flight_history']:
                    # Convert flight data to database format
                    flight_session = {
                        'icao24': icao24,
                        'callsign': flight.get('callsign'),
                        'departure_airport': flight.get('estDepartureAirport'),
                        'arrival_airport': flight.get('estArrivalAirport'),
                        'departure_time': flight.get('firstSeen'),
                        'arrival_time': flight.get('lastSeen'),
                        'duration_minutes': int(flight.get('lastSeen', 0) - flight.get('firstSeen', 0)) // 60,
                        'max_altitude': None,  # These would come from position data
                        'max_speed': None,
                        'distance_km': None,
                        'first_seen': flight.get('firstSeen'),
                        'last_seen': flight.get('lastSeen')
                    }
                    
                    # Save to database
                    db.save_flight_session(flight_session)
    except Exception as e:
        print(f"Error processing flight data: {e}")

# Main entry point

if __name__ == "__main__":
    # Run cleanup once at startup if database available
    if DATABASE_AVAILABLE:
        try:
            deleted_count = db.cleanup_old_data()
            print(f"🗑️  Initial database cleanup removed {deleted_count} old records")
        except Exception as e:
            print(f"⚠️  Initial database cleanup failed: {e}")
    # Optional test?
    test_comprehensive_tracking()
    
    # Print info about server and endpoints
    print("\nStarting Flask server on http://localhost:5000")
    print("Available endpoints:")
    print("  /api/live/all - Current aircraft data only")
    print("  /api/comprehensive/all - Current + flight history")
    print("  /api/history/<registration> - Flight history for a specific aircraft")

    if DATABASE_AVAILABLE:
        print("  /api/database/flights/recent - Recent flights from database")
        print("  /api/database/aircraft/<registration>/history - Aircraft history from DB")
        print("  /api/database/stats - Database statistics")
        print("✅ Database features ENABLED")
    else:
        print("⚠️  Database features DISABLED - create database.py to enable")
    
    # Start Flask development server
    app.run(debug=True, host="0.0.0.0", port=5000)
