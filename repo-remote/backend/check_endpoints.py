import requests

urls = [
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8000/traffic/live",
    "http://127.0.0.1:8000/traffic/heatmap",
]

for u in urls:
    try:
        r = requests.get(u, timeout=10)
        print(f"URL: {u}\nStatus: {r.status_code}\nResponse:\n{r.text}\n{'-'*60}")
    except Exception as e:
        print(f"URL: {u}\nEXCEPTION: {e}\n{'-'*60}")
