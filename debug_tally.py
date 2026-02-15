import requests
import json

headers = {
    "Authorization": "Bearer tly-CPlerdeNW8G9901xIt7ImuvN6pmBtCRI",
    "Content-Type": "application/json",
}

response = requests.get(
    "https://api.tally.so/forms/b5xGbZ/submissions", headers=headers
)
data = response.json()

print("=" * 70)
print(" TALLY SUBMISSION FIELD DEBUG")
print("=" * 70)

if data.get("data"):
    submission = data["data"][0]
    print(f"\nSubmission ID: {submission.get('submissionId')}")
    print(f"Created: {submission.get('createdAt')}")
    print(f"\nFields ({len(submission.get('fields', []))}):")

    for i, field in enumerate(submission.get("fields", []), 1):
        key = field.get("key", "")
        value = field.get("value", "")
        print(f"\n  {i}. key='{key}'")
        print(f"     value='{value}'")
        if "case" in key.lower():
            print(f"     ⭐ CASE NUMBER FIELD FOUND!")
else:
    print("\nNo submissions found")

print("\n" + "=" * 70)
