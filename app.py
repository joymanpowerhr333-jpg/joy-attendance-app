import streamlit as st
from supabase import create_client, Client
import qrcode
import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta
import base64
import os
import io

# --- PAGE CONFIGURATION & UI STYLING ---
st.set_page_config(page_title="Joy Corporate Solutions", page_icon="🏢", layout="wide")

# Set up Indian Standard Time (IST) globally
IST = timezone(timedelta(hours=5, minutes=30))

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

watermark_css = ""
logo_path = "logo.png"
if os.path.exists(logo_path):
    img_base64 = get_base64_of_bin_file(logo_path)
    watermark_css = f"""
    <style>
    .stApp::before {{
        content: ""; background-image: url("data:image/png;base64,{img_base64}");
        background-size: 40%; background-repeat: no-repeat; background-position: center;
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        opacity: 0.06; z-index: -1; pointer-events: none;
    }}
    </style>
    """

st.markdown(watermark_css, unsafe_allow_html=True)
st.markdown("""
    <style>
    h1, h2, h3, h4, p, label, span, div[data-testid="stMarkdownContainer"] > p { 
        text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important; 
    }
    .stTabs [data-baseweb="tab-list"] { justify-content: center; }
    div[role="radiogroup"] { justify-content: center; }
    div.stButton { display: flex; justify-content: center; }
    
    div.stButton > button:first-child {
        background: linear-gradient(145deg, #f68a28, #df7113) !important;
        box-shadow: 0px 4px 15px rgba(223, 113, 19, 0.4) !important;
        color: white !important; border-radius: 12px !important; border: none !important;
        padding: 12px 30px !important; font-weight: 700 !important; letter-spacing: 0.5px !important;
        transition: all 0.2s ease-in-out !important; width: 100%; max-width: 300px;
    }
    div.stButton > button:first-child * { color: white !important; }
    div.stButton > button:first-child:hover {
        background: linear-gradient(145deg, #df7113, #f68a28) !important;
        box-shadow: 0px 6px 20px rgba(223, 113, 19, 0.6) !important; transform: translateY(-2px);
    }
    
    .stForm, div[data-testid="stExpander"] { 
        background: var(--secondary-background-color) !important; backdrop-filter: blur(12px) !important;
        border-radius: 16px !important; border: 1px solid rgba(128, 128, 128, 0.2) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important; padding: 25px !important; margin: 0 auto;
    }
    
    input, select, .stTextInput > div > div > input, div[data-baseweb="select"] > div {
        border-radius: 8px !important; background: var(--background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important; text-align: center !important;
        color: var(--text-color) !important; -webkit-text-fill-color: var(--text-color) !important;
    }
    </style>
""", unsafe_allow_html=True)

# Connect to Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- HELPER FUNCTIONS ---
def get_dynamic_shifts():
    """Fetches real-time shift list from the database."""
    try:
        res = supabase.table("shifts").select("shift_name").execute()
        if res.data:
            return [row["shift_name"] for row in res.data]
        return ["General"]
    except:
        return ["General"]

def generate_id_card(emp_id, name, department, mobile):
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
    return id_card

def check_punch_status(emp_id):
    today_ist_str = datetime.now(IST).strftime('%Y-%m-%d')
    res = supabase.table("attendance").select("*").eq("emp_id", emp_id).execute()
    
    if not res.data: return "Punch In"
        
    df = pd.DataFrame(res.data)
    df["time_logged"] = pd.to_datetime(df["time_logged"]).dt.tz_convert('Asia/Kolkata')
    df["date_only"] = df["time_logged"].dt.strftime('%Y-%m-%d')
    punches_today = len(df[df["date_only"] == today_ist_str])
    
    if punches_today == 0: return "Punch In"
    elif punches_today == 1: return "Punch Out"
    else: return "Limit Reached"

