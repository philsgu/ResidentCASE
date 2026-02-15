# Tally.so API Setup Guide

## Current Status
✅ API Key is valid  
✅ Form ID is correct: `b5xGbZ` (Team Based Case Discussion - 1 submission)  
❌ API Key lacks **"Read form responses"** permission

## Problem
The current API key can list forms but cannot read form responses. You'll see:
```
Error: 401 Unauthorized when accessing responses
```

## Solution: Generate API Key with Correct Permissions

### Step-by-Step Instructions

1. **Log in to Tally.so**
   - Go to https://tally.so/
   - Sign in to your workspace

2. **Navigate to API Settings**
   - Click on your profile/workspace name
   - Go to: **Settings** → **Integrations** → **API**

3. **Create New API Token**
   - Click **"Generate new token"** or **"Create API key"**
   - Give it a name like "ResidentCASE Response Reader"
   - **IMPORTANT**: Check the box for **"Read form responses"** permission
   - Copy the generated key immediately (it won't be shown again)

4. **Update app.py**
   - Open `app.py`
   - Find line ~17: `TALLY_API_KEY = "tly-..."`
   - Replace with your new key
   - Change line ~21: `USE_TALLY_API = False` to `USE_TALLY_API = True`
   - Save and restart the Streamlit app

### Option 2: Use Demo Mode

If you don't need real Tally responses right now, you can disable the API:

1. Open `app.py`
2. Find line ~21: `USE_TALLY_API = True`
3. Change to: `USE_TALLY_API = False`
4. Save and restart

This will:
- ✅ Show sample demo responses
- ✅ Still use AI evaluation
- ✅ Allow manual response testing

### Option 3: Manual Response Testing

The app now includes a "Test with Custom Response" section where you can:
- Enter a team name
- Paste a response
- Get AI evaluation immediately
- No API needed!

## Verifying Your API Key

Test if your API key works:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  https://api.tally.so/forms/b5xGbZ/responses
```

**Note**: Form ID is `b5xGbZ` (capital Z) - it's case-sensitive!

If it works, you'll see JSON response data. If not, you'll see an error.

## Common Issues

### 401 Unauthorized
- **Most Common**: API key doesn't have "Read form responses" permission
- API key is invalid or expired
- Wrong authentication format

### 404 Not Found
- Form ID is wrong or case-sensitive mismatch (use `b5xGbZ` not `b5xGbz`)
- Form doesn't exist or isn't accessible

### No Responses Showing
- Form hasn't received any submissions yet
- Responses exist but aren't matching case numbers
- Check that your Tally form has a field for "case number" (1-10)

## Required Tally Form Structure

For the app to categorize responses correctly, your Tally form should have:

1. **Case Number Field**: Dropdown or number input (values 1-10)
   - Field label should contain "case" or "case number"

2. **Team Name Field**: Text input
   - Field label should contain "team" or "group"

3. **Response Field**: Long text area
   - Field label should contain "response", "answer", or "management"

## Need Help?

- Check Tally.so documentation: https://tally.so/help/integrations
- Use the manual testing feature in the app (no API needed)
- Contact your Tally workspace admin for API access
