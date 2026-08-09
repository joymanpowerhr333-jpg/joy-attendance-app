import streamlit as st
from supabase import create_client, Client
import qrcode
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta
import base64
import os
import io
from streamlit_qrcode_scanner import qrcode_scanner

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

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- HELPER FUNCTIONS ---
def get_shift_data():
    try:
        res = supabase.table("shifts").select("*").execute()
        if res.data: return pd.DataFrame(res.data)
        return pd.DataFrame()
    except: return pd.DataFrame()

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
        font_large, font_small = ImageFont.load_default(), ImageFont.load_default()
        
    draw.text((20, height), f"Name: {name}", fill="#1a365d", font=font_large)
    draw.text((20, height + 40), f"Emp ID: {emp_id}", fill="#1a365d", font=font_large)
    draw.text((20, height + 80), f"Dept: {department}", fill="#666666", font=font_small)
    draw.text((20, height + 110), f"Phone: {mobile}", fill="#666666", font=font_small)
    return id_card

def check_punch_status(emp_id):
    res = supabase.table("attendance").select("punch_type").eq("emp_id", emp_id).order("id", desc=True).limit(1).execute()
    if not res.data: return "Punch In"
    return "Punch In" if res.data[0]['punch_type'] == "Punch Out" else "Punch Out"

