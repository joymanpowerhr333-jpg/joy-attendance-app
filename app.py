import streamlit as st
from supabase import create_client, Client
import qrcode
import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import datetime
import base64
import os

# --- PAGE CONFIGURATION & UI STYLING ---
st.set_page_config(page_title="Joy Corporate Solutions", page_icon="🏢", layout="wide")

# Function to encode local image to Base64 for the CSS watermark
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Try to load the logo for the watermark.
watermark_css = ""
logo_path = "logo.png"
if os.path.exists(logo_path):
    img_base64 = get_base64_of_bin_file(logo_path)
    watermark_css = f"""
    <style>
    .stApp::before {{
        content: "";
        background-image: url("data:image/png;base64,{img_base64}");
        background-size: 40%;
        background-repeat: no-repeat;
        background-position: center;
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        opacity: 0.06; 
        z-index: -1;
        pointer-events: none;
    }}
    </style>
    """

# --- INJECT 3D REALISTIC CSS, CENTERING & ADAPTIVE DARK/LIGHT MODE ---
st.markdown(watermark_css, unsafe_allow_html=True)
st.markdown("""
    <style>
    /* 3D Typography & Global Centering - ADAPTIVE TO DARK/LIGHT MODE */
    h1, h2, h3, h4, p, label, span, div[data-testid="stMarkdownContainer"] > p { 
        text-align: center;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important; 
    }
    
    /* Center Streamlit Tabs and Radio Buttons */
    .stTabs [data-baseweb="tab-list"] { justify-content: center; }
    div[role="radiogroup"] { justify-content: center; }
    div.stButton { display: flex; justify-content: center; }
    
    /* 3D Realistic Neumorphic Buttons - FORCED ORANGE GRADIENT (Looks great on dark & light) */
    div.stButton > button:first-child {
        background: linear-gradient(145deg, #f68a28, #df7113) !important;
        box-shadow: 0px 4px 15px rgba(223, 113, 19, 0.4) !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 12px 30px !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.2s ease-in-out !important;
        width: 100%;
        max-width: 300px;
    }
    div.stButton > button:first-child * {
        color: white !important;
    }
    div.stButton > button:first-child:hover {
        background: linear-gradient(145deg, #df7113, #f68a28) !important;
        box-shadow: 0px 6px 20px rgba(223, 113, 19, 0.6) !important;
        transform: translateY(-2px);
    }
    
    /* Glassmorphism Forms & Containers - ADAPTIVE */
    .stForm, div[data-testid="stExpander"] { 
        background: var(--secondary-background-color) !important;
        backdrop-filter: blur(12px) !important;
        border-radius: 16px !important; 
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important;
        padding: 25px !important;
        margin: 0 auto;
    }
    
    /* Input Boxes 3D Effect - ADAPTIVE */
    input, select, .stTextInput > div > div > input, div[data-baseweb="select"] > div {
        border-radius: 8px !important;
        background: var(--background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
        text-align: center !important;
        color: var(--text-color) !important;
        -webkit-text-fill-color: var(--text-color) !important;
    }
    </style>
""", unsafe_allow_html=True)

# Connect to your Supabase Database securely
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- INITIALIZE SESSION STATE (APP MEMORY) ---
if "hr_logged_in" not in st.session_state:
    st.session_state.hr_logged_in = False
if "hr_username" not in st.session_state:
    st.session_state.hr_username = ""
if "super_logged_in" not in st.session_state:
    st.session_state.super_logged_in = False
if "camera_key" not in st.session_state:
    st.session_state.camera_key = 1
if "success_msg" not in st.session_state:
    st.session_state.success_msg = ""

