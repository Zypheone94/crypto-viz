"""Script pour tester les routes de l'API metrics avec httpx."""
import httpx
from datetime import datetime, timedelta
import json

# URL de base de l'API
BASE_URL = "http://localhost:8000"

def print_response(endpoint, response):
    """Affiche la réponse de manière formatée."""
    print(f"\n{'='*70}")
    print(f"🔗 Endpoint: {endpoint}")
    print(f"📊 Status: {response.status_code}")
    print(f"📦 Response:")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)
    
    print(f"{'='*70}\n")

def test_all_routes():
    """Teste toutes les routes de l'API."""
    
    # Dates pour les tests
    now = datetime.now()
    to_date = now.isoformat() + "Z"
    from_date = (now - timedelta(days=7)).isoformat() + "Z"
    
    print("🧪 Test des routes de l'API Metrics")
    print(f"📅 Période: {from_date} → {to_date}\n")
    
    with httpx.Client() as client:
        
        # Test 1: GET /metrics/trending
        print("\n1️⃣ Test: /metrics/trending")
        try:
            response = client.get(
                f"{BASE_URL}/metrics/trending",
                params={
                    "from": from_date,
                    "to": to_date,
                    "bucket": "day",
                    "limit": 5
                },
                timeout=10.0
            )
            print_response("/metrics/trending", response)
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        # Test 2: GET /metrics/timeseries
        print("\n2️⃣ Test: /metrics/timeseries")
        try:
            response = client.get(
                f"{BASE_URL}/metrics/timeseries",
                params={
                    "from": from_date,
                    "to": to_date,
                    "bucket": "day"
                },
                timeout=10.0
            )
            print_response("/metrics/timeseries", response)
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        # Test 3: GET /metrics/latest
        print("\n3️⃣ Test: /metrics/latest")
        try:
            response = client.get(
                f"{BASE_URL}/metrics/latest",
                timeout=10.0
            )
            print_response("/metrics/latest", response)
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        # Test 4: GET /metrics/top
        print("\n4️⃣ Test: /metrics/top")
        try:
            response = client.get(
                f"{BASE_URL}/metrics/top",
                params={
                    "from": from_date,
                    "to": to_date,
                    "limit": 5
                },
                timeout=10.0
            )
            print_response("/metrics/top", response)
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        # Test 5: GET /metrics/aggregate
        print("\n5️⃣ Test: /metrics/aggregate")
        try:
            response = client.get(
                f"{BASE_URL}/metrics/aggregate",
                params={
                    "from": from_date,
                    "to": to_date,
                    "bucket": "day"
                },
                timeout=10.0
            )
            print_response("/metrics/aggregate", response)
        except Exception as e:
            print(f"❌ Erreur: {e}")

def test_single_route(route, params=None):
    """Teste une seule route."""
    with httpx.Client() as client:
        try:
            response = client.get(f"{BASE_URL}{route}", params=params, timeout=10.0)
            print_response(route, response)
        except Exception as e:
            print(f"❌ Erreur lors du test de {route}: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test d'une route spécifique
        route = sys.argv[1]
        
        # Préparer les paramètres par défaut
        now = datetime.now()
        default_params = {
            "from": (now - timedelta(days=7)).isoformat() + "Z",
            "to": now.isoformat() + "Z"
        }
        
        test_single_route(route, default_params)
    else:
        # Test de toutes les routes
        test_all_routes()
