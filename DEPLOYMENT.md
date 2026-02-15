# Streamlit Cloud Deployment Guide

## Overview
This app reads diabetes case management scenarios and evaluates team responses using AI (Gemini).

## Local Development

1. **Install dependencies:**
   ```bash
   uv sync
   # or
   pip install -r requirements.txt
   ```

2. **Configure secrets:**
   - Secrets are stored in `.streamlit/secrets.toml` (already created)
   - This file is gitignored and won't be committed

3. **Run locally:**
   ```bash
   streamlit run app.py
   # or with uv
   uv run streamlit run app.py
   ```

## Deploying to Streamlit Cloud

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Click "New app"
3. Select your GitHub repository
4. Set main file path: `app.py`
5. Click "Advanced settings" → "Secrets"

### Step 3: Add Secrets to Streamlit Cloud

In the Secrets section, paste the following (update with your actual keys):

```toml
GEMINI_API_KEY = "AIzaSyCR98gDlOytcvC5lJ2KUq5JOa0ttUWml4w"
TALLY_API_KEY = "tly-CPlerdeNW8G9901xIt7ImuvN6pmBtCRI"
TALLY_FORM_ID = "b5xGbZ"
USE_TALLY_API = true
```

6. Click "Save"
7. Click "Deploy"

## Required Files

- ✅ `app.py` - Main application
- ✅ `cases.md` - Case data
- ✅ `requirements.txt` - Python dependencies
- ✅ `.streamlit/secrets.toml` - Local secrets (gitignored)
- ✅ `.gitignore` - Excludes secrets from git

## API Keys

### Gemini API Key
- Get your key at: https://makersuite.google.com/app/apikey
- Free tier available

### Tally.so API Key
- Get your key at: https://tally.so/
- Navigate to: Settings → Integrations → API
- Generate API token with form read access

## Features

- 📋 10 diabetes case scenarios
- 💊 Evidence-based management guidelines
- 👥 Team response tracking via Tally.so
- 🤖 AI-powered evaluation using Gemini
- 🏆 Automatic leaderboard and scoring

## Support

For issues or questions, check the Streamlit Community: https://discuss.streamlit.io/