# ==========================================
#         STATE 1: THE MAIN LOGIN SCREEN
# ==========================================
if not st.session_state.hr_logged_in and not st.session_state.super_logged_in:
    
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        if os.path.exists(logo_path):
            # Changed the column ratio from [1, 1, 1] to [5, 2, 5]. 
            # This makes the middle column exactly 50% smaller while staying perfectly centered!
            logo_col1, logo_col2, logo_col3 = st.columns([5, 2, 5])
            with logo_col2:
                st.image(logo_path, use_container_width=True)
                
        st.markdown("<h1>Joy Corporate Solutions</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 18px;'>Enterprise Attendance Portal</p><br>", unsafe_allow_html=True)
        
        login_type = st.selectbox("Select Portal Identity", ["HR User Portal", "Super Admin Portal"])
        st.write("<br>", unsafe_allow_html=True)
        
        if login_type == "HR User Portal":
            with st.form("hr_login_form"):
                st.markdown("### 🔐 HR Secure Login")
                hr_user_input = st.text_input("HR Username")
                hr_pass_input = st.text_input("HR Password", type="password")
                login_submit = st.form_submit_button("Authenticate")
                
                if login_submit:
                    hr_check = supabase.table("hr_users").select("*").eq("username", hr_user_input).eq("password", hr_pass_input).execute()
                    if hr_check.data:
                        st.session_state.hr_logged_in = True
                        st.session_state.hr_username = hr_user_input
                        st.rerun() 
                    else:
                        st.error("❌ Invalid HR Username or Password.")
                        
        elif login_type == "Super Admin Portal":
            with st.form("super_login_form"):
                st.markdown("### 🛡️ Master Control Login")
                super_pass_input = st.text_input("Master Key Password", type="password")
                if st.form_submit_button("Authenticate Mainframe"):
                    if super_pass_input == "JoyMaster2026":
                        st.session_state.super_logged_in = True
                        st.rerun() 
                    else:
                        st.error("❌ Invalid System Override.")


