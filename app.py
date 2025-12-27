"""
COMPLETE WORKING Flask Backend for Form Submission
FINAL PATH: /etc/secrets/nortiq-forms-65b5a63e6217.json
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

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

# FINAL credentials file path - EXACT PATH
CREDENTIALS_FILE_PATH = "/etc/secrets/nortiq-forms-65b5a63e6217.json"

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'service': 'Form Submission Backend - FINAL',
        'config': {
            'email': bool(EMAIL_USER and EMAIL_PASSWORD),
            'google_sheets': bool(GOOGLE_SHEET_KEY),
            'credentials_file': 'nortiq-forms-65b5a63e6217.json',
            'credentials_path': CREDENTIALS_FILE_PATH,
            'file_exists': os.path.exists(CREDENTIALS_FILE_PATH) if SHEETS_AVAILABLE else 'N/A',
            'sheets_library': 'AVAILABLE' if SHEETS_AVAILABLE else 'NOT AVAILABLE'
        },
        'endpoints': ['/', '/ping', '/health', '/test', '/debug', '/check-creds', '/submit']
    })

@app.route('/ping')
def ping():
    return jsonify({'pong': True, 'time': datetime.now().isoformat(), 'timestamp': time.time()})

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
        'credentials_file': 'nortiq-forms-65b5a63e6217.json',
        'credentials_path': CREDENTIALS_FILE_PATH,
        'file_exists': creds_file_exists,
        'file_exists_detail': 'YES' if creds_file_exists else 'NO - Check Render Secret Files',
        'sheets_library': 'AVAILABLE' if SHEETS_AVAILABLE else 'NOT AVAILABLE',
        'server_time': datetime.now().isoformat()
    })

@app.route('/debug')
def debug():
    """Debug credentials file"""
    debug_info = {
        'credentials_file': 'nortiq-forms-65b5a63e6217.json',
        'credentials_path': CREDENTIALS_FILE_PATH,
        'file_exists': os.path.exists(CREDENTIALS_FILE_PATH),
        'sheets_available': SHEETS_AVAILABLE,
        'server_time': time.time(),
        'render_environment': bool(os.getenv('RENDER'))
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
                    debug_info['private_key_id'] = creds.get('private_key_id', 'Not found')
                    debug_info['key_type'] = creds.get('type', 'Not found')
                    
                    # Check private key
                    private_key = creds.get('private_key', '')
                    if private_key:
                        debug_info['private_key_length'] = len(private_key)
                        debug_info['private_key_has_newlines'] = '\n' in private_key
                        debug_info['private_key_starts_with'] = private_key[:30]
                except json.JSONDecodeError as e:
                    debug_info['json_valid'] = False
                    debug_info['json_error'] = str(e)
                    
        except Exception as e:
            debug_info['file_readable'] = False
            debug_info['file_error'] = str(e)
    else:
        debug_info['file_exists'] = False
        debug_info['note'] = 'Upload file to Render Secret Files with exact path'
    
    return jsonify(debug_info)

@app.route('/check-creds', methods=['GET'])
def check_credentials():
    """Verify FINAL credentials file"""
    try:
        print(f"🔍 Checking credentials at: {CREDENTIALS_FILE_PATH}")
        
        if not os.path.exists(CREDENTIALS_FILE_PATH):
            return jsonify({
                'status': 'error',
                'message': 'File not found at exact path',
                'exact_path': CREDENTIALS_FILE_PATH,
                'instruction': 'Upload to Render → Environment → Secret Files with exact mount path'
            }), 404
        
        with open(CREDENTIALS_FILE_PATH, 'r') as f:
            content = f.read()
            print(f"📄 File size: {len(content)} bytes")
            creds = json.loads(content)
        
        # Extract key details
        private_key = creds.get('private_key', '')
        client_email = creds.get('client_email', '')
        
        return jsonify({
            'status': 'success',
            'message': 'Credentials file is valid',
            'file_path': CREDENTIALS_FILE_PATH,
            'file_size': len(content),
            'credentials_file': 'nortiq-forms-65b5a63e6217.json',
            'service_account': client_email,
            'share_sheet_with': client_email,  # EMAIL TO SHARE GOOGLE SHEET WITH
            'project_id': creds.get('project_id'),
            'private_key_id': creds.get('private_key_id'),
            'private_key_length': len(private_key) if private_key else 0,
            'private_key_valid': private_key.startswith('-----BEGIN PRIVATE KEY-----'),
            'key_type': creds.get('type'),
            'action_required': 'Share your Google Sheet with the service account email above'
        })
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid JSON format',
            'error': str(e),
            'file_path': CREDENTIALS_FILE_PATH
        }), 500
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'type': type(e).__name__,
            'file_path': CREDENTIALS_FILE_PATH
        }), 500

def load_credentials():
    """Load credentials from EXACT path"""
    print(f"📂 Loading from: {CREDENTIALS_FILE_PATH}")
    
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        print(f"❌ File not found: {CREDENTIALS_FILE_PATH}")
        print("💡 Upload to Render → Environment → Secret Files")
        print(f"💡 Mount Path: {CREDENTIALS_FILE_PATH}")
        return None
    
    try:
        with open(CREDENTIALS_FILE_PATH, 'r') as f:
            credentials = json.load(f)
        
        # Verify required fields
        required = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing = [field for field in required if field not in credentials]
        
        if missing:
            print(f"❌ Missing fields: {missing}")
            return None
        
        print(f"✅ Loaded credentials for: {credentials.get('client_email', 'Unknown')}")
        return credentials
        
    except Exception as e:
        print(f"❌ Error reading {CREDENTIALS_FILE_PATH}: {e}")
        return None

def save_to_google_sheets(data):
    """Save form data to Google Sheets using FINAL credentials"""
    if not SHEETS_AVAILABLE:
        print("❌ Google Sheets library not available")
        return False
    
    if not GOOGLE_SHEET_KEY:
        print("❌ GOOGLE_SHEET_KEY not set")
        return False
    
    try:
        print("="*50)
        print("📊 GOOGLE SHEETS SAVE ATTEMPT")
        print("="*50)
        print(f"📁 Credentials: {CREDENTIALS_FILE_PATH}")
        print(f"🔑 Sheet ID: {GOOGLE_SHEET_KEY}")
        print(f"⏰ Time: {datetime.now().isoformat()}")
        
        # Load credentials from EXACT path
        credentials_dict = load_credentials()
        if not credentials_dict:
            print("❌ FAILED: Could not load credentials")
            return False
        
        service_email = credentials_dict.get('client_email', 'Unknown')
        print(f"✅ Service Account: {service_email}")
        print(f"✅ Project: {credentials_dict.get('project_id', 'Unknown')}")
        
        # Setup Google Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        
        creds = Credentials.from_service_account_info(
            credentials_dict, 
            scopes=scope
        )
        
        client = gspread.authorize(creds)
        
        # Open spreadsheet
        print(f"🔓 Opening Google Sheet...")
        spreadsheet = client.open_by_key(GOOGLE_SHEET_KEY)
        worksheet = spreadsheet.sheet1
        print(f"✅ Opened sheet: {worksheet.title}")
        
        # Prepare data
        interests = data.get('interests', [])
        if isinstance(interests, list):
            interests_str = ', '.join(interests)
        else:
            interests_str = str(interests) if interests else ''
        
        row = [
            data.get('fullName', ''),
            data.get('desiredPosition', ''),
            data.get('desiredYear', ''),
            interests_str,
            data.get('comments', ''),
            datetime.now().isoformat()
        ]
        
        print(f"📝 Data: {row[:3]}...")
        
        # Add headers if needed
        try:
            existing = worksheet.row_values(1)
            if not existing or existing[0] != 'Timestamp':
                headers = ['Timestamp', 'Full Name', 'Gender', 'Faculty', 
                          'Desired Position', 'Year', 'Email', 'Interest', 'Note']
                worksheet.insert_row(headers, 1)
                print("✅ Added headers")
        except Exception as e:
            print(f"⚠️ Header check: {e}")
        
        # Append row
        worksheet.append_row(row)
        print(f"✅ SUCCESS: Saved to Google Sheets!")
        print(f"👤 User: {data.get('fullName', 'Unknown')}")
        print(f"📧 Email: {data.get('email', 'No email')}")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"❌ GOOGLE SHEETS ERROR: {type(e).__name__}")
        print(f"❌ Details: {str(e)[:200]}")
        
        # Specific error handling
        if 'invalid_grant' in str(e):
            print("🔑 ERROR: Invalid JWT Signature")
            print("💡 Solution: Regenerate credentials or check time sync")
        elif 'PERMISSION_DENIED' in str(e):
            print("🔑 ERROR: Permission denied")
            print(f"💡 Solution: Share sheet with: {credentials_dict.get('client_email', 'service account')}")
        elif 'not found' in str(e).lower():
            print("🔑 ERROR: Sheet not found")
            print("💡 Solution: Check GOOGLE_SHEET_KEY environment variable")
        
        import traceback
        traceback.print_exc()
        return False

def send_confirmation_email(to_email, name):
    """Send confirmation email"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("❌ Email credentials not configured")
        return False
    
    try:
        print(f"📧 Sending email to {to_email}...")
        
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
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP Auth Failed: Use App Password, not regular password")
        return False
    except Exception as e:
        print(f"❌ Email error: {type(e).__name__}: {e}")
        return False

