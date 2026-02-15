import requests
import re

headers = {
    "Authorization": "Bearer tly-CPlerdeNW8G9901xIt7ImuvN6pmBtCRI",
    "Content-Type": "application/json",
}

response = requests.get(
    "https://api.tally.so/forms/b5xGbZ/submissions", headers=headers
)
data = response.json()

print("TALLY SUBMISSION DEBUG")
print("=" * 70)

submissions = data.get("data", [])
print(f"Total submissions found: {len(submissions)}\n")

for idx, submission in enumerate(submissions, 1):
    print(f"Submission {idx}:")
    print(f"  ID: {submission.get('submissionId')}")

    fields = submission.get("fields", [])
    print(f"  Fields: {len(fields)}")

    response_case = None
    team_number = None

    for field in fields:
        field_key = field.get("key", "").lower()
        field_value = field.get("value", "")

        print(f"    - key: '{field.get('key')}' = '{str(field_value)[:50]}'")

        # Check for case
        if field_key == "case" or "case" in field_key:
            case_match = re.search(r"\d+", str(field_value))
            if case_match:
                response_case = int(case_match.group())
                print(f"      ⭐ CASE NUMBER EXTRACTED: {response_case}")

        # Check for team
        if "team" in field_key and "number" in field_key:
            team_number = field_value
            print(f"      ⭐ TEAM NUMBER: {team_number}")

    print(f"\n  RESULT: Case={response_case}, Team={team_number}")
    print()

print("=" * 70)