def render_shift_master_ui():
    """Centralized Shift Master UI for both HR and Super Admin."""
    st.markdown("### ⚙️ Shift Master Management")
    
    current_shifts = get_dynamic_shifts()
    st.info(f"**Current Active Shifts:** {', '.join(current_shifts)}")
    
    tab1, tab2, tab3 = st.tabs(["➕ Add Shift", "✏️ Edit Shift", "❌ Delete Shift"])
    
    with tab1:
        with st.form("add_shift_form", clear_on_submit=True):
            new_shift = st.text_input("New Shift Name (e.g., Weekend Shift)")
            if st.form_submit_button("Add Shift"):
                if new_shift:
                    try:
                        supabase.table("shifts").insert({"shift_name": new_shift}).execute()
                        st.success(f"✅ Added {new_shift} successfully!")
                        st.rerun()
                    except: st.error("⚠️ Shift already exists or database error.")

    with tab2:
        with st.form("edit_shift_form", clear_on_submit=True):
            old_shift = st.selectbox("Select Shift to Edit", current_shifts)
            edited_shift = st.text_input("Enter New Name")
            if st.form_submit_button("Update Shift"):
                if old_shift and edited_shift:
                    try:
                        # Update the shift list
                        supabase.table("shifts").update({"shift_name": edited_shift}).eq("shift_name", old_shift).execute()
                        # Auto-update all employees currently assigned to the old shift!
                        supabase.table("employees").update({"shift": edited_shift}).eq("shift", old_shift).execute()
                        st.success(f"✅ Changed {old_shift} to {edited_shift} and updated employees!")
                        st.rerun()
                    except: st.error("⚠️ Error updating shift.")

    with tab3:
        with st.form("delete_shift_form"):
            del_shift = st.selectbox("Select Shift to Remove", current_shifts)
            if st.form_submit_button("Delete Shift"):
                if del_shift:
                    try:
                        supabase.table("shifts").delete().eq("shift_name", del_shift).execute()
                        st.success(f"✅ Deleted {del_shift}!")
                        st.rerun()
                    except: st.error("⚠️ Error deleting shift.")

# --- SESSION STATE ---
if "hr_logged_in" not in st.session_state: st.session_state.hr_logged_in = False
if "hr_username" not in st.session_state: st.session_state.hr_username = ""
if "super_logged_in" not in st.session_state: st.session_state.super_logged_in = False
if "camera_key" not in st.session_state: st.session_state.camera_key = 1
if "success_msg" not in st.session_state: st.session_state.success_msg = ""
if "error_msg" not in st.session_state: st.session_state.error_msg = ""


