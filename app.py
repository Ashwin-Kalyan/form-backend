"""
COMPLETE WORKING Flask Backend for Form Submission
Uses Secret File: /etc/secrets/credentials.json
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

# Credentials file path - Render Secret Files location
CREDENTIALS_FILE_PATH = "/etc/secrets/credentials.json"

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'service': 'Form Submission Backend',
        'config': {
            'email': bool(EMAIL_USER and EMAIL_PASSWORD),
            'google_sheets': bool(GOOGLE_SHEET_KEY),
            'credentials_file': 'Using file path',
            'credentials_path': CREDENTIALS_FILE_PATH,
            'file_exists': os.path.exists(CREDENTIALS_FILE_PATH) if SHEETS_AVAILABLE else 'N/A'
        },
        'endpoints': ['/', '/ping', '/health', '/test', '/debug', '/submit']
    })

@app.route('/ping')
def ping():
    return jsonify({'pong': True, 'time': datetime.now().isoformat()})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/test')
def test():
    """Check configuration"""
    creds_file_exists = os.path.exists(CREDENTIALS_FILE_PATH) if SHEETS_AVAILABLE else False
    
    return jsonify({
        'email_user': 'SET' if EMAIL_USER else 'NOT SET',
        'email_password': 'SET' if EMAIL_PASSWORD else 'NOT SET',
        'google_sheet_key': 'SET' if GOOGLE_SHEET_KEY else 'NOT SET',
        'credentials_file': 'EXISTS' if creds_file_exists else 'NOT FOUND',
        'credentials_path': CREDENTIALS_FILE_PATH,
        'sheets_library': 'AVAILABLE' if SHEETS_AVAILABLE else 'NOT AVAILABLE'
    })

@app.route('/debug')
def debug():
    """Debug credentials file"""
    debug_info = {
        'credentials_path': CREDENTIALS_FILE_PATH,
        'file_exists': os.path.exists(CREDENTIALS_FILE_PATH),
        'sheets_available': SHEETS_AVAILABLE
    }
    
    if os.path.exists(CREDENTIALS_FILE_PATH):
        try:
            with open(CREDENTIALS_FILE_PATH, 'r') as f:
                content = f.read()
                debug_info['file_size'] = len(content)
                debug_info['file_readable'] = True
                
                # Try to parse as JSON
                try:
                    creds = json.loads(content)
                    debug_info['json_valid'] = True
                    debug_info['service_account'] = creds.get('client_email', 'Not found')
                    debug_info['project_id'] = creds.get('project_id', 'Not found')
                except json.JSONDecodeError as e:
                    debug_info['json_valid'] = False
                    debug_info['json_error'] = str(e)
                    
        except Exception as e:
            debug_info['file_readable'] = False
            debug_info['file_error'] = str(e)
    else:
        debug_info['file_exists'] = False
    
    return jsonify(debug_info)

def load_credentials():
    """Load credentials from file"""
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        print(f"❌ Credentials file not found at: {CREDENTIALS_FILE_PATH}")
        return None
    
    try:
        with open(CREDENTIALS_FILE_PATH, 'r') as f:
            credentials = json.load(f)
        
        print(f"✅ Loaded credentials for: {credentials.get('client_email', 'Unknown')}")
        return credentials
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse credentials JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return None

def save_to_google_sheets(data):
    """Save form data to Google Sheets using credentials file"""
    if not SHEETS_AVAILABLE:
        print("❌ Google Sheets library not available")
        return False
    
    if not GOOGLE_SHEET_KEY:
        print("❌ GOOGLE_SHEET_KEY not set")
        return False
    
    try:
        print("📊 Attempting to save to Google Sheets...")
        print(f"📁 Using credentials file: {CREDENTIALS_FILE_PATH}")
        
        # Load credentials from file
        credentials_dict = load_credentials()
        if not credentials_dict:
            return False
        
        print(f"✅ Service Account: {credentials_dict.get('client_email', 'Unknown')}")
        
        # Setup Google Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Open spreadsheet
        spreadsheet = client.open_by_key(GOOGLE_SHEET_KEY)
        worksheet = spreadsheet.sheet1
        
        # Prepare data
        interests = data.get('interests', [])
        if isinstance(interests, list):
            interests_str = ', '.join(interests)
        else:
            interests_str = str(interests) if interests else ''
        
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
                headers = ['Timestamp', 'Full Name', 'Gender', 'Faculty', 
                          'Desired Position', 'Year', 'Email', 'Interest', 'Note']
                worksheet.insert_row(headers, 1)
                print("✅ Added headers to sheet")
        except Exception as e:
            print(f"⚠️ Error checking headers: {e}")
            # Continue anyway
        
        # Append row
        worksheet.append_row(row)
        print(f"✅ Successfully saved to Google Sheets: {data.get('fullName', 'Unknown')}")
        return True
        
    except Exception as e:
        print(f"❌ Google Sheets Error: {type(e).__name__}: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

def send_confirmation_email(to_email, name):
    """Send confirmation email"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("❌ Email credentials not configured")
        return False
    
    try:
        print(f"📧 Attempting to send email to {to_email}...")
        
        # Email content
        subject = "本日のブース訪問、ありがとうございます / Thanks for visiting our booth today!"
        
        html_content = f"""
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
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP Authentication failed! Check your App Password")
        return False
    except Exception as e:
        print(f"❌ Email error: {type(e).__name__}: {e}")
        return False

@app.route('/submit', methods=['POST', 'OPTIONS'])
def submit_form():
    """Handle form submission - MAIN ENDPOINT"""
    if request.method == 'OPTIONS':
        # CORS preflight
        return '', 200
    
    print("\n" + "="*60)
    print("📝 FORM SUBMISSION RECEIVED")
    print("="*60)
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        print(f"👤 Name: {data.get('fullName', 'Unknown')}")
        print(f"📧 Email: {data.get('email', 'No email')}")
        
        # Save to Google Sheets
        sheets_success = False
        if GOOGLE_SHEET_KEY and SHEETS_AVAILABLE:
            sheets_success = save_to_google_sheets(data)
        else:
            print("⚠️ Google Sheets not configured or library missing")
        
        # Send confirmation email
        email_success = False
        email = data.get('email', '')
        name = data.get('fullName', 'User')
        
        if email:
            if EMAIL_USER and EMAIL_PASSWORD:
                email_success = send_confirmation_email(email, name)
            else:
                print("⚠️ Email credentials not configured")
        else:
            print("⚠️ No email address provided")
        
        # Return response
        response = {
            'success': True,
            'message': 'Form submitted successfully',
            'sheets_saved': sheets_success,
            'email_sent': email_success,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"✅ Response: {response}")
        print("="*60 + "\n")
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print("\n" + "="*60)
    print(f"🚀 Starting Form Backend on port {port}")
    print(f"📧 Email: {'CONFIGURED' if EMAIL_USER and EMAIL_PASSWORD else 'NOT CONFIGURED'}")
    print(f"📊 Sheets Key: {'SET' if GOOGLE_SHEET_KEY else 'NOT SET'}")
    print(f"📁 Credentials File: {CREDENTIALS_FILE_PATH}")
    print(f"📁 File Exists: {os.path.exists(CREDENTIALS_FILE_PATH)}")
    print(f"📚 Sheets Library: {'AVAILABLE' if SHEETS_AVAILABLE else 'MISSING'}")
    print("="*60 + "\n")
    
    # For Render deployment
    app.run(host='0.0.0.0', port=port, debug=False)