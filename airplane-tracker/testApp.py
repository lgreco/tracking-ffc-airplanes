import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(endpoint, name):
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"\n=== {name} ===")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing {name}: {e}")
        return False

def main():
    print("Testing FFC Aircraft Tracker API...")
    
    # Test all endpoints
    endpoints = [
        ("/", "Root Endpoint"),
        ("/api/live/all", "Live Aircraft Data"),
        ("/api/comprehensive/all", "Comprehensive Data"),
        # ("/api/history/N31401", "Aircraft History")  # Uncomment with actual registration
    ]
    
    results = []
    for endpoint, name in endpoints:
        results.append(test_endpoint(endpoint, name))
    
    print(f"\n=== SUMMARY ===")
    print(f"Passed: {sum(results)}/{len(results)} tests")
    
    if all(results):
        print("✅ All tests passed! API is working correctly.")
    else:
        print("❌ Some tests failed. Check the server and endpoints.")

if __name__ == "__main__":
    main()