# ==========================================
#         STATE 2: THE HR DASHBOARD
# ==========================================
elif st.session_state.hr_logged_in:
    
    col_l, col_main, col_r = st.columns([1, 8, 1])
    
    with col_main:
        st.markdown(f"<h1>🏢 HR Command Center</h1>", unsafe_allow_html=True)
        st.markdown(f"<p>Secure Session Active: <b>{st.session_state.hr_username}</b></p>", unsafe_allow_html=True)
        
        if st.button("🚪 Terminate Session & Logout"):
            st.session_state.hr_logged_in = False
            st.session_state.hr_username = ""
            st.rerun()
            
        st.write("---")
        
        hr_action = st.radio("Select Module:", ["⏱️ Record Attendance", "📊 View Attendance Logs", "👤 Enroll New Employee", "👥 Employee Directory"], horizontal=True)
        st.write("<br>", unsafe_allow_html=True)
        
        # --- 1. RECORD ATTENDANCE ---
        if hr_action == "⏱️ Record Attendance":
            st.markdown("### ⏱️ Daily Attendance Capture")
            
            if st.session_state.success_msg:
                st.success(st.session_state.success_msg)
                st.session_state.success_msg = ""
            
            tab1, tab2 = st.tabs(["📸 3D QR Scanner", "⌨️ Manual Entry"])
            
            with tab1:
                st.info("Hold the Employee QR Code up to the camera. The scanner will automatically reset for the next person once submitted.")
                
                scan_image = st.camera_input("Scanner Camera", key=f"qr_cam_{st.session_state.camera_key}")
                
                if scan_image and st.button("Submit QR Attendance"):
                    bytes_data = scan_image.getvalue()
                    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                    detector = cv2.QRCodeDetector()
                    data, bbox, _ = detector.detectAndDecode(cv2_img)
                    
                    if data:
                        supabase.table("attendance").insert({"emp_id": data, "method": "QR Code"}).execute()
                        st.session_state.success_msg = f"✅ Attendance successfully recorded for ID: **{data}**"
                        st.session_state.camera_key += 1
                        st.rerun()
                    else:
                        st.error("⚠️ No QR code detected. Please ensure it is clearly visible and try again.")
            
            with tab2:
                with st.form("manual_entry_form", clear_on_submit=True):
                    manual_id = st.text_input("Enter Employee ID Number")
                    manual_submit = st.form_submit_button("Record Manual Punch")
                    
                    if manual_submit and manual_id:
                        supabase.table("attendance").insert({"emp_id": manual_id, "method": "Manual Entry"}).execute()
                        st.success(f"✅ Manual attendance successfully recorded for ID: **{manual_id}**")
                        
        # --- 2. ENROLL NEW EMPLOYEE ---
        elif hr_action == "👤 Enroll New Employee":
            st.markdown("### 👤 Employee Enrollment & ID Generation")
            
            with st.form("enrollment_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    emp_id = st.text_input("Employee ID Number*")
                    name = st.text_input("Full Name*")
                with col2:
                    department = st.text_input("Department")
                    mobile = st.text_input("Mobile Number")
                
                submit_button = st.form_submit_button("✨ Generate Profile & ID Card")
            
            if submit_button and emp_id and name:
                try:
                    current_date = datetime.date.today().strftime('%d-%m-%Y')
                    supabase.table("employees").insert({
                        "emp_id": emp_id, "name": name, "department": department,
                        "mobile": mobile, "status": "Active", "status_updated_on": current_date
                    }).execute()
                    st.success(f"🎉 Profile created for {name}! The form has been reset for the next person.")
                    
                    qr = qrcode.QRCode(box_size=10, border=4)
                    qr.add_data(emp_id)
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color="#1a365d", back_color="white").convert("RGB")
                    
                    width, height = qr_img.size
                    id_card = Image.new('RGB', (width, height + 150), 'white')
                    id_card.paste(qr_img, (0, 0))
                    
                    draw = ImageDraw.Draw(id_card)
                    try:
                        font_large = ImageFont.truetype("arial.ttf", 24)
                        font_small = ImageFont.truetype("arial.ttf", 20)
                    except:
                        font_large = ImageFont.load_default()
                        font_small = ImageFont.load_default()
                        
                    draw.text((20, height), f"Name: {name}", fill="#1a365d", font=font_large)
                    draw.text((20, height + 40), f"Emp ID: {emp_id}", fill="#1a365d", font=font_large)
                    draw.text((20, height + 80), f"Dept: {department}", fill="#666666", font=font_small)
                    draw.text((20, height + 110), f"Phone: {mobile}", fill="#666666", font=font_small)
                    
                    img_col1, img_col2, img_col3 = st.columns([1, 2, 1])
                    with img_col2:
                        st.image(id_card, caption=f"ID Card for {name} (Right-click image to 'Save As' and print)")
                except Exception as e:
                    if "duplicate key" in str(e).lower() or "23505" in str(e):
                        st.warning(f"⚠️ Employee ID '{emp_id}' already exists! Please use a different ID.")
                    else:
                        st.error("An unexpected error occurred. Please try again.")

        # --- 3. EMPLOYEE DIRECTORY & STATUS MANAGEMENT ---
        elif hr_action == "👥 Employee Directory":
            st.markdown("### 👥 Employee Lifecycle Management")
            
            dir_tab1, dir_tab2 = st.tabs(["📋 View & Download Roster", "🔄 Update Lifecycle Status"])
            
            with dir_tab1:
                status_filter = st.radio("Filter Directory By:", ["Active", "Left", "All"], horizontal=True)
                emp_response = supabase.table("employees").select("*").execute()
                
                if emp_response.data:
                    df_emp = pd.DataFrame(emp_response.data)
                    if "status" not in df_emp.columns: df_emp["status"] = "Active"
                    if "status_updated_on" not in df_emp.columns: df_emp["status_updated_on"] = "N/A"
                    df_emp["status"] = df_emp["status"].fillna("Active")
                    df_emp["status_updated_on"] = df_emp["status_updated_on"].fillna("N/A")
                    
                    if status_filter != "All":
                        df_emp = df_emp[df_emp["status"] == status_filter]
                    
                    if not df_emp.empty:
                        cols = ["emp_id", "name", "department", "mobile", "status", "status_updated_on"]
                        df_emp = df_emp[[c for c in cols if c in df_emp.columns]].rename(columns={
                            "emp_id": "Employee ID", "name": "Name", "department": "Department",
                            "mobile": "Phone", "status": "Status", "status_updated_on": "Effective Date"
                        })
                        st.dataframe(df_emp, use_container_width=True)
                        csv_emp = df_emp.to_csv(index=False).encode('utf-8')
                        st.download_button(f"📥 Download {status_filter} Roster CSV", data=csv_emp, file_name=f'Joy_{status_filter}_Roster.csv', mime='text/csv')
                    else:
                        st.info(f"No {status_filter.lower()} employees found in the database.")
                else:
                    st.info("No employees have been enrolled yet.")
                    
            with dir_tab2:
                with st.form("status_update_form"):
                    st.info("Log employee resignations or reactivations and track the effective date.")
                    col1, col2, col3 = st.columns(3)
                    with col1: update_id = st.text_input("Enter Employee ID")
                    with col2: new_status = st.selectbox("Select New Status", ["Left", "Active"])
                    with col3: effective_date = st.date_input("Effective Date", datetime.date.today())
                    status_submit = st.form_submit_button("Update Status")
                    
                if status_submit and update_id:
                    formatted_date = effective_date.strftime('%d-%m-%Y')
                    try:
                        check_emp = supabase.table("employees").select("*").eq("emp_id", update_id).execute()
                        if check_emp.data:
                            supabase.table("employees").update({"status": new_status, "status_updated_on": formatted_date}).eq("emp_id", update_id).execute()
                            st.success(f"✅ Successfully updated Employee **{update_id}** to **{new_status}** status as of **{formatted_date}**!")
                        else:
                            st.error(f"❌ Employee ID {update_id} not found in the database.")
                    except Exception as e:
                        st.error(f"Error updating status. Please try again.")

        # --- 4. VIEW ATTENDANCE LOGS ---
        elif hr_action == "📊 View Attendance Logs":
            st.markdown("### 📊 Enterprise Attendance Reports")
            
            report_type = st.radio("Choose Report Type", ["Daily Report", "Monthly Report", "Custom Date Range"], horizontal=True)
            today = datetime.date.today()
            report_name = ""
            
            st.write("<br>", unsafe_allow_html=True)
            
            if report_type == "Daily Report":
                search_date = st.date_input("Select Date", today)
                report_name = f"Daily_{search_date}"
                
            elif report_type == "Monthly Report":
                col1, col2 = st.columns(2)
                with col1:
                    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                    selected_month = st.selectbox("Select Month", months, index=today.month - 1)
                    month_num = months.index(selected_month) + 1
                with col2:
                    selected_year = st.selectbox("Select Year", range(today.year - 5, today.year + 5), index=5)
                report_name = f"Monthly_{selected_month}_{selected_year}"
                
            elif report_type == "Custom Date Range":
                date_range = st.date_input("Select Start and End Date", [today, today])
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    report_name = f"Custom_{start_date}_to_{end_date}"
                else:
                    st.warning("Please select both a start and end date.")
                    report_name = "Custom_Range"
            
            att_response = supabase.table("attendance").select("*").execute()
            emp_response = supabase.table("employees").select("emp_id, name, department").execute()
            
            if att_response.data:
                df_att = pd.DataFrame(att_response.data)
                df_emp = pd.DataFrame(emp_response.data) if emp_response.data else pd.DataFrame(columns=["emp_id", "name", "department"])
                
                if not df_emp.empty:
                    df = pd.merge(df_att, df_emp, on="emp_id", how="left")
                else:
                    df = df_att
                    df["name"], df["department"] = "Unknown", "Unknown"
                
                if "time_logged" in df.columns:
                    df["time_logged"] = pd.to_datetime(df["time_logged"]).dt.tz_convert('Asia/Kolkata')
                    df["date_only"] = df["time_logged"].dt.date
                    
                    if report_type == "Daily Report":
                        df_filtered = df[df["date_only"] == search_date].copy()
                    elif report_type == "Monthly Report":
                        df_filtered = df[(df["time_logged"].dt.month == month_num) & (df["time_logged"].dt.year == selected_year)].copy()
                    elif report_type == "Custom Date Range":
                        if len(date_range) == 2:
                            df_filtered = df[(df["date_only"] >= start_date) & (df["date_only"] <= end_date)].copy()
                        else:
                            df_filtered = pd.DataFrame() 
                    
                    if not df_filtered.empty:
                        df_filtered["Date"] = df_filtered["time_logged"].dt.strftime('%d-%m-%Y')
                        df_filtered["Punch Time"] = df_filtered["time_logged"].dt.strftime('%I:%M %p')
                        df_filtered = df_filtered.drop(columns=["id", "method", "date_only", "face_encoding", "time_logged"], errors="ignore")
                        
                        cols = ["emp_id", "name", "department", "Date", "Punch Time"]
                        df_filtered = df_filtered[[c for c in cols if c in df_filtered.columns]].rename(columns={"emp_id": "Employee ID", "name": "Name", "department": "Department"})
                        
                        st.dataframe(df_filtered, use_container_width=True)
                        csv = df_filtered.to_csv(index=False).encode('utf-8')
                        st.download_button(f"📥 Export {report_name} CSV", data=csv, file_name=f'Joy_Attendance_{report_name}.csv', mime='text/csv')
                    else:
                        st.info("No attendance records found for the selected criteria.")
            else:
                st.info("No attendance records found yet.")


