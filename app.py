"""
Simple Python Flask backend for form submission
Handles Google Sheets and email sending
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

# Try to import Google Sheets libraries, but handle errors gracefully
try:
    import gspread
    from google.oauth2.service_account import Credentials
    SHEETS_AVAILABLE = True
except Exception as e:
    print(f"Warning: Google Sheets libraries not available: {e}")
    print("The server will start, but Google Sheets integration will be disabled.")
    SHEETS_AVAILABLE = False
    gspread = None
    Credentials = None

load_dotenv()

app = Flask(__name__)
# Allow CORS from Vercel frontend and localhost for development
# For production, you may want to restrict this to specific domains
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins for now

# Google Sheets setup
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Email configuration (using Gmail SMTP)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")  # App password, not regular password
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

def get_sheet():
    """Connect to Google Sheets"""
    if not SHEETS_AVAILABLE:
        print("Google Sheets libraries not available - skipping Sheets integration")
        return None
    try:
        # Try JSON string first (for Render/cloud deployments)
        if GOOGLE_CREDENTIALS_JSON:
            import json
            try:
                # Try parsing as JSON string
                credentials_data = json.loads(GOOGLE_CREDENTIALS_JSON)
                creds = Credentials.from_service_account_info(credentials_data, scopes=SCOPE)
                print("Using credentials from GOOGLE_CREDENTIALS_JSON environment variable")
            except json.JSONDecodeError:
                # Try base64 decode if it's base64 encoded
                import base64
                try:
                    decoded = base64.b64decode(GOOGLE_CREDENTIALS_JSON).decode('utf-8')
                    credentials_data = json.loads(decoded)
                    creds = Credentials.from_service_account_info(credentials_data, scopes=SCOPE)
                    print("Using credentials from base64-decoded GOOGLE_CREDENTIALS_JSON")
                except Exception as e:
                    print(f"Error parsing GOOGLE_CREDENTIALS_JSON: {e}")
                    return None
        else:
            # Fall back to file path (for local development)
            creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPE)
            print(f"Using credentials from file: {GOOGLE_CREDENTIALS_PATH}")
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_KEY).sheet1
        return sheet
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return None

def send_email(to_email, name):
    """Send confirmation email"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("=" * 50)
        print("ERROR: Email credentials not configured!")
        print("Please set EMAIL_USER and EMAIL_PASSWORD in backend/.env file")
        print("Make sure EMAIL_PASSWORD is an App Password, not your regular Gmail password")
        print("=" * 50)
        return False
    
    try:
        subject = "本日のブース訪問、ありがとうございます / Thanks for visiting our booth today!"
        
        html_body = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="margin-bottom: 30px;">
                <h2 style="color: #333; margin-bottom: 15px;">本日のブース訪問、ありがとうございます。</h2>
                
                <p>貴方のご回答、確かに拝見しました。</p>
                <p>担当者より改めてご連絡いたします。</p>
                
                <p style="margin-top: 20px;">私たちは日本で、決して止まってはいけない社会インフラを支える通信技術に取り組んでいます。</p>
                
                <p>日本で学び、経験を積み、将来その力をタイで活かしたい方との出会いを楽しみにしています。</p>
                
                <div style="margin-top: 30px;">
                    <p style="margin-bottom: 5px;"><strong>CEO 十河元太郎</strong></p>
                    <p style="margin-bottom: 5px;"><strong>協和テクノロジィズ株式会社</strong></p>
                    <p style="margin-bottom: 5px;">採用専用メールアドレス: <a href="mailto:r-hirata@star.kyotec.co.jp">r-hirata@star.kyotec.co.jp</a></p>
                </div>
            </div>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
            
            <div>
                <h2 style="color: #333; margin-bottom: 15px;">Dear All,</h2>
                
                <p><strong>Thanks for visiting our booth today!</strong></p>
                <p><strong>we'll be in touch soon!</strong></p>
                
                <p style="margin-top: 20px;">Our mission is engineering the critical communication technologies that keep essential infrastructure running in Japan.</p>
                
                <p><strong>Join us in Japan and grow with us!</strong></p>
                <p><strong>We guide you and we learn together!</strong></p>
                
                <div style="margin-top: 30px;">
                    <p style="margin-bottom: 5px;">Yours sincerely,</p>
                    <p style="margin-bottom: 5px;"><strong>Gentaro Sogo</strong></p>
                    <p style="margin-bottom: 5px;"><strong>CEO Kyowa Technologies Co., Ltd.</strong></p>
                    <p style="margin-bottom: 5px;">Continued contact: <a href="mailto:r-hirata@star.kyotec.co.jp">r-hirata@star.kyotec.co.jp</a></p>
                </div>
            </div>
        </div>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print("=" * 50)
        print(f"ERROR: SMTP Authentication failed!")
        print(f"Details: {e}")
        print("This usually means:")
        print("1. EMAIL_PASSWORD is incorrect (make sure it's an App Password, not your regular password)")
        print("2. 2-Step Verification is not enabled on your Google Account")
        print("3. App Password was not generated correctly")
        print("=" * 50)
        return False
    except smtplib.SMTPException as e:
        print("=" * 50)
        print(f"ERROR: SMTP error occurred!")
        print(f"Details: {e}")
        print("=" * 50)
        return False
    except Exception as e:
        print("=" * 50)
        print(f"ERROR: Failed to send email to {to_email}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e}")
        print("=" * 50)
        return False