# ==========================================
#         STATE 1: MAIN LOGIN SCREEN
# ==========================================
if not st.session_state.hr_logged_in and not st.session_state.super_logged_in:
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        if os.path.exists(logo_path):
            logo_col1, logo_col2, logo_col3 = st.columns([5, 2, 5])
            with logo_col2: st.image(logo_path, use_container_width=True)
                
        st.markdown("<h1>Joy Corporate Solutions</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 18px;'>Enterprise Attendance Portal</p><br>", unsafe_allow_html=True)
        
        login_type = st.selectbox("Select Portal Identity", ["HR User Portal", "Super Admin Portal"])
        st.write("<br>", unsafe_allow_html=True)
        
        if login_type == "HR User Portal":
            with st.form("hr_login_form"):
                st.markdown("### 🔐 HR Secure Login")
                hr_user_input = st.text_input("HR Username")
                hr_pass_input = st.text_input("HR Password", type="password")
                if st.form_submit_button("Authenticate"):
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
#         STATE 2: HR DASHBOARD
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
        hr_action = st.radio("Select Module:", ["⏱️ Record Attendance", "📊 View Logs", "👤 Enroll Employees", "👥 Employee Directory", "⚙️ Shift Master"], horizontal=True)
        st.write("<br>", unsafe_allow_html=True)
        
        # --- 1. RECORD ATTENDANCE ---
        if hr_action == "⏱️ Record Attendance":
            st.markdown("### ⏱️ Daily Attendance Capture (In / Out)")
            
            if st.session_state.success_msg:
                st.success(st.session_state.success_msg)
                st.session_state.success_msg = ""
            if st.session_state.error_msg:
                st.warning(st.session_state.error_msg)
                st.session_state.error_msg = ""
            
            tab1, tab2 = st.tabs(["📸 3D QR Scanner", "⌨️ Manual Entry"])
            
            with tab1:
                st.info("Maximum 2 scans per day (Punch In & Punch Out).")
                scan_image = st.camera_input("Scanner Camera", key=f"qr_cam_{st.session_state.camera_key}")
                
                if scan_image and st.button("Submit QR Attendance"):
                    bytes_data = scan_image.getvalue()
                    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                    detector = cv2.QRCodeDetector()
                    data, bbox, _ = detector.detectAndDecode(cv2_img)
                    
                    if data:
                        punch_type = check_punch_status(data)
                        if punch_type == "Limit Reached":
                            st.session_state.error_msg = f"⚠️ Limit Reached: Employee ID {data} has already Punched In and Out today!"
                        else:
                            supabase.table("attendance").insert({"emp_id": data, "method": "QR Code", "punch_type": punch_type}).execute()
                            st.session_state.success_msg = f"✅ {punch_type} successfully recorded for ID: **{data}**"
                        
                        st.session_state.camera_key += 1
                        st.rerun()
                    else: st.error("⚠️ No QR code detected. Please try again.")
            
            with tab2:
                with st.form("manual_entry_form", clear_on_submit=True):
                    manual_id = st.text_input("Enter Employee ID Number")
                    manual_submit = st.form_submit_button("Record Manual Punch")
                    
                    if manual_submit and manual_id:
                        punch_type = check_punch_status(manual_id)
                        if punch_type == "Limit Reached":
                            st.warning(f"⚠️ Limit Reached: Employee ID {manual_id} has already Punched In and Out today!")
                        else:
                            supabase.table("attendance").insert({"emp_id": manual_id, "method": "Manual Entry", "punch_type": punch_type}).execute()
                            st.success(f"✅ {punch_type} successfully recorded for ID: **{manual_id}**")
                        
        # --- 2. ENROLL EMPLOYEES ---
        elif hr_action == "👤 Enroll Employees":
            st.markdown("### 👤 Employee Enrollment")
            dynamic_shifts = get_dynamic_shifts()
            
            e_tab1, e_tab2 = st.tabs(["Single Enrollment", "Bulk Upload (CSV)"])
            
            with e_tab1:
                with st.form("enrollment_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        emp_id = st.text_input("Employee ID Number*")
                        name = st.text_input("Full Name*")
                    with col2:
                        department = st.text_input("Department")
                        mobile = st.text_input("Mobile Number")
                        shift = st.selectbox("Shift", dynamic_shifts)
                    
                    submit_button = st.form_submit_button("✨ Generate Profile & ID Card")
                
                if submit_button and emp_id and name:
                    try:
                        current_date = datetime.now(IST).strftime('%d-%m-%Y')
                        supabase.table("employees").insert({
                            "emp_id": emp_id, "name": name, "department": department,
                            "mobile": mobile, "shift": shift, "status": "Active", "status_updated_on": current_date
                        }).execute()
                        st.success(f"🎉 Profile created for {name}!")
                        
                        id_card = generate_id_card(emp_id, name, department, mobile)
                        img_col1, img_col2, img_col3 = st.columns([1, 2, 1])
                        with img_col2: st.image(id_card, caption=f"ID Card for {name} (Right-click to Save)")
                    except Exception as e: st.error("⚠️ Error saving. ID might already exist.")
                        
            with e_tab2:
                st.info("Upload a CSV file to enroll multiple employees at once.")
                st.markdown("**Required Columns:** `emp_id`, `name`, `department`, `mobile`, `shift`")
                
                sample_csv = "emp_id,name,department,mobile,shift\n1001,John Doe,Sales,9876543210,General\n1002,Jane Smith,IT,8765432109,1st shift"
                st.download_button("📥 Download Sample CSV Template", data=sample_csv, file_name="bulk_enroll_template.csv", mime="text/csv")
                
                uploaded_file = st.file_uploader("Upload Completed CSV", type=["csv"])
                if uploaded_file is not None:
                    if st.button("Process Bulk Enrollment"):
                        try:
                            df_upload = pd.read_csv(uploaded_file)
                            success_count = 0
                            current_date = datetime.now(IST).strftime('%d-%m-%Y')
                            
                            for index, row in df_upload.iterrows():
                                try:
                                    supabase.table("employees").insert({
                                        "emp_id": str(row['emp_id']), "name": str(row['name']), 
                                        "department": str(row.get('department', '')),
                                        "mobile": str(row.get('mobile', '')), "shift": str(row.get('shift', 'General')),
                                        "status": "Active", "status_updated_on": current_date
                                    }).execute()
                                    success_count += 1
                                except Exception as e: st.error(f"Failed to add ID {row['emp_id']} (Might be duplicate)")
                            
                            st.success(f"✅ Successfully enrolled {success_count} employees!")
                        except Exception as e: st.error("Error reading CSV. Ensure columns match the template exactly.")

        # --- 3. EMPLOYEE DIRECTORY ---
        elif hr_action == "👥 Employee Directory":
            st.markdown("### 👥 Lifecycle & ID Management")
            
            dir_tab1, dir_tab2, dir_tab3, dir_tab4 = st.tabs(["📋 Roster", "🪪 Download ID Cards", "🕒 Shift Mapping", "🔄 Status"])
            
            def get_all_employees():
                res = supabase.table("employees").select("*").execute()
                if res.data:
                    df = pd.DataFrame(res.data)
                    if "shift" not in df.columns: df["shift"] = "General"
                    if "status" not in df.columns: df["status"] = "Active"
                    if "status_updated_on" not in df.columns: df["status_updated_on"] = "N/A"
                    df["status"] = df["status"].fillna("Active")
                    df["shift"] = df["shift"].fillna("General")
                    return df
                return pd.DataFrame()
                
            df_emp_main = get_all_employees()
            dynamic_shifts = get_dynamic_shifts()
            
            with dir_tab1:
                if not df_emp_main.empty:
                    status_filter = st.radio("Filter By:", ["Active", "Left", "All"], horizontal=True)
                    df_filtered = df_emp_main if status_filter == "All" else df_emp_main[df_emp_main["status"] == status_filter]
                    
                    if not df_filtered.empty:
                        cols = ["emp_id", "name", "department", "shift", "mobile", "status"]
                        display_df = df_filtered[[c for c in cols if c in df_filtered.columns]].rename(columns={
                            "emp_id": "ID", "name": "Name", "department": "Dept", "shift": "Shift", "mobile": "Phone"
                        })
                        st.dataframe(display_df, use_container_width=True)
                    else: st.info("No employees found.")
                else: st.info("No employees enrolled yet.")
                
            with dir_tab2:
                st.markdown("#### Click to Download Employee ID Card")
                if not df_emp_main.empty:
                    active_emps = df_emp_main[df_emp_main["status"] == "Active"]
                    emp_dict = {f"{row['name']} (ID: {row['emp_id']})": row for _, row in active_emps.iterrows()}
                    selected_emp = st.selectbox("Select Employee to Generate ID", options=list(emp_dict.keys()))
                    
                    if selected_emp:
                        emp_data = emp_dict[selected_emp]
                        id_img = generate_id_card(emp_data['emp_id'], emp_data['name'], emp_data.get('department',''), emp_data.get('mobile',''))
                        
                        buf = io.BytesIO()
                        id_img.save(buf, format="PNG")
                        byte_im = buf.getvalue()
                        
                        st.image(id_img, width=300)
                        st.download_button(label=f"📥 Download ID for {emp_data['name']}", data=byte_im, file_name=f"ID_Card_{emp_data['emp_id']}.png", mime="image/png")
                else: st.info("No active employees available.")

            with dir_tab3:
                st.markdown("#### Shift Mapping")
                st.info("Assign shifts individually or upload a CSV for bulk mapping.")
                
                s_col1, s_col2 = st.columns(2)
                with s_col1:
                    with st.form("single_shift_form"):
                        st.markdown("**Individual Update**")
                        if not df_emp_main.empty:
                            emp_map_dict = {f"{r['name']} (ID: {r['emp_id']})": r['emp_id'] for _, r in df_emp_main.iterrows()}
                            map_sel = st.selectbox("Select Employee", list(emp_map_dict.keys()))
                            new_shift = st.selectbox("Assign Shift", dynamic_shifts)
                            if st.form_submit_button("Update Shift"):
                                emp_target_id = emp_map_dict[map_sel]
                                supabase.table("employees").update({"shift": new_shift}).eq("emp_id", emp_target_id).execute()
                                st.success(f"Shift updated to {new_shift}!")
                        else: st.write("No employees available.")
                with s_col2:
                    st.markdown("**Bulk Update**")
                    bulk_shift_csv = "emp_id,shift\n1001,1st shift\n1002,12Hr Day"
                    st.download_button("📥 Shift Mapping Template", data=bulk_shift_csv, file_name="shift_mapping.csv", mime="text/csv")
                    shift_file = st.file_uploader("Upload Shift CSV", type=["csv"])
                    if shift_file and st.button("Update Bulk Shifts"):
                        df_shifts = pd.read_csv(shift_file)
                        count = 0
                        for _, row in df_shifts.iterrows():
                            try:
                                supabase.table("employees").update({"shift": str(row['shift'])}).eq("emp_id", str(row['emp_id'])).execute()
                                count += 1
                            except: pass
                        st.success(f"Updated shifts for {count} employees!")

            with dir_tab4:
                with st.form("status_update_form"):
                    st.info("Log resignations or reactivations.")
                    c1, c2, c3 = st.columns(3)
                    with c1: update_id = st.text_input("Enter Employee ID")
                    with c2: new_status = st.selectbox("New Status", ["Left", "Active"])
                    with c3: eff_date = st.date_input("Effective Date", datetime.now(IST).date())
                    
                    if st.form_submit_button("Update Status") and update_id:
                        f_date = eff_date.strftime('%d-%m-%Y')
                        check = supabase.table("employees").select("*").eq("emp_id", update_id).execute()
                        if check.data:
                            supabase.table("employees").update({"status": new_status, "status_updated_on": f_date}).eq("emp_id", update_id).execute()
                            st.success(f"✅ Employee {update_id} updated to {new_status}!")
                        else: st.error("❌ Employee not found.")

        # --- 4. VIEW ATTENDANCE LOGS ---
        elif hr_action == "📊 View Logs":
            st.markdown("### 📊 Enterprise Attendance Reports")
            
            report_type = st.radio("Choose Report Type", ["Daily Report", "Monthly Report", "Custom Date Range"], horizontal=True)
            today = datetime.now(IST).date()
            report_name = ""
            st.write("<br>", unsafe_allow_html=True)
            
            if report_type == "Daily Report":
                search_date = st.date_input("Select Date", today)
                report_name = f"Daily_{search_date}"
            elif report_type == "Monthly Report":
                col1, col2 = st.columns(2)
                with col1:
                    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                    selected_month = st.selectbox("Month", months, index=today.month - 1)
                    month_num = months.index(selected_month) + 1
                with col2:
                    selected_year = st.selectbox("Year", range(today.year - 5, today.year + 5), index=5)
                report_name = f"Monthly_{selected_month}_{selected_year}"
            elif report_type == "Custom Date Range":
                date_range = st.date_input("Select Start and End Date", [today, today])
                if len(date_range) == 2: report_name = f"Custom_{date_range[0]}_to_{date_range[1]}"
                else: report_name = "Custom_Range"
            
            att_res = supabase.table("attendance").select("*").execute()
            emp_res = supabase.table("employees").select("emp_id, name, department, shift").execute()
            
            if att_res.data:
                df_att = pd.DataFrame(att_res.data)
                df_emp = pd.DataFrame(emp_res.data) if emp_res.data else pd.DataFrame(columns=["emp_id", "name", "department", "shift"])
                
                if "punch_type" not in df_att.columns: df_att["punch_type"] = "N/A"
                if not df_emp.empty: df = pd.merge(df_att, df_emp, on="emp_id", how="left")
                else:
                    df = df_att
                    df["name"], df["department"], df["shift"] = "Unknown", "Unknown", "Unknown"
                
                if "time_logged" in df.columns:
                    df["time_logged"] = pd.to_datetime(df["time_logged"]).dt.tz_convert('Asia/Kolkata')
                    df["date_only"] = df["time_logged"].dt.date
                    
                    if report_type == "Daily Report": df_filtered = df[df["date_only"] == search_date].copy()
                    elif report_type == "Monthly Report": df_filtered = df[(df["time_logged"].dt.month == month_num) & (df["time_logged"].dt.year == selected_year)].copy()
                    elif report_type == "Custom Date Range" and len(date_range) == 2:
                        df_filtered = df[(df["date_only"] >= date_range[0]) & (df["date_only"] <= date_range[1])].copy()
                    else: df_filtered = pd.DataFrame() 
                    
                    if not df_filtered.empty:
                        df_filtered["Date"] = df_filtered["time_logged"].dt.strftime('%d-%m-%Y')
                        df_filtered["Punch Time"] = df_filtered["time_logged"].dt.strftime('%I:%M %p')
                        
                        cols = ["emp_id", "name", "department", "shift", "Date", "Punch Time", "punch_type"]
                        df_filtered = df_filtered[[c for c in cols if c in df_filtered.columns]].rename(
                            columns={"emp_id": "ID", "name": "Name", "department": "Dept", "shift": "Shift", "punch_type": "Type"}
                        )
                        st.dataframe(df_filtered, use_container_width=True)
                        csv = df_filtered.to_csv(index=False).encode('utf-8')
                        st.download_button(f"📥 Export {report_name} CSV", data=csv, file_name=f'Joy_Attendance_{report_name}.csv', mime='text/csv')
                    else: st.info("No attendance records found for this date range.")
            else: st.info("No attendance records found yet.")
            
        # --- 5. SHIFT MASTER ---
        elif hr_action == "⚙️ Shift Master":
            render_shift_master_ui()

# ==========================================
#         STATE 3: SUPER ADMIN DASHBOARD
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
        sa_tab1, sa_tab2, sa_tab3 = st.tabs(["➕ Provision HR Accounts", "👥 Security Audit & Directory", "⚙️ Shift Master"])
        
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
                        except Exception: st.error("Error creating account. Ensure username is unique.")
        with sa_tab2:
            st.markdown("#### Security Roster")
            try:
                hr_list = supabase.table("hr_users").select("id, username").execute()
                if hr_list.data:
                    df_hr = pd.DataFrame(hr_list.data).rename(columns={"id": "System ID Node", "username": "HR Identity"})
                    st.dataframe(df_hr, use_container_width=True)
                else: st.info("No active nodes on network.")
            except Exception: st.error("Network error retrieving users.")
            
        with sa_tab3:
            render_shift_master_ui()