@app.route('/submit', methods=['POST', 'OPTIONS'])
def submit_form():
    """Handle form submission"""
    if request.method == 'OPTIONS':
        return '', 200
    
    print("\n" + "="*60)
    print("📝 FORM SUBMISSION - FINAL VERSION")
    print("="*60)
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data'}), 400
        
        print(f"👤 Name: {data.get('fullName', 'Unknown')}")
        print(f"📧 Email: {data.get('email', 'No email')}")
        
        # Save to Google Sheets
        sheets_success = False
        if GOOGLE_SHEET_KEY and SHEETS_AVAILABLE:
            sheets_success = save_to_google_sheets(data)
        else:
            print("⚠️ Google Sheets: Not configured")
        
        # Send email
        email_success = False
        email = data.get('email', '')
        name = data.get('fullName', 'User')
        
        if email:
            if EMAIL_USER and EMAIL_PASSWORD:
                email_success = send_confirmation_email(email, name)
            else:
                print("⚠️ Email: Not configured")
        else:
            print("⚠️ Email: No address provided")
        
        response = {
            'success': True,
            'message': 'Form submitted',
            'sheets_saved': sheets_success,
            'email_sent': email_success,
            'timestamp': datetime.now().isoformat(),
            'version': 'FINAL',
            'credentials_file': 'nortiq-forms-65b5a63e6217.json'
        }
        
        print(f"✅ Response: {response}")
        print("="*60)
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print("\n" + "="*60)
    print("🚀 FORM BACKEND - FINAL VERSION")
    print("="*60)
    print(f"📍 Port: {port}")
    print(f"📧 Email: {'✅ CONFIGURED' if EMAIL_USER and EMAIL_PASSWORD else '❌ NOT CONFIGURED'}")
    print(f"📊 Sheets Key: {'✅ SET' if GOOGLE_SHEET_KEY else '❌ NOT SET'}")
    print(f"📁 Credentials: {CREDENTIALS_FILE_PATH}")
    print(f"📁 File Exists: {'✅ YES' if os.path.exists(CREDENTIALS_FILE_PATH) else '❌ NO - Upload to Render Secret Files'}")
    print(f"📚 Sheets Lib: {'✅ AVAILABLE' if SHEETS_AVAILABLE else '❌ MISSING'}")
    print("="*60)
    print("💡 Upload credentials to Render → Environment → Secret Files")
    print(f"💡 Mount Path: {CREDENTIALS_FILE_PATH}")
    print("="*60)
    
    app.run(host='0.0.0.0', port=port, debug=False)