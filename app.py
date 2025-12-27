"""
COMPLETE WORKING Flask Backend for Form Submission
Google Sheets + Email sending - FIXED VERSION
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
        'endpoints': ['/', '/ping', '/health', '/test', '/submit', '/debug']
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
        'creds_length': len(GOOGLE_CREDENTIALS_JSON) if GOOGLE_CREDENTIALS_JSON else 0,
        'sheets_library': 'AVAILABLE' if SHEETS_AVAILABLE else 'NOT AVAILABLE'
    })

@app.route('/debug')
def debug():
    """Debug Google Sheets credentials"""
    debug_info = {
        'json_set': bool(GOOGLE_CREDENTIALS_JSON),
        'json_length': len(GOOGLE_CREDENTIALS_JSON) if GOOGLE_CREDENTIALS_JSON else 0,
        'first_50': GOOGLE_CREDENTIALS_JSON[:50] if GOOGLE_CREDENTIALS_JSON else '',
        'last_50': GOOGLE_CREDENTIALS_JSON[-50:] if GOOGLE_CREDENTIALS_JSON else ''
    }
    
    if GOOGLE_CREDENTIALS_JSON:
        try:
            creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
            debug_info['parse_success'] = True
            debug_info['service_account'] = creds_dict.get('client_email', 'Not found')
            debug_info['project_id'] = creds_dict.get('project_id', 'Not found')
        except json.JSONDecodeError as e:
            debug_info['parse_error'] = str(e)
            debug_info['parse_success'] = False
    
    return jsonify(debug_info)

def save_to_google_sheets(data):
    """Save form data to Google Sheets - FIXED VERSION"""
    if not SHEETS_AVAILABLE:
        print("❌ Google Sheets library not available")
        return False
    
    if not GOOGLE_SHEET_KEY:
        print("❌ GOOGLE_SHEET_KEY not set")
        return False
    
    if not GOOGLE_CREDENTIALS_JSON:
        print("❌ GOOGLE_CREDENTIALS_JSON not set")
        return False
    
    try:
        print("📊 Attempting to save to Google Sheets...")
        print(f"JSON length: {len(GOOGLE_CREDENTIALS_JSON)}")
        print(f"First 100 chars: {GOOGLE_CREDENTIALS_JSON[:100]}")
        
        # Try multiple ways to parse the JSON
        credentials_dict = None
        
        # Method 1: Direct JSON parse
        try:
            credentials_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
            print("✅ Method 1: Direct JSON parse successful")
        except json.JSONDecodeError as e:
            print(f"❌ Method 1 failed: {e}")
            
            # Method 2: Clean and try again
            try:
                # Replace escaped newlines with actual newlines
                cleaned = GOOGLE_CREDENTIALS_JSON.replace('\\n', '\n')
                credentials_dict = json.loads(cleaned)
                print("✅ Method 2: Cleaned JSON parse successful")
            except json.JSONDecodeError as e2:
                print(f"❌ Method 2 failed: {e2}")
                
                # Method 3: Try base64 decode
                try:
                    import base64
                    decoded = base64.b64decode(GOOGLE_CREDENTIALS_JSON).decode('utf-8')
                    credentials_dict = json.loads(decoded)
                    print("✅ Method 3: Base64 decode successful")
                except Exception as e3:
                    print(f"❌ Method 3 failed: {e3}")
                    return False
        
        if not credentials_dict:
            print("❌ Could not parse credentials")
            return False
        
        print(f"✅ Service Account: {credentials_dict.get('client_email', 'Unknown')}")
        print(f"✅ Project ID: {credentials_dict.get('project_id', 'Unknown')}")
        
        # Setup Google Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
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
        print(f"🎓 Faculty: {data.get('faculty', 'Not specified')}")
        
        # Save to Google Sheets
        sheets_success = False
        if GOOGLE_SHEET_KEY and GOOGLE_CREDENTIALS_JSON and SHEETS_AVAILABLE:
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
    print(f"📊 Sheets: {'CONFIGURED' if GOOGLE_SHEET_KEY and GOOGLE_CREDENTIALS_JSON else 'NOT CONFIGURED'}")
    print(f"📚 Sheets Library: {'AVAILABLE' if SHEETS_AVAILABLE else 'MISSING'}")
    print(f"🌍 Environment: {'Render' if os.getenv('RENDER') else 'Local'}")
    print("="*60 + "\n")
    
    # For Render deployment
    app.run(host='0.0.0.0', port=port, debug=False)