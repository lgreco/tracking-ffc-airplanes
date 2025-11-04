# HOW TO USE TESTING 
### in one terminal window run 'python app.py'
### in second terminal window 
#       'cd airplane-tracker'
#       'curl http://localhost:5000/'
#       'curl http://localhost:5000//api/live/all'
#       'curl http://localhost:5000/api/comprehensive/all'
#       'curl http://localhost:5000/api/history/<registration>' 
# you can also run 'python testApp.py' to see all the tests passing


import requests
import json

BASE_URL = "http://localhost:5000"

def test_api_endpoint(endpoint, name):
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"\n=== {name} ===")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error testing {name}: {e}")
        return False

def main():
    print("Testing FFC Aircraft Tracker API Endpoints...")
    
    # Test only the API endpoints that return JSON
    endpoints = [
        ("/api/live/all", "Live Aircraft Data"),
        ("/api/comprehensive/all", "Comprehensive Data"),
        ("/api/history/N31401", "Aircraft History - N31401"),
    ]
    
    results = []
    for endpoint, name in endpoints:
        results.append(test_api_endpoint(endpoint, name))
    
    print(f"\n=== SUMMARY ===")
    print(f"API Endpoints Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All API endpoints working perfectly!")
        print("💡 Note: Empty aircraft data is normal when planes aren't flying")
    else:
        print("❌ Some API tests failed.")

if __name__ == "__main__":
    main()