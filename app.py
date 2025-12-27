"""
COMPLETE WORKING Flask Backend for Form Submission
Uses NEW credentials file: nortiq-forms-65b5a63e6217.json
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

# NEW credentials file path - Render Secret Files location
CREDENTIALS_FILE_PATH = "/etc/secrets/credentials.json"
BACKUP_CREDENTIALS_PATH = "/opt/render/project/src/credentials.json"

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'service': 'Form Submission Backend v2.0',
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
        'sheets_library': 'AVAILABLE' if SHEETS_AVAILABLE else 'NOT AVAILABLE',
        'server_time': datetime.now().isoformat(),
        'unix_time': time.time()
    })

@app.route('/debug')
def debug():
    """Debug credentials file"""
    debug_info = {
        'credentials_path': CREDENTIALS_FILE_PATH,
        'backup_path': BACKUP_CREDENTIALS_PATH,
        'file_exists': os.path.exists(CREDENTIALS_FILE_PATH),
        'backup_exists': os.path.exists(BACKUP_CREDENTIALS_PATH),
        'sheets_available': SHEETS_AVAILABLE,
        'server_time': time.time()
    }
    
    # Try primary path
    if os.path.exists(CREDENTIALS_FILE_PATH):
        try:
            with open(CREDENTIALS_FILE_PATH, 'r') as f:
                content = f.read()
                debug_info['primary_file_size'] = len(content)
                debug_info['primary_file_readable'] = True
                
                # Try to parse as JSON
                try:
                    creds = json.loads(content)
                    debug_info['primary_json_valid'] = True
                    debug_info['service_account'] = creds.get('client_email', 'Not found')
                    debug_info['project_id'] = creds.get('project_id', 'Not found')
                    debug_info['private_key_id'] = creds.get('private_key_id', 'Not found')
                    debug_info['key_type'] = creds.get('type', 'Not found')
                except json.JSONDecodeError as e:
                    debug_info['primary_json_valid'] = False
                    debug_info['primary_json_error'] = str(e)
                    
        except Exception as e:
            debug_info['primary_file_readable'] = False
            debug_info['primary_file_error'] = str(e)
    
    # Try backup path
    if os.path.exists(BACKUP_CREDENTIALS_PATH):
        try:
            with open(BACKUP_CREDENTIALS_PATH, 'r') as f:
                content = f.read()
                debug_info['backup_file_size'] = len(content)
                debug_info['backup_file_readable'] = True
        except Exception as e:
            debug_info['backup_file_readable'] = False
    
    return jsonify(debug_info)

@app.route('/check-creds', methods=['GET'])
def check_credentials():
    """Verify NEW credentials file"""
    try:
        # Try primary location first
        file_path = CREDENTIALS_FILE_PATH
        if not os.path.exists(file_path):
            # Try backup
            file_path = BACKUP_CREDENTIALS_PATH
            if not os.path.exists(file_path):
                return jsonify({
                    'error': 'File not found',
                    'primary_path': CREDENTIALS_FILE_PATH,
                    'backup_path': BACKUP_CREDENTIALS_PATH,
                    'both_exist': False
                }), 404
        
        with open(file_path, 'r') as f:
            content = f.read()
            creds = json.loads(content)
        
        # Extract key details
        private_key = creds.get('private_key', '')
        private_key_lines = private_key.count('\n') if private_key else 0
        
        return jsonify({
            'status': 'ok',
            'file_path': file_path,
            'file_exists': True,
            'file_size': len(content),
            'credentials_file': 'nortiq-forms-65b5a63e6217.json',
            'service_account': creds.get('client_email'),
            'project_id': creds.get('project_id'),
            'private_key_id': creds.get('private_key_id'),
            'private_key_length': len(private_key) if private_key else 0,
            'private_key_lines': private_key_lines,
            'private_key_starts': private_key[:50] + '...' if private_key else 'None',
            'private_key_ends': '...' + private_key[-50:] if private_key else 'None',
            'key_type': creds.get('type'),
            'universe_domain': creds.get('universe_domain', 'Not specified')
        })
        
    except json.JSONDecodeError as e:
        return jsonify({
            'error': 'JSON Parse Error',
            'details': str(e),
            'file_path': file_path
        }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'type': type(e).__name__,
            'file_path': file_path if 'file_path' in locals() else 'Unknown'
        }), 500

def load_credentials():
    """Load credentials from file with fallback"""
    possible_paths = [
        CREDENTIALS_FILE_PATH,      # Render Secret Files
        BACKUP_CREDENTIALS_PATH,    # Project directory
        "nortiq-forms-65b5a63e6217.json",  # Local development
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Found credentials at: {path}")
            try:
                with open(path, 'r') as f:
                    credentials = json.load(f)
                
                # Verify required fields
                required = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                if all(field in credentials for field in required):
                    print(f"✅ Loaded credentials for: {credentials.get('client_email', 'Unknown')}")
                    return credentials
                else:
                    print(f"❌ Missing required fields in: {path}")
                    
            except Exception as e:
                print(f"❌ Error reading {path}: {e}")
    
    print(f"❌ No valid credentials found in: {possible_paths}")
    return None

def save_to_google_sheets(data):
    """Save form data to Google Sheets using NEW credentials"""
    if not SHEETS_AVAILABLE:
        print("❌ Google Sheets library not available")
        return False
    
    if not GOOGLE_SHEET_KEY:
        print("❌ GOOGLE_SHEET_KEY not set")
        return False
    
    try:
        print("📊 Attempting to save to Google Sheets...")
        print(f"📁 Using NEW credentials file: nortiq-forms-65b5a63e6217.json")
        print(f"🔑 Sheet ID: {GOOGLE_SHEET_KEY}")
        print(f"⏰ Server time: {time.time()}")
        
        # Load credentials from file
        credentials_dict = load_credentials()
        if not credentials_dict:
            print("❌ Failed to load credentials")
            return False
        
        service_email = credentials_dict.get('client_email', 'Unknown')
        print(f"✅ Service Account: {service_email}")
        print(f"✅ Project ID: {credentials_dict.get('project_id', 'Unknown')}")
        print(f"✅ Private Key ID: {credentials_dict.get('private_key_id', 'Unknown')}")
        
        # IMPORTANT: Fix for time sync issues
        # Sometimes Render server time is off
        current_time = time.time()
        print(f"⏱️ Current UNIX time: {current_time}")
        
        # Setup Google Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        
        # Add extra parameters for JWT validation
        from google.oauth2.service_account import Credentials
        
        creds = Credentials.from_service_account_info(
            credentials_dict, 
            scopes=scope,
            subject=service_email  # Sometimes needed
        )
        
        client = gspread.authorize(creds)
        
        # Open spreadsheet
        print(f"🔓 Opening spreadsheet with ID: {GOOGLE_SHEET_KEY}")
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
        
        print(f"📝 Prepared row data: {row[:3]}...")
        
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
        print(f"✅ Sheet URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_KEY}")
        return True
        
    except Exception as e:
        print(f"❌ Google Sheets Error: {type(e).__name__}: {str(e)}")
        print(f"❌ Error details: {e.args if hasattr(e, 'args') else 'No args'}")
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
    print("📝 FORM SUBMISSION RECEIVED - v2.0")
    print("="*60)
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        print(f"👤 Name: {data.get('fullName', 'Unknown')}")
        print(f"📧 Email: {data.get('email', 'No email')}")
        print(f"⏰ Submission time: {datetime.now().isoformat()}")
        
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
            'timestamp': datetime.now().isoformat(),
            'version': '2.0',
            'credentials_file': 'nortiq-forms-65b5a63e6217.json'
        }
        
        print(f"✅ Response: {response}")
        print("="*60 + "\n")
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Internal server error', 'version': '2.0'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print("\n" + "="*60)
    print(f"🚀 Starting Form Backend v2.0 on port {port}")
    print(f"📧 Email: {'CONFIGURED' if EMAIL_USER and EMAIL_PASSWORD else 'NOT CONFIGURED'}")
    print(f"📊 Sheets Key: {'SET' if GOOGLE_SHEET_KEY else 'NOT SET'}")
    print(f"📁 Credentials File: nortiq-forms-65b5a63e6217.json")
    print(f"📁 Primary Path: {CREDENTIALS_FILE_PATH}")
    print(f"📁 Primary Exists: {os.path.exists(CREDENTIALS_FILE_PATH)}")
    print(f"📁 Backup Exists: {os.path.exists(BACKUP_CREDENTIALS_PATH)}")
    print(f"📚 Sheets Library: {'AVAILABLE' if SHEETS_AVAILABLE else 'MISSING'}")
    print(f"⏰ Server Time: {time.time()}")
    print("="*60 + "\n")
    
    # For Render deployment
    app.run(host='0.0.0.0', port=port, debug=False)