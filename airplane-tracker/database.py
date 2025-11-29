# database.py
import sqlite3
import time
from datetime import datetime, timedelta
import logging
from fetch_data import AIRCRAFT_MAP

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AircraftDatabase:
    def __init__(self, db_path='aircraft_tracker.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Aircraft master table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aircraft (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration TEXT UNIQUE NOT NULL,
                icao24 TEXT UNIQUE NOT NULL,
                aircraft_type TEXT,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Flight sessions table (complete flights)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flight_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aircraft_id INTEGER,
                callsign TEXT,
                departure_airport TEXT,
                arrival_airport TEXT,
                departure_time TIMESTAMP,
                arrival_time TIMESTAMP,
                duration_minutes INTEGER,
                max_altitude INTEGER,
                max_speed INTEGER,
                distance_km REAL,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (aircraft_id) REFERENCES aircraft (id)
            )
        ''')
        
        # Status history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aircraft_id INTEGER,
                timestamp INTEGER,
                latitude REAL,
                longitude REAL,
                altitude REAL,
                velocity REAL,
                heading REAL,
                on_ground BOOLEAN,
                callsign TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (aircraft_id) REFERENCES aircraft (id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_flight_sessions_times ON flight_sessions(departure_time, arrival_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_history_timestamp ON status_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON flight_sessions(created_at)')
        
        conn.commit()
        conn.close()
        
        # Insert initial aircraft from AIRCRAFT_MAP
        self._initialize_aircraft()
        logging.info("Database initialized successfully")
    
    def _initialize_aircraft(self):
        """Initialize aircraft from the AIRCRAFT_MAP"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for registration, icao24 in AIRCRAFT_MAP.items():
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO aircraft (registration, icao24, description)
                    VALUES (?, ?, ?)
                ''', (registration, icao24, f"FFC Training Aircraft {registration}"))
            except Exception as e:
                logging.warning(f"Could not insert aircraft {registration}: {e}")
        
        conn.commit()
        conn.close()
    
    def cleanup_old_data(self):
        """Remove data older than 48 hours"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=48)).timestamp()
        
        # Delete old status history
        cursor.execute('DELETE FROM status_history WHERE timestamp < ?', (cutoff_time,))
        status_deleted = cursor.rowcount
        
        # Delete flight sessions that ended more than 48 hours ago
        cursor.execute('DELETE FROM flight_sessions WHERE last_seen < ?', (cutoff_time,))
        flights_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        total_deleted = status_deleted + flights_deleted
        logging.info(f"Database cleanup removed {total_deleted} old records")
        return total_deleted
    
    def save_aircraft_status(self, aircraft_data):
        """Save current aircraft status to history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for aircraft in aircraft_data:
            try:
                # Get aircraft ID
                cursor.execute('SELECT id FROM aircraft WHERE icao24 = ?', (aircraft['icao24'],))
                result = cursor.fetchone()
                
                if result:
                    aircraft_id = result[0]
                    cursor.execute('''
                        INSERT INTO status_history 
                        (aircraft_id, timestamp, latitude, longitude, altitude, velocity, heading, on_ground, callsign)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        aircraft_id,
                        aircraft.get('last_contact', int(time.time())),
                        aircraft.get('latitude'),
                        aircraft.get('longitude'),
                        aircraft.get('altitude'),
                        aircraft.get('velocity'),
                        aircraft.get('heading'),
                        aircraft.get('on_ground', False),
                        aircraft.get('callsign', '')
                    ))
            except Exception as e:
                logging.warning(f"Could not save status for {aircraft.get('icao24')}: {e}")
        
        conn.commit()
        conn.close()
    
    def save_flight_session(self, flight_data):
        """Save a complete flight session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get aircraft ID
            cursor.execute('SELECT id FROM aircraft WHERE icao24 = ?', (flight_data['icao24'],))
            result = cursor.fetchone()
            
            if result:
                aircraft_id = result[0]
                
                # Check if this flight already exists to avoid duplicates
                cursor.execute('''
                    SELECT id FROM flight_sessions 
                    WHERE aircraft_id = ? AND first_seen = ? AND last_seen = ?
                ''', (aircraft_id, flight_data.get('first_seen'), flight_data.get('last_seen')))
                
                if not cursor.fetchone():  # Only insert if it doesn't exist
                    cursor.execute('''
                        INSERT INTO flight_sessions 
                        (aircraft_id, callsign, departure_airport, arrival_airport, 
                         departure_time, arrival_time, duration_minutes, max_altitude, 
                         max_speed, distance_km, first_seen, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        aircraft_id,
                        flight_data.get('callsign'),
                        flight_data.get('departure_airport'),
                        flight_data.get('arrival_airport'),
                        flight_data.get('departure_time'),
                        flight_data.get('arrival_time'),
                        flight_data.get('duration_minutes'),
                        flight_data.get('max_altitude'),
                        flight_data.get('max_speed'),
                        flight_data.get('distance_km'),
                        flight_data.get('first_seen'),
                        flight_data.get('last_seen')
                    ))
                
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error saving flight session: {e}")
        finally:
            conn.close()
        
        return None
    
    def get_recent_flights(self, hours=48):
        """Get flights from the last specified hours"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
        
        cursor.execute('''
            SELECT 
                fs.*,
                a.registration,
                a.icao24
            FROM flight_sessions fs
            JOIN aircraft a ON fs.aircraft_id = a.id
            WHERE fs.last_seen >= ?
            ORDER BY fs.departure_time DESC
        ''', (cutoff_time,))
        
        flights = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return flights
    
    def get_aircraft_flight_history(self, registration, hours=48):
        """Get flight history for a specific aircraft"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
        
        cursor.execute('''
            SELECT 
                fs.*,
                a.registration,
                a.icao24
            FROM flight_sessions fs
            JOIN aircraft a ON fs.aircraft_id = a.id
            WHERE a.registration = ? AND fs.last_seen >= ?
            ORDER BY fs.departure_time DESC
        ''', (registration, cutoff_time))
        
        flights = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return flights
    
    def get_aircraft_stats(self, registration, days=7):
        """Get statistics for a specific aircraft"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()
        
        # Total flights
        cursor.execute('''
            SELECT COUNT(*) FROM flight_sessions fs
            JOIN aircraft a ON fs.aircraft_id = a.id
            WHERE a.registration = ? AND fs.last_seen >= ?
        ''', (registration, cutoff_time))
        total_flights = cursor.fetchone()[0] or 0
        
        # Total flight time
        cursor.execute('''
            SELECT SUM(duration_minutes) FROM flight_sessions fs
            JOIN aircraft a ON fs.aircraft_id = a.id
            WHERE a.registration = ? AND fs.last_seen >= ?
        ''', (registration, cutoff_time))
        total_minutes = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_flights': total_flights,
            'total_flight_time_minutes': total_minutes,
            'total_flight_time_hours': round(total_minutes / 60, 1)
        }

# Database instance
db = AircraftDatabase()