# ==========================================
#         STATE 3: THE SUPER ADMIN DASHBOARD
# ==========================================
elif st.session_state.super_logged_in:
    
    col_l, col_main, col_r = st.columns([1, 6, 1])
    
    with col_main:
        st.markdown("<h1>🛡️ Super Admin Control Center</h1>", unsafe_allow_html=True)
        st.markdown("<p>✅ Mainframe Accessed: Full system privileges active.</p>", unsafe_allow_html=True)
        
        if st.button("🚪 Terminate Session & Logout"):
            st.session_state.super_logged_in = False
            st.rerun()
            
        st.write("---")
        
        sa_tab1, sa_tab2 = st.tabs(["➕ Provision HR Accounts", "👥 Security Audit & Directory"])
        
        with sa_tab1:
            with st.form("new_hr_form"):
                st.markdown("#### Provision New Access Credential")
                new_hr_username = st.text_input("New Identity (Username)")
                new_hr_password = st.text_input("Security Key (Password)", type="password")
                
                if st.form_submit_button("Generate & Encrypt Account"):
                    if new_hr_username and new_hr_password:
                        try:
                            supabase.table("hr_users").insert({"username": new_hr_username, "password": new_hr_password}).execute()
                            st.success(f"🎉 Credential provisioned successfully for: **{new_hr_username}**")
                        except Exception as e:
                            st.error("Error creating account. Ensure the username is globally unique.")
                    
        with sa_tab2:
            st.markdown("#### Security Roster")
            st.info("Authorized HR node identities (encryption keys hidden per compliance).")
            try:
                hr_list = supabase.table("hr_users").select("id, username").execute()
                if hr_list.data:
                    df_hr = pd.DataFrame(hr_list.data).rename(columns={"id": "System ID Node", "username": "HR Identity"})
                    st.dataframe(df_hr, use_container_width=True)
                else:
                    st.info("No active nodes on network.")
            except Exception as e:
                st.error("Network error retrieving users.")
