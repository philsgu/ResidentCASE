import streamlit as st
import re
import requests
from typing import Dict, List
import os

# Configure API Keys from Streamlit secrets
# For local development: .streamlit/secrets.toml
# For Streamlit Cloud: Add secrets in dashboard Settings > Secrets
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    TALLY_API_KEY = st.secrets.get("TALLY_API_KEY", "")
    TALLY_FORM_ID = st.secrets.get("TALLY_FORM_ID", "b5xGbZ")
    USE_TALLY_API = st.secrets.get("USE_TALLY_API", True)
except Exception as e:
    # Fallback to environment variables if secrets not available
    st.warning("⚠️ Secrets not configured. Using environment variables or demo mode.")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
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

        # Split by "Management Considerations:" to separate description from management
        parts = re.split(r"\*\*Management Considerations:\*\*", block, maxsplit=1)

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
    """Use Gemini API to rate and score a team's response"""
    try:
        prompt = f"""You are an expert medical educator evaluating resident physicians' case management responses.

**Case Background:**
{case_description}

**REFERENCE ANSWER - Evidence-Based Management Considerations:**
{management_guideline}

**Team's Response:**
{team_response}

EVALUATION INSTRUCTIONS:
Score the team's response (0-100) based SPECIFICALLY on how well it aligns with the Management Considerations listed above. The score should reflect:
- Coverage of key management points mentioned in the reference (40 points)
- Accuracy and appropriateness of recommendations (30 points)
- Clinical reasoning and safety considerations (20 points)
- Completeness and organization (10 points)

Compare the team's response directly against each point in the Management Considerations. Award higher scores for responses that address most or all of the reference points with appropriate clinical reasoning.

Provide:
1. **Overall Score** (0-100): Based on alignment with Management Considerations
2. **Strengths**: Specific management points they correctly addressed from the reference (bullet points)
3. **Areas for Improvement**: How they could better align with the reference guidelines (bullet points)
4. **Key Points Missed**: Management considerations from the reference that they did not address (bullet points)
5. **Clinical Reasoning**: Assessment of their reasoning in relation to evidence-based guidelines (2-3 sentences)

Format your response as:
SCORE: [number]
STRENGTHS:
- [point 1]
- [point 2]
...

AREAS FOR IMPROVEMENT:
- [point 1]
- [point 2]
...

KEY POINTS MISSED:
- [point 1]
- [point 2]
...

CLINICAL REASONING:
[Your assessment]
"""

        # Use Gemini REST API directly with v1 endpoint
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        evaluation_text = result["candidates"][0]["content"]["parts"][0]["text"]

        # Parse the response
        score_match = re.search(r"SCORE:\s*(\d+)", evaluation_text)
        score = int(score_match.group(1)) if score_match else 0

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
        improvements = improvements_match.group(1).strip() if improvements_match else ""

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
            "strengths": strengths,
            "improvements": improvements,
            "missed_points": missed,
            "clinical_reasoning": reasoning,
            "full_evaluation": evaluation_text,
        }

    except Exception as e:
        st.error(f"Error rating response: {e}")
        return {
            "score": 0,
            "strengths": "Error occurred during evaluation",
            "improvements": "",
            "missed_points": "",
            "clinical_reasoning": "",
            "full_evaluation": f"Error: {e}",
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
    st.sidebar.title("📋 Case Navigation")
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
                # Show sample/demo response
                st.markdown("### 📝 Demo Mode - Sample Responses")
                st.info(
                    "Showing sample team responses for demonstration purposes. Use the 'Test with Custom Response' section above to evaluate actual responses."
                )

                # Generate demo responses relevant to the case
                demo_responses = [
                    {
                        "team": "Demo Team Alpha",
                        "response": """For this patient, I would:
1. Start with Metformin 500mg twice daily as first-line therapy
2. Implement lifestyle modifications including diet and exercise
3. Schedule follow-up in 3 months to reassess HbA1c
4. Consider referral to diabetes education
5. Monitor for complications""",
                        "submitted_at": "2026-02-13",
                    },
                    {
                        "team": "Demo Team Beta",
                        "response": """My management approach:
- Initiate metformin and titrate to maximum tolerated dose
- Refer to DSMES for comprehensive education
- Consider adding GLP-1 RA if cardiovascular disease present
- Implement evidence-based lifestyle interventions
- Monitor HbA1c quarterly, adjust therapy as needed""",
                        "submitted_at": "2026-02-13",
                    },
                ]

                # First, display all demo team responses immediately
                st.markdown("---")
                st.markdown("### 📋 Demo Team Responses")

                # Create tabs for each team (without scores initially)
                tab_names = [demo["team"] for demo in demo_responses]
                tabs = st.tabs(tab_names)

                # Display each team's response in its tab
                for tab, demo_response in zip(tabs, demo_responses):
                    with tab:
                        st.markdown(f"### 👥 {demo_response['team']}")
                        with st.expander("📝 Team Response", expanded=True):
                            st.markdown(demo_response["response"])

                        if demo_response.get("submitted_at"):
                            st.caption(f"Submitted: {demo_response['submitted_at']}")

                # AI Evaluation Section
                st.markdown("---")
                st.markdown("### 🤖 AI Evaluation")

                # Use session state for demo evaluation
                demo_eval_key = f"demo_evaluated_case_{selected_case_idx}"
                if demo_eval_key not in st.session_state:
                    st.session_state[demo_eval_key] = False
                    st.session_state[f"demo_eval_data_{selected_case_idx}"] = []

                # Button to trigger evaluation
                if not st.session_state[demo_eval_key]:
                    st.info(
                        f"💡 Click below to evaluate **all {len(demo_responses)} demo team(s)** at once using AI."
                    )

                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button(
                            f"🚀 Evaluate All {len(demo_responses)} Team(s) Now",
                            key=f"demo_eval_btn_{selected_case_idx}",
                            type="primary",
                            use_container_width=True,
                        ):
                            evaluated_teams = []

                            # Show progress
                            progress_text = st.empty()
                            progress_bar = st.progress(0)

                            for idx, demo_response in enumerate(demo_responses):
                                progress_text.text(
                                    f"Evaluating {demo_response['team']}... ({idx+1}/{len(demo_responses)})"
                                )
                                progress_bar.progress((idx + 1) / len(demo_responses))

                                evaluation = rate_response_with_gemini(
                                    selected_case["description"],
                                    selected_case["management"],
                                    demo_response["response"],
                                )
                                evaluated_teams.append(
                                    {
                                        "team": demo_response["team"],
                                        "response_data": demo_response,
                                        "evaluation": evaluation,
                                        "score": evaluation["score"],
                                    }
                                )

                            # Clear progress indicators
                            progress_text.empty()
                            progress_bar.empty()

                            # Sort by score
                            evaluated_teams.sort(key=lambda x: x["score"], reverse=True)

                            # Store in session state
                            st.session_state[demo_eval_key] = True
                            st.session_state[f"demo_eval_data_{selected_case_idx}"] = (
                                evaluated_teams
                            )
                            st.rerun()

                # Display evaluation results if available
                if st.session_state[demo_eval_key]:
                    evaluated_teams = st.session_state[
                        f"demo_eval_data_{selected_case_idx}"
                    ]

                    # Display leaderboard
                    st.success(
                        f"✅ AI evaluation completed for all {len(evaluated_teams)} team(s)!"
                    )
                    st.markdown("### 🏆 Leaderboard")

                    leaderboard_cols = st.columns(len(evaluated_teams))
                    for idx, team_data in enumerate(evaluated_teams):
                        with leaderboard_cols[idx]:
                            medal = "🥇" if idx == 0 else "🥈"
                            st.metric(
                                label=f"{medal} {team_data['team']}",
                                value=f"{team_data['score']}/100",
                            )

                    st.markdown("---")
                    st.markdown("### 📊 Detailed Evaluation (View One at a Time)")

                    # Create tabs for each team with scores
                    eval_tab_names = [
                        f"{team_data['team']} ({team_data['score']}/100)"
                        for team_data in evaluated_teams
                    ]
                    eval_tabs = st.tabs(eval_tab_names)

                    # Display each team in its tab
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
                            key=f"demo_reeval_btn_{selected_case_idx}",
                            use_container_width=True,
                        ):
                            st.session_state[demo_eval_key] = False
                            st.session_state[f"demo_eval_data_{selected_case_idx}"] = []
                            st.rerun()

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
                        evaluated_teams = st.session_state[f"eval_data_{case_number}"]

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
                                        "🥈" if idx == 1 else "🥉" if idx == 2 else "📊"
                                    )
                                )
                                st.metric(
                                    label=f"{medal} {team_data['team']}",
                                    value=f"{team_data['score']}/100",
                                )

                        st.markdown("---")
                        st.markdown("### 📊 Detailed Evaluation (View One at a Time)")

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

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📝 Submit Responses")
    st.sidebar.markdown("Teams can submit their case responses at:")
    st.sidebar.markdown("[**Tally Form Link**](https://tally.so/r/b5xGbZ)")
    st.sidebar.caption(
        "Form fields: Team Number, Team Name, Case, Management, Additional Tests/Labs"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 API Status")
    st.sidebar.markdown(
        f"**Tally API**: {'✅ Enabled' if USE_TALLY_API else '⚠️ Disabled (Demo Mode)'}"
    )
    st.sidebar.markdown("**Gemini AI**: ✅ Active")

    if USE_TALLY_API:
        st.sidebar.caption("Having API issues? Set USE_TALLY_API = False in app.py")


if __name__ == "__main__":
    main()
