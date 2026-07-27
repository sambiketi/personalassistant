import requests
import json

# Test the schedule endpoint
response = requests.post(
    "http://localhost:8000/api/schedule",
    json={
        "prompt": "Waking up at 6am. Exercise 1 hour, Code for 2 hours, Break, Apply to jobs",
        "unsnoozables": ["Exercise", "Apply to jobs"]
    }
)

print(json.dumps(response.json(), indent=2))
