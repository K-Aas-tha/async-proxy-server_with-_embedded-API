import requests
import json

PROXY_URL = "http://localhost:8080"

def test_proxy_forwarding():
    print("\n" + "="*50)
    print("📡 Testing Proxy Forwarding (Client -> Proxy:8080 -> Target:8000)")
    print("="*50)

    # 1. Test GET request via proxy
    print("\n1. Sending GET request to /test-endpoint via Proxy...")
    try:
        response = requests.get(f"{PROXY_URL}/test-endpoint")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Test POST request via proxy
    print("\n2. Sending POST request with data via Proxy...")
    data = {"key": "value", "hello": "world"}
    try:
        response = requests.post(f"{PROXY_URL}/data", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_proxy_forwarding()
