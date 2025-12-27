# Backend Setup Instructions

This backend handles Google Sheets integration and email sending for the registration form.

## Prerequisites

1. Python 3.8 or higher
2. Google Cloud Project with Google Sheets API enabled
3. Gmail account with App Password enabled (for email sending)

## Installation

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

## Configuration

### 1. Google Sheets Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API and Google Drive API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "sheets-service")
   - Click "Create and Continue"
   - Skip role assignment, click "Done"
5. Create a key for the service account:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the JSON file and save it as `credentials.json` in the `backend/` directory
6. Create a Google Sheet:
   - Create a new Google Sheet
   - Share it with the service account email (found in credentials.json, looks like `xxx@xxx.iam.gserviceaccount.com`)
   - Give it "Editor" permissions
   - Copy the Sheet ID from the URL (the long string between `/d/` and `/edit`)
   - Example URL: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
   - The `SHEET_ID_HERE` is your `GOOGLE_SHEET_KEY`

### 2. Gmail Setup (for email sending)

1. Go to your Google Account settings
2. Enable 2-Step Verification
3. Generate an App Password:
   - Go to "Security" > "2-Step Verification" > "App passwords"
   - Select "Mail" and "Other (Custom name)"
   - Enter "Nortiq Forms" as the name
   - Click "Generate"
   - Copy the 16-character password (this is your `EMAIL_PASSWORD`)

### 3. Environment Variables

Create a `.env` file in the `backend/` directory with the following:

```env
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-16-character-app-password
GOOGLE_SHEET_KEY=your-google-sheet-id-from-url
GOOGLE_CREDENTIALS_PATH=credentials.json
PORT=5001
```

**Important**: 
- `EMAIL_PASSWORD` should be the App Password, NOT your regular Gmail password
- `GOOGLE_SHEET_KEY` is the Sheet ID from the Google Sheets URL
- Make sure `credentials.json` is in the `backend/` directory

## Running the Backend

```bash
cd backend
python app.py
```

The server will start on `http://localhost:5001` (or the port specified in your .env file).

## Testing

You can test if the backend is running by visiting:
```
http://localhost:5001/health
```

You should see: `{"status":"ok"}`

## Troubleshooting

### Backend not connecting
- Make sure the backend is running (`python backend/app.py`)
- Check that the port matches in both `.env` files (frontend and backend)
- Check browser console for CORS errors

### Google Sheets not working
- Verify `credentials.json` is in the `backend/` directory
- Check that the service account email has access to the Google Sheet
- Verify `GOOGLE_SHEET_KEY` is correct (the Sheet ID from the URL)
- Check backend console for error messages

### Email not sending
- Verify `EMAIL_USER` and `EMAIL_PASSWORD` are correct
- Make sure you're using an App Password, not your regular password
- Check that 2-Step Verification is enabled on your Google Account
- Check backend console for SMTP error messages

