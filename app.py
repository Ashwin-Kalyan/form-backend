"""
COMPLETE WORKING Flask Backend for Form Submission
Google Sheets + Email sending
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Try to import Google Sheets
try:
    import gspread
    from google.oauth2.service_account import Credentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    print("Note: gspread not installed - Google Sheets disabled")

app = Flask(__name__)
CORS(app)

# Environment variables
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'service': 'Form Submission Backend',
        'features': {
            'email': bool(EMAIL_USER and EMAIL_PASSWORD),
            'google_sheets': bool(GOOGLE_SHEET_KEY and GOOGLE_CREDENTIALS_JSON and SHEETS_AVAILABLE)
        },
        'endpoints': ['/', '/ping', '/health', '/test', '/submit']
    })

@app.route('/ping')
def ping():
    return jsonify({'pong': True, 'time': datetime.now().isoformat()})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/test')
def test():
    """Check environment variables"""
    return jsonify({
        'email_user': 'SET' if EMAIL_USER else 'NOT SET',
        'email_password': 'SET' if EMAIL_PASSWORD else 'NOT SET',
        'google_sheet_key': 'SET' if GOOGLE_SHEET_KEY else 'NOT SET',
        'google_creds_json': 'SET' if GOOGLE_CREDENTIALS_JSON else 'NOT SET',
        'sheets_library': 'AVAILABLE' if SHEETS_AVAILABLE else 'NOT AVAILABLE'
    })

def save_to_google_sheets(data):
    """Save form data to Google Sheets"""
    if not SHEETS_AVAILABLE:
        print("Google Sheets library not available")
        return False
    
    if not GOOGLE_SHEET_KEY:
        print("GOOGLE_SHEET_KEY not set")
        return False
    
    if not GOOGLE_CREDENTIALS_JSON:
        print("GOOGLE_CREDENTIALS_JSON not set")
        return False
    
    try:
        print("Attempting to save to Google Sheets...")
        
        # Parse credentials
        try:
            creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        except json.JSONDecodeError:
            # Try cleaning
            cleaned = GOOGLE_CREDENTIALS_JSON.replace('\\n', '\n').replace('\\"', '"')
            creds_dict = json.loads(cleaned)
        
        # Setup Google Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Open spreadsheet
        spreadsheet = client.open_by_key(GOOGLE_SHEET_KEY)
        worksheet = spreadsheet.sheet1
        
        # Prepare data
        interests = data.get('interests', [])
        interests_str = ', '.join(interests) if isinstance(interests, list) else str(interests)
        
        row = [
            datetime.now().isoformat(),          # Timestamp
            data.get('fullName', ''),            # Full Name
            data.get('gender', ''),              # Gender
            data.get('faculty', ''),             # Faculty
            data.get('desiredPosition', ''),     # Desired Position
            data.get('desiredYear', ''),         # Year
            data.get('email', ''),               # Email
            interests_str,                       # Interests
            data.get('comments', '')             # Comments
        ]
        
        # Add headers if needed
        try:
            existing = worksheet.row_values(1)
            if not existing or existing[0] != 'Timestamp':
                headers = ['Timestamp', 'Full Name', 'Gender', 'Faculty', 'Desired Position',
                          'Year', 'Email', 'Interest', 'Note']
                worksheet.insert_row(headers, 1)
        except:
            pass  # Continue anyway
        
        # Append row
        worksheet.append_row(row)
        print(f"Successfully saved to Google Sheets: {data.get('fullName')}")
        return True
        
    except Exception as e:
        print(f"Google Sheets error: {e}")
        return False

def send_confirmation_email(to_email, name):
    """Send confirmation email"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("Email credentials not set")
        return False
    
    try:
        print(f"Sending email to {to_email}...")
        
        # Email content
        html_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Thank you for visiting our booth!</h2>
            <p>Dear {name},</p>
            <p>We have received your information and will contact you soon.</p>
            <p>Best regards,<br/>Kyowa Technologies</p>
        </div>
        """
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Thank you for visiting our booth"
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"Email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"Email error: {e}")
        return False

@app.route('/submit', methods=['POST', 'OPTIONS'])
def submit_form():
    """Handle form submission"""
    if request.method == 'OPTIONS':
        return '', 200
    
    print("\n=== FORM SUBMISSION ===")
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data'}), 400
        
        print(f"From: {data.get('fullName')}")
        print(f"Email: {data.get('email')}")
        
        # Save to Google Sheets
        sheets_success = False
        if GOOGLE_SHEET_KEY and GOOGLE_CREDENTIALS_JSON and SHEETS_AVAILABLE:
            sheets_success = save_to_google_sheets(data)
        else:
            print("Google Sheets not configured")
        
        # Send email
        email_success = False
        email = data.get('email', '')
        if email and EMAIL_USER and EMAIL_PASSWORD:
            email_success = send_confirmation_email(email, data.get('fullName', 'User'))
        else:
            print("Email not configured or no email provided")
        
        response = {
            'success': True,
            'message': 'Form submitted successfully',
            'sheets_saved': sheets_success,
            'email_sent': email_success
        }
        
        print(f"Response: {response}")
        print("====================\n")
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print(f"\nStarting server on port {port}")
    print(f"Email configured: {'YES' if EMAIL_USER else 'NO'}")
    print(f"Sheets configured: {'YES' if GOOGLE_SHEET_KEY and GOOGLE_CREDENTIALS_JSON else 'NO'}")
    app.run(host='0.0.0.0', port=port, debug=False)