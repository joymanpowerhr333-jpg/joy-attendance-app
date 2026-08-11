import os
import json
import requests
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, Query, Response, Request
from supabase import create_client, Client

# Create FastAPI app
app = FastAPI()

# Read from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")

# Initialize Supabase
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
except:
    supabase = None
    print("Failed to initialize Supabase")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "whatsapp-webhook",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if supabase else "disconnected"
    }

# Webhook verification endpoint
@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    print(f"Webhook verification: mode={mode}, token={token}, challenge={challenge}")
    
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain", status_code=200)
    return Response(status_code=403)

# Webhook message handler
@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        body = await request.body()
        data = json.loads(body)
        print(f"Webhook received: {data}")
        
        # Process messages
        entries = data.get('entry', [])
        for entry in entries:
            changes = entry.get('changes', [])
            for change in changes:
                value = change.get('value', {})
                messages = value.get('messages', [])
                
                for message in messages:
                    phone_number = message.get('from', '')
                    text = message.get('text', {}).get('body', '')
                    
                    print(f"Message from {phone_number}: {text}")
                    
                    # Auto-reply for testing
                    if text.lower() in ["attendance", "report", "daily"]:
                        reply = "📊 *Attendance Report*\n\nToday's attendance is being processed.\n\nPowered by Joy Corporate Solutions"
                        
                        # Send reply using WhatsApp API
                        if WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
                            api_url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
                            headers = {
                                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                                "Content-Type": "application/json"
                            }
                            payload = {
                                "messaging_product": "whatsapp",
                                "to": phone_number,
                                "type": "text",
                                "text": {"body": reply}
                            }
                            requests.post(api_url, headers=headers, json=payload)
        
        return Response(content="EVENT_RECEIVED", status_code=200)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return Response(content="ERROR", status_code=500)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "WhatsApp Webhook Service is running",
        "endpoints": {
            "/": "This message",
            "/health": "Health check",
            "/webhook": "WhatsApp webhook endpoint (GET for verification, POST for messages)"
        }
    }
