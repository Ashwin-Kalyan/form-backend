from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'ok', 'message': 'Server is working!'})

@app.route('/ping')
def ping():
    return jsonify({'pong': True})

@app.route('/health')
def health():
    return jsonify({'healthy': True})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port)