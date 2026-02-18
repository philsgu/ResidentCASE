import streamlit as st
import re
import requests
from typing import Dict, List
import os
import time

# Configure API Keys from Streamlit secrets
# For local development: .streamlit/secrets.toml
# For Streamlit Cloud: Add secrets in dashboard Settings > Secrets
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
    TALLY_API_KEY = st.secrets.get("TALLY_API_KEY", "")
    TALLY_FORM_ID = st.secrets.get("TALLY_FORM_ID", "b5xGbZ")
    USE_TALLY_API = st.secrets.get("USE_TALLY_API", True)
except Exception as e:
    # Fallback to environment variables if secrets not available
    st.warning("⚠️ Secrets not configured. Using environment variables or demo mode.")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    TALLY_API_KEY = os.getenv("TALLY_API_KEY", "")
    TALLY_FORM_ID = os.getenv("TALLY_FORM_ID", "b5xGbZ")
    USE_TALLY_API = os.getenv("USE_TALLY_API", "false").lower() == "true"

# Configure Tally API URL
TALLY_API_URL = f"https://api.tally.so/forms/{TALLY_FORM_ID}/submissions"

# Page configuration
st.set_page_config(
    page_title="Resident CASE - Diabetes Management",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add custom CSS for better formatting
st.markdown(
    """
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        padding: 10px 24px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
    }
    .team-response {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 4px solid #ff4b4b;
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


def parse_cases_file(file_path: str) -> List[Dict]:
    """Parse cases.md and extract case information"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    cases = []

    # Split by the separator "* * *" (which appears as horizontal rule)
    # First, split by the actual separator pattern
    case_blocks = re.split(r"\n\* \* \*\n|\n---\n", content)

    for block in case_blocks:
        # Skip if doesn't contain a case title
        if "## Case" not in block:
            continue

        # Extract case title
        title_match = re.search(r"## (Case \d+:.*?)(?:\n|$)", block)
        if not title_match:
            continue
        case_title = title_match.group(1).strip()

        # Split by management section header to separate description from management
        parts = re.split(
            r"\*\*(?:Management Considerations|Management Plan):\*\*", block, maxsplit=1
        )

        if len(parts) == 2:
            description_part = parts[0].strip()
            management_part = parts[1].strip()

            # The description is everything after the title and before Management Considerations
            # Clean up the description
            description = description_part

            # Clean up management text (remove any trailing references section markers)
            management = management_part

        else:
            # Fallback if structure is different
            description_part = block
            management_part = ""
            description = description_part
            management = management_part

        cases.append(
            {
                "title": case_title,
                "description": description,
                "management": management,
            }
        )

    return cases


def extract_section(text: str, section_name: str) -> str:
    """Extract content of a specific section"""
    # Pattern to match section content until next major section or end
    pattern = rf"\*\*{re.escape(section_name)}\*\*\s*(.*?)(?=\*\*[A-Z][^:]*:|---|\Z)"
    match = re.search(pattern, text, re.DOTALL)

    if match:
        content = match.group(1).strip()
        return content
    return ""


def fetch_tally_responses() -> List[Dict]:
    """Fetch responses from Tally.so API"""
    if not USE_TALLY_API:
        return []

    headers = {
        "Authorization": f"Bearer {TALLY_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(TALLY_API_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        # Tally API returns submissions array, not data array
        submissions = data.get("submissions", [])
        return submissions
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.warning("⚠️ Tally API authentication failed. This could mean:")
            st.info(
                """
            - The API key needs to be regenerated in Tally settings
            - The form might need different access permissions
            - The API key might be for a different form
            
            **To fix this:**
            1. Go to Tally.so → Settings → Integrations
            2. Generate a new API key
            3. Update the key in app.py (line 11)
            4. Or use the demo mode below
            """
            )
        else:
            st.error(f"HTTP Error: {e}")
        return []
    except Exception as e:
        st.error(f"Error fetching Tally responses: {e}")
        return []


def categorize_responses_by_case(
    submissions: List[Dict], case_number: int
) -> List[Dict]:
    """Filter and categorize responses for a specific case"""
    case_responses = []

    # Map question IDs to their purpose
    # These IDs come from the Tally form structure
    QUESTION_IDS = {
        "oAR5MN": "team_number",  # Team Number dropdown
        "GrpqdO": "case_number",  # Hidden field with case number
        "OAXb5M": "team_name",  # Team Name text input
        "VZPb56": "additional_tests",  # Additional tests textarea
        "PA9b5x": "management",  # Management textarea
    }

    for submission in submissions:
        # Each submission has a responses array
        responses = submission.get("responses", [])

        # Extract data from responses by questionId
        submission_data = {}

        for response in responses:
            question_id = response.get("questionId")
            answer = response.get("answer")

            # Map questionId to field name
            if question_id in QUESTION_IDS:
                field_name = QUESTION_IDS[question_id]

                # Handle different answer formats
                if field_name == "case_number":
                    # Hidden field: answer is {"case_number": "10"}
                    if isinstance(answer, dict):
                        submission_data["case_number"] = int(
                            answer.get("case_number", 0)
                        )
                elif field_name == "team_number":
                    # Dropdown: answer is ["1"]
                    if isinstance(answer, list) and answer:
                        submission_data["team_number"] = answer[0]
                else:
                    # Text fields: answer is string
                    submission_data[field_name] = answer

        # Check if this submission is for the requested case
        if submission_data.get("case_number") == case_number:
            # Build response text
            response_parts = []
            if submission_data.get("additional_tests"):
                response_parts.append(
                    f"**Additional Tests/Labs/Referrals:**\n{submission_data['additional_tests']}"
                )
            if submission_data.get("management"):
                response_parts.append(
                    f"**Management:**\n{submission_data['management']}"
                )

            response_text = (
                "\n\n".join(response_parts)
                if response_parts
                else "No response provided"
            )

            # Determine team identifier - show both number and name
            team_name = submission_data.get("team_name", "")
            team_number = submission_data.get("team_number", "")

            if team_number and team_name:
                team_identifier = f"Team {team_number} - {team_name}"
            elif team_number:
                team_identifier = f"Team {team_number}"
            elif team_name:
                team_identifier = team_name
            else:
                team_identifier = "Unknown Team"

            case_responses.append(
                {
                    "team": team_identifier,
                    "response": response_text,
                    "submitted_at": submission.get("submittedAt", ""),
                    "raw_data": submission_data,
                }
            )

    return case_responses


def rate_response_with_gemini(
    case_description: str, management_guideline: str, team_response: str
) -> Dict:
    """Use Groq API to rate and score a team's response"""
    max_retries = 3
    retry_delay = 5  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            prompt = f"""You are evaluating a medical resident's case response against a reference answer.

**Case Background:**
{case_description}

**REFERENCE ANSWER (Evidence-Based Management):**
{management_guideline}

**Team's Response to Evaluate:**
{team_response}

---
STRICT EVALUATION PROTOCOL — follow every step:

**STEP 1 — CHECKLIST:** Read the Reference Answer above. List each distinct management point from the reference (number them 1, 2, 3...). For each point, mark whether the team's response addressed it: [HIT], [PARTIAL], or [MISSED].

**STEP 2 — TALLY:** Count your HITs, PARTIALs, and MISSEDs.

**STEP 3 — SCORE CALCULATION:**
- Each HIT = full points, each PARTIAL = half points, each MISSED = 0
- Base score = (HITs + 0.5×PARTIALs) / total points × 70  (covers 70 points)
- Accuracy/safety penalty: deduct up to 20 points for incorrect, dangerous, or missing safety-critical recommendations
- Organization bonus: up to 10 points for clear, well-structured, complete reasoning
- Final score = base score + accuracy/safety + organization (0–100)

**STEP 4 — SCORING RULES (strictly enforce):**
- 80–100: Addresses nearly all reference points correctly with good reasoning
- 60–79: Addresses most points but misses some important ones
- 40–59: Addresses some points but misses half or more of the key recommendations
- 20–39: Only addresses a few points; significant gaps in management
- 0–19: Largely irrelevant, incorrect, or missing critical safety considerations

**IMPORTANT**: Be discriminating. If the response is vague or generic without naming specific interventions, score it LOW (below 50). Do not give high scores just for using medical-sounding language.

**OUTPUT FORMAT (use exactly this format):**

CHECKLIST:
1. [management point from reference] — [HIT/PARTIAL/MISSED]
2. [management point from reference] — [HIT/PARTIAL/MISSED]
(continue for all reference points)

TALLY: [X] HITs, [Y] PARTIALs, [Z] MISSEDs out of [total] points

SCORE: [number 0-100]

STRENGTHS:
- [specific points correctly addressed]

AREAS FOR IMPROVEMENT:
- [specific gaps or errors]

KEY POINTS MISSED:
- [reference points not addressed]

CLINICAL REASONING:
[2-3 sentences assessing quality of clinical reasoning]
"""

            # Use Groq API with Llama 3.3 70B
            url = "https://api.groq.com/openai/v1/chat/completions"

            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict medical education evaluator. Your job is to critically assess "
                            "resident physicians' responses against a reference answer. You must be rigorous and "
                            "discriminating — scores should reflect the actual quality of the response. "
                            "Do NOT inflate scores. A response that only partially addresses the reference "
                            "should score 40-60. A response missing major points should score below 40. "
                            "Only award high scores (80+) for responses that are thorough and accurate. "
                            "Different teams should receive meaningfully different scores based on their responses."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
            }

            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            evaluation_text = result["choices"][0]["message"]["content"]

            # Parse the response
            score_match = re.search(r"SCORE:\s*(\d+)", evaluation_text)
            score = int(score_match.group(1)) if score_match else 0

            checklist_match = re.search(
                r"CHECKLIST:(.*?)(?=TALLY:|SCORE:|\Z)",
                evaluation_text,
                re.DOTALL,
            )
            checklist = checklist_match.group(1).strip() if checklist_match else ""

            tally_match = re.search(
                r"TALLY:(.*?)(?=SCORE:|\Z)", evaluation_text, re.DOTALL
            )
            tally = tally_match.group(1).strip() if tally_match else ""

            strengths_match = re.search(
                r"STRENGTHS:(.*?)(?=AREAS FOR IMPROVEMENT:|KEY POINTS MISSED:|CLINICAL REASONING:|\Z)",
                evaluation_text,
                re.DOTALL,
            )
            strengths = strengths_match.group(1).strip() if strengths_match else ""

            improvements_match = re.search(
                r"AREAS FOR IMPROVEMENT:(.*?)(?=KEY POINTS MISSED:|CLINICAL REASONING:|\Z)",
                evaluation_text,
                re.DOTALL,
            )
            improvements = (
                improvements_match.group(1).strip() if improvements_match else ""
            )

            missed_match = re.search(
                r"KEY POINTS MISSED:(.*?)(?=CLINICAL REASONING:|\Z)",
                evaluation_text,
                re.DOTALL,
            )
            missed = missed_match.group(1).strip() if missed_match else ""

            reasoning_match = re.search(
                r"CLINICAL REASONING:(.*?)(?=\Z)", evaluation_text, re.DOTALL
            )
            reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

            return {
                "score": score,
                "checklist": checklist,
                "tally": tally,
                "strengths": strengths,
                "improvements": improvements,
                "missed_points": missed,
                "clinical_reasoning": reasoning,
                "full_evaluation": evaluation_text,
            }

        except requests.exceptions.HTTPError as e:
            # Handle 429 (rate limit) errors with retry
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)  # Exponential backoff
                st.warning(
                    f"⏳ Rate limit reached. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
                continue  # Retry
            else:
                # Final attempt failed or other HTTP error
                st.error(f"Error rating response: {e}")
                return {
                    "score": 0,
                    "checklist": "",
                    "tally": "",
                    "strengths": "Error occurred during evaluation",
                    "improvements": "",
                    "missed_points": "",
                    "clinical_reasoning": "",
                    "full_evaluation": f"Error: {e}",
                }

        except Exception as e:
            st.error(f"Error rating response: {e}")
            return {
                "score": 0,
                "checklist": "",
                "tally": "",
                "strengths": "Error occurred during evaluation",
                "improvements": "",
                "missed_points": "",
                "clinical_reasoning": "",
                "full_evaluation": f"Error: {e}",
            }

    # If all retries failed (should not reach here, but for safety)
    return {
        "score": 0,
        "checklist": "",
        "tally": "",
        "strengths": "All retry attempts failed",
        "improvements": "",
        "missed_points": "",
        "clinical_reasoning": "",
        "full_evaluation": "Error: Maximum retries exceeded",
    }


def display_team_response(team_name: str, response_data: Dict, evaluation: Dict):
    """Display a single team's response with evaluation"""
    st.markdown(f"### 👥 {team_name}")

    # Display score card
    score = evaluation["score"]
    score_color = "#2ecc71" if score >= 80 else "#f39c12" if score >= 60 else "#e74c3c"

    st.markdown(
        f"""
    <div class="score-card" style="background: {score_color};">
        <h2 style="margin: 0;">Score: {score}/100</h2>
        <p style="margin: 5px 0 0 0;">{'Excellent' if score >= 80 else 'Good' if score >= 60 else 'Needs Improvement'}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Display response
    with st.expander("📝 Team Response", expanded=True):
        st.markdown(response_data["response"])
        if response_data.get("submitted_at"):
            st.caption(f"Submitted: {response_data['submitted_at']}")

    # Display evaluation
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ✅ Strengths")
        st.markdown(evaluation["strengths"])

        st.markdown("#### 🎯 Clinical Reasoning")
        st.markdown(evaluation["clinical_reasoning"])

    with col2:
        st.markdown("#### 📈 Areas for Improvement")
        st.markdown(evaluation["improvements"])

        if evaluation["missed_points"]:
            st.markdown("#### ⚠️ Key Points Missed")
            st.markdown(evaluation["missed_points"])

    # Show checklist breakdown
    if evaluation.get("checklist") or evaluation.get("tally"):
        with st.expander("🔍 Scoring Breakdown (Checklist)", expanded=False):
            if evaluation.get("tally"):
                st.info(f"**Tally:** {evaluation['tally']}")
            if evaluation.get("checklist"):
                st.markdown(evaluation["checklist"])

    st.markdown("---")


def main():
    # Title
    st.title("🏥 Resident CASE - Diabetes Management Scenarios")
    st.markdown("*Interactive case-based learning with AI-powered evaluation*")
    st.markdown("---")

    # Load cases
    try:
        cases = parse_cases_file("cases.md")
    except Exception as e:
        st.error(f"Error loading cases: {e}")
        st.info("Please ensure cases.md is in the same directory as this app.")
        return

    # Sidebar navigation
    st.sidebar.title("📋 Navigation")

    # Add view selection
    view_mode = st.sidebar.radio(
        "Select View:",
        ["📊 Overall Leaderboard", "📋 Individual Cases"],
        index=1,  # Default to Cases view
    )

    st.sidebar.markdown("---")

    if view_mode == "📊 Overall Leaderboard":
        # Display overall leaderboard across all cases
        st.header("🏆 Overall Team Leaderboard")
        st.markdown("*Aggregate scores across all 10 diabetes management cases*")
        st.success(
            "⚡ **Fast Mode**: Using cached evaluations from individual case pages for instant display"
        )
        st.markdown("---")

        # Fetch all responses
        all_responses = fetch_tally_responses()

        if not all_responses:
            st.info("⚠️ No team responses found. Using demo mode.")
            st.markdown(
                "This page will show overall standings once teams submit responses."
            )
        else:
            # Calculate total scores for each team across all cases
            # ONLY use cached evaluations for fast display
            team_scores = (
                {}
            )  # {team_name: {"total": score, "cases": {case_num: score}}}
            unevaluated_responses = []  # Track responses that need evaluation

            for case_idx in range(len(cases)):
                case_number = case_idx + 1
                case_responses = categorize_responses_by_case(
                    all_responses, case_number
                )

                if case_responses:
                    for response_data in case_responses:
                        team_name = response_data["team"]
                        eval_cache_key = f"cache_{case_number}_{team_name}"

                        # ONLY use cached evaluations - don't run AI here
                        if eval_cache_key in st.session_state:
                            evaluation = st.session_state[eval_cache_key]
                            score = evaluation["score"]

                            # Initialize team if not exists
                            if team_name not in team_scores:
                                team_scores[team_name] = {
                                    "total": 0,
                                    "cases": {},
                                    "count": 0,
                                }

                            team_scores[team_name]["cases"][case_number] = score
                            team_scores[team_name]["total"] += score
                            team_scores[team_name]["count"] += 1
                        else:
                            # Track unevaluated responses
                            unevaluated_responses.append(
                                {
                                    "case_idx": case_idx,
                                    "case_number": case_number,
                                    "team_name": team_name,
                                    "response_data": response_data,
                                }
                            )

            # Show info about unevaluated responses
            if unevaluated_responses:
                st.info(
                    f"⚡ **Fast Display Mode**: Showing {len(team_scores)} team(s) with previously evaluated scores. "
                    f"{len(unevaluated_responses)} response(s) not yet evaluated."
                )

                # Add button to evaluate remaining responses
                if st.button(
                    f"🤖 Evaluate {len(unevaluated_responses)} Remaining Response(s)",
                    key="eval_remaining_leaderboard",
                    type="primary",
                ):
                    progress_text = st.empty()
                    progress_bar = st.progress(0)

                    for idx, item in enumerate(unevaluated_responses):
                        progress_text.text(
                            f"Evaluating {item['team_name']} for Case {item['case_number']}... ({idx+1}/{len(unevaluated_responses)})"
                        )
                        progress_bar.progress((idx + 1) / len(unevaluated_responses))

                        # Evaluate and cache
                        evaluation = rate_response_with_gemini(
                            cases[item["case_idx"]]["description"],
                            cases[item["case_idx"]]["management"],
                            item["response_data"]["response"],
                        )
                        eval_cache_key = (
                            f"cache_{item['case_number']}_{item['team_name']}"
                        )
                        st.session_state[eval_cache_key] = evaluation

                    progress_text.empty()
                    progress_bar.empty()
                    st.success("✅ All evaluations complete! Refreshing leaderboard...")
                    st.rerun()

                st.markdown("---")

            if not team_scores:
                st.warning(
                    "⚠️ No evaluated responses found yet. Please:\n"
                    "1. Go to individual case pages and click 'Evaluate All Teams'\n"
                    "2. OR click the button above to evaluate all pending responses"
                )
            else:
                # Sort teams by total score
                sorted_teams = sorted(
                    team_scores.items(), key=lambda x: x[1]["total"], reverse=True
                )

                # Display winner announcement
                winner_name = sorted_teams[0][0]
                winner_total = sorted_teams[0][1]["total"]
                winner_count = sorted_teams[0][1]["count"]
                winner_avg = winner_total / winner_count if winner_count > 0 else 0

                st.balloons()
                st.markdown(
                    f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; padding: 30px; border-radius: 15px; text-align: center; margin: 20px 0;">
                    <h1 style="margin: 0; font-size: 3em;">🥇 {winner_name}</h1>
                    <h2 style="margin: 10px 0 0 0;">Total Score: {winner_total:,} points</h2>
                    <p style="margin: 5px 0 0 0; font-size: 1.2em;">Average: {winner_avg:.1f}/100 across {winner_count} case(s)</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                st.markdown("---")
                st.markdown("### 📊 Complete Rankings")

                # Create columns for medals
                if len(sorted_teams) >= 3:
                    col1, col2, col3 = st.columns(3)

                    for idx, col in enumerate([col1, col2, col3]):
                        if idx < len(sorted_teams):
                            team_name, data = sorted_teams[idx]
                            medal = ["🥇", "🥈", "🥉"][idx]
                            avg_score = (
                                data["total"] / data["count"]
                                if data["count"] > 0
                                else 0
                            )

                            with col:
                                st.markdown(
                                    f"""
                                <div style="background: {'#FFD700' if idx == 0 else '#C0C0C0' if idx == 1 else '#CD7F32'}30; 
                                            padding: 20px; border-radius: 10px; text-align: center;">
                                    <h2 style="margin: 0;">{medal}</h2>
                                    <h3 style="margin: 10px 0;">{team_name}</h3>
                                    <p style="margin: 5px 0; font-size: 1.5em; font-weight: bold;">{data["total"]:,} pts</p>
                                    <p style="margin: 5px 0;">Avg: {avg_score:.1f}/100</p>
                                    <p style="margin: 5px 0; font-size: 0.9em;">{data["count"]} case(s)</p>
                                </div>
                                """,
                                    unsafe_allow_html=True,
                                )

                    st.markdown("---")

                # Detailed standings table
                st.markdown("### 📋 Detailed Standings")

                for idx, (team_name, data) in enumerate(sorted_teams):
                    rank = idx + 1
                    avg_score = (
                        data["total"] / data["count"] if data["count"] > 0 else 0
                    )

                    medal = (
                        "🥇"
                        if rank == 1
                        else ("🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}")
                    )

                    with st.expander(
                        f"{medal} {team_name} - Total: {data['total']:,} pts (Avg: {avg_score:.1f}/100)",
                        expanded=(rank <= 3),
                    ):
                        st.markdown(
                            f"**Cases Completed:** {data['count']}/{len(cases)}"
                        )

                        # Show scores per case
                        case_cols = st.columns(min(5, len(data["cases"])))
                        case_numbers = sorted(data["cases"].keys())

                        for i, case_num in enumerate(case_numbers):
                            col_idx = i % 5
                            with case_cols[col_idx]:
                                score = data["cases"][case_num]
                                score_color = (
                                    "🟢"
                                    if score >= 80
                                    else "🟡" if score >= 60 else "🔴"
                                )
                                st.metric(
                                    label=f"Case {case_num}",
                                    value=f"{score}/100",
                                    delta=f"{score_color}",
                                )

                        # Progress bar
                        completion_rate = (data["count"] / len(cases)) * 100
                        st.progress(data["count"] / len(cases))
                        st.caption(
                            f"Completion: {completion_rate:.0f}% ({data['count']}/{len(cases)} cases)"
                        )

    else:
        # Original case view
        st.sidebar.markdown("Select a case to review:")

        # Create case selection
        case_options = [f"Case {i+1}" for i in range(len(cases))]
        selected_case_idx = st.sidebar.radio(
            "Cases",
            range(len(cases)),
            format_func=lambda x: f"📌 {case_options[x]}: {cases[x]['title'].replace('Case ' + str(x+1) + ':', '').strip()[:30]}...",
        )

        # Display selected case
        selected_case = cases[selected_case_idx]

        st.header(selected_case["title"])

        # Create tabs
        tab1, tab2, tab3 = st.tabs(
            ["📋 Case Description", "💊 Management Considerations", "👥 Team Responses"]
        )

        # Tab 1: Description
        with tab1:
            st.markdown(selected_case["description"])

        # Tab 2: Management
        with tab2:
            st.markdown(selected_case["management"])

        # Tab 3: Team Responses
        with tab3:
            st.subheader("Team Responses & AI Evaluation")

            # Add option to manually test with custom response
            with st.expander("🧪 Test with Custom Response (Optional)"):
                st.markdown(
                    "Enter a response below to get AI evaluation without using Tally API:"
                )
                test_team_name = st.text_input(
                    "Team Name", value="Test Team", key=f"test_team_{selected_case_idx}"
                )
                test_response = st.text_area(
                    "Management Response",
                    height=150,
                    placeholder="Enter the team's management plan here...",
                    key=f"test_response_{selected_case_idx}",
                )
                if st.button(
                    "🤖 Evaluate This Response", key=f"eval_btn_{selected_case_idx}"
                ):
                    if test_response.strip():
                        with st.spinner("AI is evaluating the response..."):
                            evaluation = rate_response_with_gemini(
                                selected_case["description"],
                                selected_case["management"],
                                test_response,
                            )
                        test_data = {
                            "team": test_team_name,
                            "response": test_response,
                            "submitted_at": "2026-02-13 (Manual Test)",
                        }
                        st.markdown("---")
                        display_team_response(test_data["team"], test_data, evaluation)
                    else:
                        st.warning("Please enter a response to evaluate.")

            st.markdown("---")
            st.markdown("### 📊 Tally.so Submissions")

            with st.spinner("Loading team responses from Tally.so..."):
                # Fetch responses
                all_responses = fetch_tally_responses()

                if not all_responses:
                    st.info("No team responses have been submitted yet.")

                else:
                    # Filter responses for current case
                    case_number = selected_case_idx + 1
                    case_responses = categorize_responses_by_case(
                        all_responses, case_number
                    )

                    if not case_responses:
                        st.info(f"No responses found for Case {case_number} yet.")
                    else:
                        st.success(
                            f"Found {len(case_responses)} team response(s) for this case"
                        )

                        # Use session state to track if evaluation is done
                        eval_key = f"evaluated_case_{case_number}"
                        if eval_key not in st.session_state:
                            st.session_state[eval_key] = False
                            st.session_state[f"eval_data_{case_number}"] = []

                        # First show team responses in tabs
                        st.markdown("---")
                        st.markdown("### 📋 Team Responses")

                        tab_names = [
                            response_data["team"] for response_data in case_responses
                        ]
                        tabs = st.tabs(tab_names)

                        for tab, response_data in zip(tabs, case_responses):
                            with tab:
                                st.markdown(f"### 👥 {response_data['team']}")
                                with st.expander("📝 Team Response", expanded=True):
                                    st.markdown(response_data["response"])

                                if response_data.get("submitted_at"):
                                    st.caption(
                                        f"Submitted: {response_data['submitted_at']}"
                                    )

                        # AI Evaluation Section
                        st.markdown("---")
                        st.markdown("### 🤖 AI Evaluation")

                        # Button to trigger evaluation (evaluate all at once)
                        if not st.session_state[eval_key]:
                            st.info(
                                f"💡 Click below to evaluate **all {len(case_responses)} team(s)** at once using AI."
                            )

                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                if st.button(
                                    f"🚀 Evaluate All {len(case_responses)} Team(s) Now",
                                    key=f"eval_btn_{case_number}",
                                    type="primary",
                                    use_container_width=True,
                                ):
                                    evaluated_teams = []

                                    # Show progress
                                    progress_text = st.empty()
                                    progress_bar = st.progress(0)

                                    for idx, response_data in enumerate(case_responses):
                                        progress_text.text(
                                            f"Evaluating {response_data['team']}... ({idx+1}/{len(case_responses)})"
                                        )
                                        progress_bar.progress(
                                            (idx + 1) / len(case_responses)
                                        )

                                        evaluation = rate_response_with_gemini(
                                            selected_case["description"],
                                            selected_case["management"],
                                            response_data["response"],
                                        )
                                        evaluated_teams.append(
                                            {
                                                "team": response_data["team"],
                                                "response_data": response_data,
                                                "evaluation": evaluation,
                                                "score": evaluation["score"],
                                            }
                                        )

                                    # Clear progress indicators
                                    progress_text.empty()
                                    progress_bar.empty()

                                    # Sort by score (highest first)
                                    evaluated_teams.sort(
                                        key=lambda x: x["score"], reverse=True
                                    )

                                    # Store in session state
                                    st.session_state[eval_key] = True
                                    st.session_state[f"eval_data_{case_number}"] = (
                                        evaluated_teams
                                    )
                                    st.rerun()

                        # Display evaluation results if available
                        if st.session_state[eval_key]:
                            evaluated_teams = st.session_state[
                                f"eval_data_{case_number}"
                            ]

                            # Display leaderboard
                            st.success(
                                f"✅ AI evaluation completed for all {len(evaluated_teams)} team(s)!"
                            )
                            st.markdown("### 🏆 Leaderboard")

                            leaderboard_cols = st.columns(min(len(evaluated_teams), 3))
                            for idx, team_data in enumerate(evaluated_teams):
                                col_idx = idx % 3
                                with leaderboard_cols[col_idx]:
                                    medal = (
                                        "🥇"
                                        if idx == 0
                                        else (
                                            "🥈"
                                            if idx == 1
                                            else "🥉" if idx == 2 else "📊"
                                        )
                                    )
                                    st.metric(
                                        label=f"{medal} {team_data['team']}",
                                        value=f"{team_data['score']}/100",
                                    )

                            st.markdown("---")
                            st.markdown(
                                "### 📊 Detailed Evaluation (View One at a Time)"
                            )

                            # Create tabs for each team with scores
                            eval_tab_names = [
                                f"{team_data['team']} ({team_data['score']}/100)"
                                for team_data in evaluated_teams
                            ]
                            eval_tabs = st.tabs(eval_tab_names)

                            # Display each team in its tab with full evaluation
                            for eval_tab, team_data in zip(eval_tabs, evaluated_teams):
                                with eval_tab:
                                    display_team_response(
                                        team_data["team"],
                                        team_data["response_data"],
                                        team_data["evaluation"],
                                    )

                            # Add button to re-evaluate
                            st.markdown("---")
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                if st.button(
                                    "🔄 Re-evaluate All Teams",
                                    key=f"reeval_btn_{case_number}",
                                    use_container_width=True,
                                ):
                                    st.session_state[eval_key] = False
                                    st.session_state[f"eval_data_{case_number}"] = []
                                    st.rerun()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ About")
    st.sidebar.info(
        """
    This application provides:
    - 10 diabetes management cases
    - Evidence-based guidelines
    - Team response tracking
    - AI-powered evaluation using Gemini
    """
    )


if __name__ == "__main__":
    main()
