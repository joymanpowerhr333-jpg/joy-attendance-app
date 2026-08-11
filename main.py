import os
from flask import Flask, request

app = Flask(_name_)

# Reads token from Render environment variables or falls back to your token string
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "whatsapp_attendance_2026")

@app.route('/Webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        # Return plain text challenge with 200 OK
        return str(challenge), 200
    
    return 'Verification failed', 403

if _name_ == '_main_':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
