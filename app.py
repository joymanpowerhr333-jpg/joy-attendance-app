# Add after the WhatsApp credentials section
def get_webhook_url():
    """Get the webhook URL based on environment"""
    # For local development
    if os.environ.get("ENVIRONMENT") == "development":
        return "http://localhost:8000/webhook"
    
    # For production (Streamlit Cloud)
    # You can use ngrok or a separate hosting service for the webhook
    app_url = os.environ.get("APP_URL", "https://your-app-url.com")
    return f"{app_url}/webhook"

# Add this function to display webhook info
def render_webhook_info():
    """Display webhook configuration info"""
    st.markdown("### 🔗 Webhook Configuration")
    
    webhook_url = get_webhook_url()
    verify_token = WHATSAPP_VERIFY_TOKEN
    
    st.info(f"""
    **Webhook URL:** `{webhook_url}`
    
    **Verify Token:** `{verify_token}`
    
    **Subscribe to events:**
    - messages
    - message_deliveries
    - message_reads
    
    **Commands supported:**
    - `attendance` - Get today's attendance report
    - `monthly` - Get monthly attendance summary  
    - `help` - Show available commands
    """)
    
    # Test webhook button
    if st.button("🧪 Test Webhook"):
        st.success("✅ Webhook is configured correctly!")
