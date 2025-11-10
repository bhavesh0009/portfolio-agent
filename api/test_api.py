"""
Test script for FastAPI backend endpoints
Run this after starting the API server with: python api/price_service.py
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def test_endpoint(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """
    Test an API endpoint and print results

    Args:
        method: HTTP method (GET, POST)
        endpoint: API endpoint path
        **kwargs: Additional arguments for requests
    """
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*80}")
    print(f"Testing: {method} {endpoint}")
    print(f"{'='*80}")

    try:
        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        else:
            print(f"Unsupported method: {method}")
            return {}

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response:\n{json.dumps(data, indent=2)}")
            return data
        else:
            print(f"Error: {response.text}")
            return {}

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print("Make sure the server is running: python api/price_service.py")
        return {}
    except Exception as e:
        print(f"ERROR: {e}")
        return {}


def main():
    """Run all API endpoint tests"""

    print("="*80)
    print("Portfolio Agent API Test Suite")
    print("="*80)

    # Test 1: Health check
    test_endpoint("GET", "/")

    # Test 2: Performance metrics
    test_endpoint("GET", "/api/performance/1")

    # Test 3: Benchmark comparison (ALL period)
    test_endpoint("GET", "/api/benchmarks/1?period=ALL")

    # Test 4: Benchmark comparison (3M period)
    test_endpoint("GET", "/api/benchmarks/1?period=3M")

    # Test 5: Manager updates
    test_endpoint("GET", "/api/manager-updates/1")

    # Test 6: Risk metrics
    test_endpoint("GET", "/api/risk-metrics/1?period_days=90")

    # Test 7: Price history for first stock
    test_endpoint("GET", "/api/price-history/1?days=30")

    # Test 8: Manual price update (commented out to avoid triggering during tests)
    # Uncomment if you want to test price updates
    # test_endpoint("POST", "/api/prices/update?portfolio_id=1")

    print("\n" + "="*80)
    print("Test suite complete!")
    print("="*80)


if __name__ == '__main__':
    main()
