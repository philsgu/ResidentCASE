# Resident CASE - Streamlit Application Instructions

## Overview
This Streamlit application provides an interactive platform for reviewing diabetes management cases with AI-powered evaluation of team responses.

## Features
1. **10 Diabetes Cases**: Extracted and parsed from cases.txt
2. **Left Sidebar Navigation**: Menu-based links for easy case selection
3. **Three Tabs per Case**:
   - **Tab 1**: Case Description (Patient Presentation, Medications, Lab Results)
   - **Tab 2**: Management Considerations (Evidence-based guidelines)
   - **Tab 3**: Team Responses (Fetched from Tally.so and evaluated by Gemini AI)

## Running the Application

### Using uv (recommended for this project):
```bash
uv run streamlit run app.py
```

### Alternative (if uv is not available):
```bash
streamlit run app.py
```

## API Configuration

The application uses:
- **Tally.so API**: Form ID `b5xGbz` for fetching team responses
- **Gemini AI API**: For rating and scoring team responses

API keys are already configured in the app:
- Tally API Key: `tly-CPlerdeNW8G9901xIt7ImuvN6pmBtCRI`
- Gemini API Key: `AIzaSyCR98gDlOytcvC5lJ2KUq5JOa0ttUWml4w`

## How It Works

### Team Response Evaluation
1. The app fetches responses from Tally.so
2. Responses are categorized by case number
3. Each response is sent to Gemini AI for evaluation
4. AI provides:
   - Overall score (0-100)
   - Strengths identified
   - Areas for improvement
   - Key points missed
   - Clinical reasoning assessment

### Response Format Expected from Tally Form
The app looks for these fields in Tally responses:
- **Case Number**: Field containing case number (1-10)
- **Team Name**: Field identifying the team
- **Response**: Team's management plan or answer

## Troubleshooting

### No Responses Showing
If no team responses appear, the app will:
- Display a demo response with AI evaluation
- Show helpful information about possible causes

### Case Parsing Issues
Ensure `cases.txt` is in the same directory as `app.py`

## Project Structure
```
ResidentCASE/
├── app.py              # Main Streamlit application
├── cases.txt           # Diabetes management cases
├── pyproject.toml      # Project dependencies
├── INSTRUCTIONS.md     # This file
└── README.md          # Project readme
```

## Dependencies
- streamlit >= 1.54.0
- google-generativeai >= 0.8.6
- requests >= 2.31.0

These are automatically installed when running `uv sync` or `pip install -e .`
