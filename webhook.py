import os
import json
import requests
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, Query, Response, Request
from supabase import create_client, Client

app = FastAPI()

# Read from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# --- WHATSAPP FUNCTIONS ---
def log_whatsapp_message(phone_number, message_type, message_text, status, message_id=None, error_message=None):
    """Log WhatsApp message in Supabase"""
    try:
        if supabase:
            data = {
                "phone_number": phone_number,
                "message_type": message_type,
                "message_text": message_text[:500] if message_text else "",
                "status": status,
                "message_id": message_id,
                "error_message": error_message,
                "sent_at": datetime.now().isoformat()
            }
            supabase.table("whatsapp_messages").insert(data).execute()
        return True
    except Exception as e:
        print(f"Error logging message: {str(e)}")
        return False

def send_whatsapp_message_cloud_api(phone_number, message):
    """Send WhatsApp message using Meta's Cloud API"""
    try:
        access_token = WHATSAPP_ACCESS_TOKEN
        phone_number_id = WHATSAPP_PHONE_NUMBER_ID
        
        if not access_token or not phone_number_id:
            return False, "WhatsApp Cloud API credentials not configured"
        
        # Clean phone number (remove + if present)
        clean_number = phone_number.replace('+', '').strip()
        
        # Prepare the API endpoint
        api_url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        # Make the API request
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            
            # Log success
            log_whatsapp_message(
                clean_number, 
                "text", 
                message[:500],
                "sent", 
                message_id
            )
            
            return True, f"Message sent successfully! Message ID: {message_id}"
        else:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            # Log failure
            log_whatsapp_message(
                clean_number, 
                "text", 
                message[:500],
                "failed", 
                None, 
                error_message
            )
            
            return False, f"WhatsApp API Error: {error_message}"
            
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        log_whatsapp_message(phone_number, "text", message[:500], "failed", None, error_msg)
        return False, error_msg

def get_attendance_report():
    """Get today's attendance report"""
    try:
        if not supabase:
            return "Database not configured"
        
        # Get employees
        res = supabase.table("employees").select("*").execute()
        if not res.data:
            return "No employee data available"
        
        df_emp = pd.DataFrame(res.data)
        
        # Get today's attendance
        today_str = datetime.now().strftime('%Y-%m-%d')
        att_res = supabase.table("attendance").select("*").eq("date_only", today_str).execute()
        
        present_ids = []
        leave_ids = []
        
        if att_res.data:
            df_att = pd.DataFrame(att_res.data)
            present_ids = df_att[df_att['punch_type'].isin(['Punch In', 'QR Code', 'Manual Entry'])]['emp_id'].unique().tolist()
            leave_ids = df_att[df_att['punch_type'] == 'Leave']['emp_id'].unique().tolist()
        
        # Build report
        total_employees = len(df_emp)
        present = len([e for e in df_emp['emp_id'].tolist() if e in present_ids])
        leave = len([e for e in df_emp['emp_id'].tolist() if e in leave_ids])
        absent = total_employees - present - leave
        attendance_rate = round((present / total_employees) * 100 if total_employees > 0 else 0, 1)
        
        message = f"📊 *JOY CORPORATE SOLUTIONS*\n"
        message += f"📅 *Daily Attendance Report*\n"
        message += f"🗓️ Date: {datetime.now().strftime('%d-%m-%Y')}\n"
        message += f"{'='*35}\n\n"
        message += f"📌 *Total Employees:* {total_employees}\n"
        message += f"✅ *Present:* {present}\n"
        message += f"❌ *Absent:* {absent}\n"
        message += f"🏠 *On Leave:* {leave}\n"
        message += f"📈 *Attendance Rate:* {attendance_rate}%\n"
        
        return message
        
    except Exception as e:
        return f"Error generating report: {str(e)}"

# --- FASTAPI WEBHOOK ENDPOINTS ---

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """Verify webhook endpoint for WhatsApp"""
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain", status_code=200)
    return Response(status_code=403)

@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming WhatsApp webhook messages"""
    try:
        # Get the request body
        body = await request.body()
        data = json.loads(body)
        
        # Log incoming webhook
        print(f"Webhook received: {data}")
        
        # Process the webhook data
        entries = data.get('entry', [])
        for entry in entries:
            changes = entry.get('changes', [])
            for change in changes:
                value = change.get('value', {})
                messages = value.get('messages', [])
                
                for message in messages:
                    # Get message details
                    phone_number = message.get('from', '')
                    text = message.get('text', {}).get('body', '')
                    
                    # Log incoming message
                    log_whatsapp_message(
                        phone_number,
                        "incoming",
                        text,
                        "received"
                    )
                    
                    # Process commands
                    if text.lower() in ["attendance", "report", "daily"]:
                        # Generate and send attendance report
                        report = get_attendance_report()
                        send_whatsapp_message_cloud_api(phone_number, report)
                    
                    elif text.lower() == "help":
                        help_msg = "🤖 *Available Commands:*\n\n"
                        help_msg += "📊 *attendance* - Get today's attendance report\n"
                        help_msg += "📅 *monthly* - Get monthly attendance summary\n"
                        help_msg += "❓ *help* - Show this help message\n\n"
                        help_msg += "💡 *Powered by Joy Corporate Solutions*"
                        send_whatsapp_message_cloud_api(phone_number, help_msg)
                    
                    elif text.lower() == "monthly":
                        # Send monthly report
                        report = "📅 Monthly report feature coming soon!\n"
                        report += "Please check the dashboard for detailed monthly analytics."
                        send_whatsapp_message_cloud_api(phone_number, report)
        
        return Response(content="EVENT_RECEIVED", status_code=200)
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return Response(content="ERROR", status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy",
        "service": "whatsapp-webhook",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if supabase else "disconnected"
    }

# For running locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)