def render_shift_master_ui():
    st.markdown("### ⚙️ Shift Master Management")
    df_shifts = get_shift_data()
    
    if not df_shifts.empty:
        st.dataframe(df_shifts[["shift_name", "start_time", "duration_hrs", "break_mins"]].rename(
            columns={"shift_name": "Shift Name", "start_time": "Start Time", "duration_hrs": "Working Hrs", "break_mins": "Break (Mins)"}
        ), use_container_width=True)
        current_shifts = df_shifts["shift_name"].tolist()
    else: current_shifts = []

    ALLOWED_TIMES = [f"{str(h).zfill(2)}:{m}" for h in range(24) for m in ["00", "30"]]
    
    tab1, tab_bulk, tab2, tab3 = st.tabs(["➕ Add Shift", "📤 Bulk Upload", "✏️ Edit Shift", "❌ Delete Shift"])
    
    with tab1:
        with st.form("add_shift_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_shift = st.text_input("New Shift Name")
                start_time = st.selectbox("Shift Start Time", ALLOWED_TIMES, index=17) 
            with col2:
                duration = st.number_input("Working Hours", min_value=1.0, max_value=24.0, value=8.0, step=0.5)
                break_time = st.selectbox("Break Duration", [0, 30, 45, 60, 90, 120], format_func=lambda x: f"{x} Minutes")
                
            if st.form_submit_button("Add Shift") and new_shift:
                try:
                    supabase.table("shifts").insert({"shift_name": new_shift, "start_time": start_time, "duration_hrs": duration, "break_mins": break_time}).execute()
                    st.success(f"✅ Added {new_shift} successfully!")
                    st.rerun()
                except: st.error("⚠️ Shift already exists or database error.")
                
    with tab_bulk:
        st.info("Upload a CSV file to add multiple shifts at once.")
        st.markdown("**Required Columns:** `shift_name`, `start_time`, `duration_hrs`, `break_mins`")
        
        sample_shift_csv = "shift_name,start_time,duration_hrs,break_mins\nMorning A,06:00,8,30\nNight B,18:30,12,60"
        st.download_button("📥 Download Shift Template", data=sample_shift_csv, file_name="bulk_shifts_template.csv", mime="text/csv")
        
        shift_upload_file = st.file_uploader("Upload Shifts CSV", type=["csv"], key="bulk_shift_uploader")
        if shift_upload_file and st.button("Process Bulk Shifts"):
            try:
                df_shf_up = pd.read_csv(shift_upload_file)
                success_count = 0
                for _, row in df_shf_up.iterrows():
                    try:
                        supabase.table("shifts").insert({
                            "shift_name": str(row['shift_name']),
                            "start_time": str(row['start_time']).zfill(5), 
                            "duration_hrs": float(row['duration_hrs']),
                            "break_mins": int(row['break_mins'])
                        }).execute()
                        success_count += 1
                    except: pass 
                st.success(f"✅ Successfully added {success_count} shifts!")
                st.rerun()
            except Exception as e:
                st.error("Error reading CSV. Ensure columns match the template exactly.")

    with tab2:
        with st.form("edit_shift_form"):
            old_shift = st.selectbox("Select Shift to Edit", current_shifts)
            col1, col2 = st.columns(2)
            with col1:
                edited_shift = st.text_input("Enter New Name (Leave blank to keep same)")
                new_start = st.selectbox("New Start Time", ALLOWED_TIMES, index=17)
            with col2:
                new_dur = st.number_input("New Working Hours", min_value=1.0, max_value=24.0, value=8.0, step=0.5)
                new_brk = st.selectbox("New Break Duration", [0, 30, 45, 60, 90, 120])
                
            if st.form_submit_button("Update Shift"):
                final_name = edited_shift if edited_shift else old_shift
                try:
                    supabase.table("shifts").update({
                        "shift_name": final_name, "start_time": new_start, "duration_hrs": new_dur, "break_mins": new_brk
                    }).eq("shift_name", old_shift).execute()
                    
                    if edited_shift: 
                        supabase.table("employees").update({"shift": final_name}).eq("shift", old_shift).execute()
                    st.success(f"✅ Shift updated successfully!")
                    st.rerun()
                except: st.error("⚠️ Error updating shift.")

    with tab3:
        with st.form("delete_shift_form"):
            del_shift = st.selectbox("Select Shift to Remove", current_shifts)
            if st.form_submit_button("Delete Shift"):
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
if "last_scanned_id" not in st.session_state: st.session_state.last_scanned_id = None
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
                    else: st.error("❌ Invalid HR Username or Password.")
                        
        elif login_type == "Super Admin Portal":
            with st.form("super_login_form"):
                st.markdown("### 🛡️ Master Control Login")
                super_pass_input = st.text_input("Master Key Password", type="password")
                if st.form_submit_button("Authenticate Mainframe"):
                    if super_pass_input == "JoyMaster2026":
                        st.session_state.super_logged_in = True
                        st.rerun() 
                    else: st.error("❌ Invalid System Override.")


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
        hr_action = st.radio("Select Module:", ["⏱️ Record Attendance", "📊 Payroll & Logs", "👤 Enroll Employees", "👥 Directory", "⚙️ Shift Master"], horizontal=True)
        st.write("<br>", unsafe_allow_html=True)
        
        # --- 1. RECORD ATTENDANCE ---
        if hr_action == "⏱️ Record Attendance":
            st.markdown("### ⏱️ Daily Attendance Capture (In / Out)")
            
            tab1, tab2 = st.tabs(["📸 Live QR Scanner", "⌨️ Manual Entry"])
            
            with tab1:
                st.info("Scanner alternates automatically (Scan 1 = In, Scan 2 = Out). Point your camera at the QR code.")
                
                # IF A SCAN JUST HAPPENED: Show the confirmation screen
                if st.session_state.last_scanned_id:
                    if st.session_state.success_msg:
                        st.success(st.session_state.success_msg)
                    if st.session_state.error_msg:
                        st.error(st.session_state.error_msg)
                    
                    st.write("---")
                    if st.button("📸 Scan Next Employee", use_container_width=True):
                        # Clear the state and reset the camera
                        st.session_state.last_scanned_id = None
                        st.session_state.success_msg = ""
                        st.session_state.error_msg = ""
                        st.session_state.camera_key += 1
                        st.rerun()
                
                # IF NO SCAN YET: Show the active scanner
                else:
                    qr_code = qrcode_scanner(key=f"qr_cam_{st.session_state.camera_key}")
                    
                    if qr_code:
                        punch_type = check_punch_status(qr_code)
                        if punch_type == "Limit Reached":
                            st.session_state.error_msg = f"⚠️ Limit Reached: Employee ID {qr_code} has already Punched In and Out today!"
                        else:
                            supabase.table("attendance").insert({"emp_id": qr_code, "method": "QR Code", "punch_type": punch_type}).execute()
                            st.session_state.success_msg = f"✅ {punch_type} successfully recorded for ID: **{qr_code}**"
                        
                        # Lock in the scan to trigger the confirmation screen
                        st.session_state.last_scanned_id = qr_code
                        st.rerun()
            
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
            df_shifts = get_shift_data()
            dynamic_shifts = df_shifts["shift_name"].tolist() if not df_shifts.empty else ["General"]
            
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
                        shift = st.selectbox("Assigned Shift", dynamic_shifts)
                    
                    if st.form_submit_button("✨ Generate Profile & ID Card") and emp_id and name:
                        try:
                            current_date = datetime.now(IST).strftime('%d-%m-%Y')
                            supabase.table("employees").insert({
                                "emp_id": emp_id, "name": name, "department": department,
                                "mobile": mobile, "shift": shift, "status": "Active", "status_updated_on": current_date
                            }).execute()
                            st.success(f"🎉 Profile created for {name}!")
                            id_card = generate_id_card(emp_id, name, department, mobile)
                            img_col1, img_col2, img_col3 = st.columns([1, 2, 1])
                            with img_col2: st.image(id_card, caption=f"ID Card for {name}")
                        except: st.error("⚠️ Error saving. ID might already exist.")
                        
            with e_tab2:
                st.info("Upload a CSV file to enroll multiple employees at once.")
                sample_csv = "emp_id,name,department,mobile,shift\n1001,John Doe,Sales,9876543210,General\n1002,Jane Smith,IT,8765432109,1st shift"
                st.download_button("📥 Download Sample Template", data=sample_csv, file_name="bulk_enroll_template.csv", mime="text/csv")
                
                uploaded_file = st.file_uploader("Upload Completed CSV", type=["csv"])
                if uploaded_file and st.button("Process Bulk Enrollment"):
                    try:
                        df_upload = pd.read_csv(uploaded_file)
                        success_count = 0
                        for _, row in df_upload.iterrows():
                            try:
                                supabase.table("employees").insert({
                                    "emp_id": str(row['emp_id']), "name": str(row['name']), "department": str(row.get('department', '')),
                                    "mobile": str(row.get('mobile', '')), "shift": str(row.get('shift', 'General')),
                                    "status": "Active", "status_updated_on": datetime.now(IST).strftime('%d-%m-%Y')
                                }).execute()
                                success_count += 1
                            except: pass
                        st.success(f"✅ Successfully enrolled {success_count} employees!")
                    except: st.error("Error reading CSV.")

        # --- 3. EMPLOYEE DIRECTORY ---
        elif hr_action == "👥 Directory":
            st.markdown("### 👥 Lifecycle & ID Management")
            dir_tab1, dir_tab2, dir_tab3, dir_tab4 = st.tabs(["📋 Roster", "🪪 Download ID Cards", "🕒 Shift Mapping", "🔄 Status"])
            
            res = supabase.table("employees").select("*").execute()
            df_emp_main = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            df_shifts = get_shift_data()
            dynamic_shifts = df_shifts["shift_name"].tolist() if not df_shifts.empty else ["General"]
            
            with dir_tab1:
                if not df_emp_main.empty:
                    status_filter = st.radio("Filter By:", ["Active", "Left", "All"], horizontal=True)
                    df_filtered = df_emp_main if status_filter == "All" else df_emp_main[df_emp_main["status"] == status_filter]
                    if not df_filtered.empty:
                        st.dataframe(df_filtered[["emp_id", "name", "department", "shift", "mobile", "status"]].rename(
                            columns={"emp_id": "ID", "name": "Name", "department": "Dept", "shift": "Shift", "mobile": "Phone"}), use_container_width=True)
                    else: st.info("No employees found.")
                else: st.info("No employees enrolled yet.")
                
            with dir_tab2:
                if not df_emp_main.empty:
                    active_emps = df_emp_main[df_emp_main["status"] == "Active"]
                    emp_dict = {f"{r['name']} (ID: {r['emp_id']})": r for _, r in active_emps.iterrows()}
                    selected_emp = st.selectbox("Select Employee for ID Card", list(emp_dict.keys()))
                    if selected_emp:
                        ed = emp_dict[selected_emp]
                        id_img = generate_id_card(ed['emp_id'], ed['name'], ed.get('department',''), ed.get('mobile',''))
                        buf = io.BytesIO()
                        id_img.save(buf, format="PNG")
                        st.image(id_img, width=300)
                        st.download_button(label=f"📥 Download ID", data=buf.getvalue(), file_name=f"ID_Card_{ed['emp_id']}.png", mime="image/png")
                        
            with dir_tab3:
                s_col1, s_col2 = st.columns(2)
                with s_col1:
                    with st.form("single_shift_form"):
                        st.markdown("**Individual Update**")
                        if not df_emp_main.empty:
                            emp_map_dict = {f"{r['name']} (ID: {r['emp_id']})": r['emp_id'] for _, r in df_emp_main.iterrows()}
                            map_sel = st.selectbox("Select Employee", list(emp_map_dict.keys()))
                            new_shift = st.selectbox("Assign Shift", dynamic_shifts)
                            if st.form_submit_button("Update Shift"):
                                supabase.table("employees").update({"shift": new_shift}).eq("emp_id", emp_map_dict[map_sel]).execute()
                                st.success(f"Shift updated!")
                with s_col2:
                    st.markdown("**Bulk Update**")
                    bulk_shift_csv = "emp_id,shift\n1001,1st shift"
                    st.download_button("📥 Mapping Template", data=bulk_shift_csv, file_name="shift_mapping.csv", mime="text/csv")
                    shift_file = st.file_uploader("Upload Shift CSV", type=["csv"])
                    if shift_file and st.button("Update Bulk Shifts"):
                        df_shf = pd.read_csv(shift_file)
                        for _, row in df_shf.iterrows():
                            try: supabase.table("employees").update({"shift": str(row['shift'])}).eq("emp_id", str(row['emp_id'])).execute()
                            except: pass
                        st.success(f"Updated shifts successfully!")

            with dir_tab4:
                with st.form("status_update_form"):
                    c1, c2, c3 = st.columns(3)
                    with c1: update_id = st.text_input("Enter Employee ID")
                    with c2: new_status = st.selectbox("New Status", ["Left", "Active"])
                    with c3: eff_date = st.date_input("Effective Date", datetime.now(IST).date())
                    if st.form_submit_button("Update Status") and update_id:
                        f_date = eff_date.strftime('%d-%m-%Y')
                        supabase.table("employees").update({"status": new_status, "status_updated_on": f_date}).eq("emp_id", update_id).execute()
                        st.success(f"✅ Employee updated!")

        # --- 4. VIEW PAYROLL & LOGS ---
        elif hr_action == "📊 Payroll & Logs":
            st.markdown("### 📊 Automated Payroll & Penalty Calculation")
            
            report_type = st.radio("Choose Report Type", ["Daily Report", "Monthly Report", "Custom Date Range"], horizontal=True)
            today = datetime.now(IST).date()
            report_name = ""
            
            if report_type == "Daily Report":
                search_date = st.date_input("Select Date", today)
                report_name = f"Daily_{search_date}"
            elif report_type == "Monthly Report":
                c1, c2 = st.columns(2)
                with c1: selected_month = st.selectbox("Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], index=today.month - 1)
                with c2: selected_year = st.selectbox("Year", range(today.year - 5, today.year + 5), index=5)
                month_num = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"].index(selected_month) + 1
                report_name = f"Monthly_{selected_month}_{selected_year}"
            elif report_type == "Custom Date Range":
                date_range = st.date_input("Select Start and End Date", [today, today])
                report_name = f"Custom_Range" if len(date_range) != 2 else f"Custom_{date_range[0]}_to_{date_range[1]}"
            
            if st.button("Generate Payroll Report"):
                att_res = supabase.table("attendance").select("*").execute()
                emp_res = supabase.table("employees").select("emp_id, name, department, shift").execute()
                shift_res = supabase.table("shifts").select("*").execute()
                
                if att_res.data and emp_res.data and shift_res.data:
                    df_att = pd.DataFrame(att_res.data).sort_values(by=["emp_id", "time_logged"])
                    
                    records = []
                    for emp_id, grp in df_att.groupby("emp_id"):
                        current_in = None
                        for _, row in grp.iterrows():
                            if row["punch_type"] == "Punch In":
                                if current_in is not None:
                                    records.append({"emp_id": emp_id, "Punch In": current_in["time_logged"], "Punch Out": pd.NaT})
                                current_in = row
                            elif row["punch_type"] == "Punch Out" and current_in is not None:
                                records.append({"emp_id": emp_id, "Punch In": current_in["time_logged"], "Punch Out": row["time_logged"]})
                                current_in = None
                        if current_in is not None:
                            records.append({"emp_id": emp_id, "Punch In": current_in["time_logged"], "Punch Out": pd.NaT})
                    
                    df_pairs = pd.DataFrame(records)
                    
                    if not df_pairs.empty:
                        df_pairs['Punch In'] = pd.to_datetime(df_pairs['Punch In']).dt.tz_convert('Asia/Kolkata')
                        df_pairs['Punch Out'] = pd.to_datetime(df_pairs['Punch Out']).dt.tz_convert('Asia/Kolkata')
                        df_pairs['Shift Date'] = df_pairs['Punch In'].dt.date
                        
                        if report_type == "Daily Report": df_pairs = df_pairs[df_pairs["Shift Date"] == search_date]
                        elif report_type == "Monthly Report": df_pairs = df_pairs[(df_pairs['Punch In'].dt.month == month_num) & (df_pairs['Punch In'].dt.year == selected_year)]
                        elif report_type == "Custom Date Range" and len(date_range) == 2: df_pairs = df_pairs[(df_pairs["Shift Date"] >= date_range[0]) & (df_pairs["Shift Date"] <= date_range[1])]
                        
                        if not df_pairs.empty:
                            df_emp = pd.DataFrame(emp_res.data)
                            df_shf = pd.DataFrame(shift_res.data)
                            
                            df_merged = pd.merge(df_pairs, df_emp, on="emp_id", how="left")
                            df_merged = pd.merge(df_merged, df_shf.rename(columns={"shift_name": "shift"}), on="shift", how="left")
                            
                            df_merged['Start Limit'] = pd.to_datetime(df_merged['Shift Date'].astype(str) + ' ' + df_merged['start_time']).dt.tz_localize('Asia/Kolkata')
                            df_merged['End Limit'] = df_merged['Start Limit'] + pd.to_timedelta(df_merged['duration_hrs'], unit='h') + pd.to_timedelta(df_merged['break_mins'], unit='m')
                            
                            df_merged['Is_Late'] = df_merged['Punch In'] > df_merged['Start Limit']
                            df_merged['Is_Early'] = df_merged['Punch Out'].notna() & (df_merged['Punch Out'] < df_merged['End Limit'])
                            
                            df_merged['Status'] = 'Present'
                            df_merged.loc[df_merged['Is_Late'], 'Status'] = 'Half Day Absent (Late)'
                            df_merged.loc[df_merged['Punch Out'].isna(), 'Status'] = 'Missing Punch Out'
                            
                            df_merged['Worked Hrs'] = (df_merged['Punch Out'] - df_merged['Punch In']).dt.total_seconds() / 3600.0
                            df_merged['Effective Hrs'] = df_merged['Worked Hrs']
                            df_merged.loc[df_merged['Is_Early'], 'Effective Hrs'] = df_merged['Effective Hrs'] - 1.0 
                            
                            df_merged['Req Hrs'] = df_merged['duration_hrs'] + (df_merged['break_mins'] / 60.0)
                            df_merged['OT Hrs'] = (df_merged['Effective Hrs'] - df_merged['Req Hrs']).apply(lambda x: round(max(0, x), 2) if pd.notna(x) else 0)
                            
                            df_merged['Punch In Time'] = df_merged['Punch In'].dt.strftime('%I:%M %p')
                            df_merged['Punch Out Time'] = df_merged['Punch Out'].dt.strftime('%I:%M %p').fillna('--')
                            df_merged['Worked Hrs'] = df_merged['Worked Hrs'].round(2).fillna(0)
                            
                            cols = ["Shift Date", "emp_id", "name", "shift", "Punch In Time", "Punch Out Time", "Status", "Worked Hrs", "OT Hrs"]
                            final_report = df_merged[[c for c in cols if c in df_merged.columns]].rename(columns={"emp_id": "ID", "name": "Name", "shift": "Shift"})
                            
                            st.dataframe(final_report, use_container_width=True)
                            csv = final_report.to_csv(index=False).encode('utf-8')
                            st.download_button(f"📥 Export Payroll CSV", data=csv, file_name=f'Joy_Payroll_{report_name}.csv', mime='text/csv')
                        else: st.info("No records found for the selected dates.")
                    else: st.info("No records to process.")
                else: st.info("Not enough data to calculate payroll.")

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