@app.route('/submit', methods=['POST', 'OPTIONS'])
def submit_form():
    """Handle form submission"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        return '', 200
    
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data received'
            }), 400
        
        print(f"Received form submission: {data.get('fullName', 'Unknown')} - {data.get('email', 'No email')}")
        
        # Prepare row data for Google Sheets
        interests_str = ', '.join(data.get('interests', [])) if isinstance(data.get('interests'), list) else data.get('interests', '')
        
        row_data = [
            datetime.now().isoformat(),  # Timestamp
            data.get('fullName', ''),  # Full Name
            data.get('gender', ''),
            data.get('faculty', ''),
            data.get('desiredPosition', ''),  # Desired Position
            data.get('desiredYear', ''),  # Year
            data.get('email', ''),
            interests_str,  # Interest
            data.get('comments', ''),  # Note
        ]
        
        # Write to Google Sheets
        sheet = get_sheet()
        sheets_success = False
        if sheet:
            try:
                # Define correct headers
                headers = [
                    'Timestamp',
                    'Full Name',
                    'Gender',
                    'Faculty',
                    'Desired Position',
                    'Year',
                    'Email',
                    'Interest',
                    'Note'
                ]
                
                # Check if headers exist and are correct
                if sheet.row_count == 0:
                    # Sheet is empty, add headers
                    sheet.append_row(headers)
                    print("Added headers to Google Sheet")
                elif sheet.cell(1, 1).value != 'Timestamp' or sheet.cell(1, 2).value != 'Full Name':
                    # Headers don't match or don't exist, update row 1
                    sheet.update('A1:I1', [headers])
                    print("Updated headers in Google Sheet")
                
                sheet.append_row(row_data)
                sheets_success = True
                print(f"Successfully wrote data to Google Sheets for {data.get('fullName', 'Unknown')}")
            except Exception as e:
                print(f"Error writing to Google Sheets: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("WARNING: Could not connect to Google Sheets - check credentials")
        
        # Send confirmation email
        email = data.get('email', '')
        name = data.get('fullName', 'User')
        email_success = False
        if email:
            email_result = send_email(email, name)
            if email_result:
                email_success = True
                print(f"Successfully sent confirmation email to {email}")
            else:
                print(f"WARNING: Failed to send email to {email}. Check email configuration and server logs.")
        else:
            print("WARNING: No email address provided in submission")
        
        # Return success even if one operation failed (graceful degradation)
        return jsonify({
            'success': True,
            'message': 'Form submitted successfully',
            'sheets_saved': sheets_success,
            'email_sent': email_success
        }), 200
        
    except Exception as e:
        print(f"Error processing submission: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))  # Use 5001 to avoid macOS AirPlay conflict
    app.run(debug=True, port=port, host='0.0.0.0')

