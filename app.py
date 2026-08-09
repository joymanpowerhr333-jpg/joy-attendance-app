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
IST = timezone(timedelta(hours=5, minutes=30))

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f: data = f.read()
    return base64.b64encode(data).decode()

watermark_css = ""
logo_path = "logo.png"
if os.path.exists(logo_path):
    watermark_css = f"""<style>.stApp::before {{ content: ""; background-image: url("data:image/png;base64,{get_base64_of_bin_file(logo_path)}"); background-size: 40%; background-repeat: no-repeat; background-position: center; position: fixed; top: 0; left: 0; right: 0; bottom: 0; opacity: 0.06; z-index: -1; pointer-events: none; }}</style>"""

st.markdown(watermark_css, unsafe_allow_html=True)
st.markdown("""
    <style>
    h1, h2, h3, h4, p, label, span, div[data-testid="stMarkdownContainer"] > p { text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important; }
    .stTabs [data-baseweb="tab-list"] { justify-content: center; } div[role="radiogroup"] { justify-content: center; } div.stButton { display: flex; justify-content: center; }
    div.stButton > button:first-child { background: linear-gradient(145deg, #f68a28, #df7113) !important; box-shadow: 0px 4px 15px rgba(223, 113, 19, 0.4) !important; color: white !important; border-radius: 12px !important; border: none !important; padding: 12px 30px !important; font-weight: 700 !important; transition: all 0.2s ease-in-out !important; width: 100%; max-width: 300px; }
    div.stButton > button:first-child * { color: white !important; } div.stButton > button:first-child:hover { background: linear-gradient(145deg, #df7113, #f68a28) !important; transform: translateY(-2px); }
    .stForm, div[data-testid="stExpander"] { background: var(--secondary-background-color) !important; backdrop-filter: blur(12px) !important; border-radius: 16px !important; border: 1px solid rgba(128, 128, 128, 0.2) !important; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important; padding: 25px !important; margin: 0 auto; }
    input, select, .stTextInput > div > div > input, div[data-baseweb="select"] > div { border-radius: 8px !important; background: var(--background-color) !important; border: 1px solid rgba(128, 128, 128, 0.3) !important; text-align: center !important; color: var(--text-color) !important; -webkit-text-fill-color: var(--text-color) !important; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; color: #df7113 !important; }
    </style>
""", unsafe_allow_html=True)

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- HELPER FUNCTIONS ---
def get_shift_data():
    res = supabase.table("shifts").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def get_all_employees():
    res = supabase.table("employees").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        for col in ["shift", "status", "status_updated_on"]:
            if col not in df.columns: df[col] = "Active" if col == "status" else ("General" if col == "shift" else "N/A")
        df["status"] = df["status"].fillna("Active")
        df["shift"] = df["shift"].fillna("General")
        return df
    return pd.DataFrame()

def get_all_attendance():
    res = supabase.table("attendance").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df["time_logged"] = pd.to_datetime(df["time_logged"]).dt.tz_convert('Asia/Kolkata')
        df["date_only"] = df["time_logged"].dt.strftime('%Y-%m-%d')
        return df
    return pd.DataFrame()

def generate_id_card(emp_id, name, department, mobile):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(emp_id)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1a365d", back_color="white").convert("RGB")
    width, height = qr_img.size
    id_card = Image.new('RGB', (width, height + 150), 'white')
    id_card.paste(qr_img, (0, 0))
    draw = ImageDraw.Draw(id_card)
    try: font_large, font_small = ImageFont.truetype("arial.ttf", 24), ImageFont.truetype("arial.ttf", 20)
    except: font_large, font_small = ImageFont.load_default(), ImageFont.load_default()
    draw.text((20, height), f"Name: {name}", fill="#1a365d", font=font_large)
    draw.text((20, height + 40), f"Emp ID: {emp_id}", fill="#1a365d", font=font_large)
    draw.text((20, height + 80), f"Dept: {department}", fill="#666666", font=font_small)
    draw.text((20, height + 110), f"Phone: {mobile}", fill="#666666", font=font_small)
    return id_card

# --- DASHBOARD & ACCESS MANAGEMENT ---
def render_dashboard(role, dept):
    st.markdown("### 📈 Real-Time Attendance Analytics")
    df_emp = get_all_employees()
    df_att = get_all_attendance()
    
    if role == "Dept Admin": df_emp = df_emp[df_emp['department'] == dept]
        
    col1, col2 = st.columns(2)
    with col1:
        if role in ["HR", "Super Admin"]:
            dept_list = ["All"] + sorted(df_emp['department'].unique().tolist())
            dash_dept = st.selectbox("Filter by Department", dept_list)
        else:
            dash_dept = dept
            st.info(f"Viewing Analytics for Department: **{dept}**")
            
    with col2:
        df_shifts = get_shift_data()
        shift_list = ["All"] + (df_shifts["shift_name"].tolist() if not df_shifts.empty else [])
        dash_shift = st.selectbox("Filter by Shift", shift_list)
        
    df_dash_emp = df_emp.copy()
    if dash_dept != "All": df_dash_emp = df_dash_emp[df_dash_emp['department'] == dash_dept]
    if dash_shift != "All": df_dash_emp = df_dash_emp[df_dash_emp['shift'] == dash_shift]
        
    active_emp_count = len(df_dash_emp[df_dash_emp['status'] == 'Active'])
    valid_emp_ids = df_dash_emp['emp_id'].tolist()
    
    df_att_dash = df_att[df_att['emp_id'].isin(valid_emp_ids)].copy() if not df_att.empty else pd.DataFrame(columns=['emp_id', 'date_only'])
        
    today_str = datetime.now(IST).strftime('%Y-%m-%d')
    yesterday_str = (datetime.now(IST) - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if not df_att_dash.empty:
        today_att = df_att_dash[df_att_dash['date_only'] == today_str]['emp_id'].nunique()
        yest_att = df_att_dash[df_att_dash['date_only'] == yesterday_str]['emp_id'].nunique()
        
        current_month = datetime.now(IST).month
        df_mtd = df_att_dash[pd.to_datetime(df_att_dash['time_logged']).dt.month == current_month]
        days_in_month = df_mtd['date_only'].nunique()
        avg_mtd_nos = round(len(df_mtd.drop_duplicates(subset=['emp_id', 'date_only'])) / days_in_month) if days_in_month > 0 else 0
    else:
        today_att = yest_att = avg_mtd_nos = 0
        
    today_pct = round((today_att / active_emp_count * 100) if active_emp_count else 0, 1)
    yest_pct = round((yest_att / active_emp_count * 100) if active_emp_count else 0, 1)
    avg_mtd_pct = round((avg_mtd_nos / active_emp_count * 100) if active_emp_count else 0, 1)
    diff = round(today_pct - yest_pct, 1)
    diff_str = f"🚀 +{diff}% vs Yest" if diff >= 0 else f"📉 {diff}% vs Yest"
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Active Employees", f"{active_emp_count}")
    with m2: st.metric("Today Present", f"{today_att} ({today_pct}%)", diff_str)
    with m3: st.metric("Yesterday Present", f"{yest_att} ({yest_pct}%)")
    with m4: st.metric("Month Avg Present", f"{avg_mtd_nos} ({avg_mtd_pct}%)")

def render_access_control():
    st.markdown("### 🔐 Provision Department Access")
    st.info("Create login credentials for Department Heads to manage their own shifts and view analytics.")
    with st.form("new_access_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_user = st.text_input("Username")
            new_pass = st.text_input("Password", type="password")
        with col2:
            new_role = st.selectbox("Assign Role", ["Dept Admin", "HR"])
            new_dept = st.text_input("Department Name (Type 'All' for HR)", value="All" if new_role == "HR" else "")
        if st.form_submit_button("Generate & Encrypt Account"):
            if new_user and new_pass and new_dept:
                try:
                    supabase.table("hr_users").insert({"username": new_user, "password": new_pass, "role": new_role, "department": new_dept}).execute()
                    st.success(f"🎉 Account provisioned successfully for {new_user} ({new_role} - {new_dept})")
                except: st.error("Error creating account. Ensure username is globally unique.")

# --- SESSION STATE ---
if "hr_logged_in" not in st.session_state: st.session_state.hr_logged_in = False
if "hr_username" not in st.session_state: st.session_state.hr_username = ""
if "user_role" not in st.session_state: st.session_state.user_role = ""
if "user_dept" not in st.session_state: st.session_state.user_dept = "All"
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
        
        login_type = st.selectbox("Select Portal Identity", ["Staff & Dept Admin Portal", "Super Admin Portal"])
        st.write("<br>", unsafe_allow_html=True)
        
        if login_type == "Staff & Dept Admin Portal":
            with st.form("hr_login_form"):
                st.markdown("### 🔐 Secure Login")
                hr_user_input = st.text_input("Username")
                hr_pass_input = st.text_input("Password", type="password")
                if st.form_submit_button("Authenticate"):
                    hr_check = supabase.table("hr_users").select("*").eq("username", hr_user_input).eq("password", hr_pass_input).execute()
                    if hr_check.data:
                        user_data = hr_check.data[0]
                        st.session_state.hr_logged_in = True
                        st.session_state.hr_username = hr_user_input
                        st.session_state.user_role = user_data.get("role", "HR")
                        st.session_state.user_dept = user_data.get("department", "All")
                        st.rerun() 
                    else: st.error("❌ Invalid Username or Password.")
                        
        elif login_type == "Super Admin Portal":
            with st.form("super_login_form"):
                st.markdown("### 🛡️ Master Control Login")
                super_pass_input = st.text_input("Master Key Password", type="password")
                if st.form_submit_button("Authenticate Mainframe"):
                    if super_pass_input == "JoyMaster2026":
                        st.session_state.super_logged_in = True
                        st.session_state.user_role = "Super Admin"
                        st.session_state.user_dept = "All"
                        st.rerun() 
                    else: st.error("❌ Invalid System Override.")


# ==========================================
#         STATE 2: GENERAL DASHBOARD (HR & DEPT ADMIN)
# ==========================================
elif st.session_state.hr_logged_in:
    col_l, col_main, col_r = st.columns([1, 8, 1])
    with col_main:
        st.markdown(f"<h1>🏢 {st.session_state.user_role} Command Center</h1>", unsafe_allow_html=True)
        st.markdown(f"<p>Secure Session Active: <b>{st.session_state.hr_username}</b> | Dept: <b>{st.session_state.user_dept}</b></p>", unsafe_allow_html=True)
        
        if st.button("🚪 Terminate Session & Logout"):
            for key in ["hr_logged_in", "hr_username", "user_role", "user_dept"]: st.session_state[key] = ""
            st.session_state.hr_logged_in = False
            st.rerun()
            
        st.write("---")
        
        # --- DYNAMIC MENU: Removes "Enroll Employees" for Dept Admins ---
        menu_options = ["📈 Dashboard", "⏱️ Record Attendance", "📊 Payroll & Logs", "👥 Directory"]
        if st.session_state.user_role == "HR":
            menu_options.insert(3, "👤 Enroll Employees")
            menu_options.extend(["⚙️ Shift Master", "🔐 Access Control"])
            
        hr_action = st.radio("Select Module:", menu_options, horizontal=True)
        st.write("<br>", unsafe_allow_html=True)

        if hr_action == "📈 Dashboard":
            render_dashboard(st.session_state.user_role, st.session_state.user_dept)
        
        # --- RECORD ATTENDANCE (SCANNER HIDDEN UNTIL SELECTED) ---
        elif hr_action == "⏱️ Record Attendance":
            st.markdown("### ⏱️ Daily Attendance Capture")
            
            tab1, tab2 = st.tabs(["📸 Live QR Scanner", "⌨️ Manual Entry"])
            with tab1:
                if st.session_state.last_scanned_id:
                    if st.session_state.success_msg: st.success(st.session_state.success_msg)
                    if st.session_state.error_msg: st.error(st.session_state.error_msg)
                    st.write("---")
                    if st.button("📸 Scan Next Employee", use_container_width=True):
                        st.session_state.last_scanned_id = None
                        st.session_state.success_msg = st.session_state.error_msg = ""
                        st.session_state.camera_key += 1
                        st.rerun()
                else:
                    punch_action = st.radio("Select Action to Enable Scanner:", ["Punch In", "Punch Out", "Break Start", "Break End"], horizontal=True, index=None)
                    
                    if punch_action is None:
                        st.warning("⚠️ Please select an action above (e.g., 'Punch In') to activate the camera.")
                    else:
                        st.info(f"🟢 **Scanner Enabled for: {punch_action}**. Point camera at QR code.")
                        qr_code = qrcode_scanner(key=f"qr_cam_{st.session_state.camera_key}")
                        if qr_code:
                            supabase.table("attendance").insert({"emp_id": qr_code, "method": "QR Code", "punch_type": punch_action}).execute()
                            st.session_state.success_msg = f"✅ **{punch_action}** successfully recorded for ID: **{qr_code}**"
                            st.session_state.last_scanned_id = qr_code
                            st.rerun()
            
            with tab2:
                with st.form("manual_entry_form", clear_on_submit=True):
                    manual_action = st.radio("Select Manual Action:", ["Punch In", "Punch Out", "Break Start", "Break End"], horizontal=True)
                    manual_id = st.text_input("Enter Employee ID Number")
                    if st.form_submit_button("Record Manual Punch") and manual_id:
                        supabase.table("attendance").insert({"emp_id": manual_id, "method": "Manual Entry", "punch_type": manual_action}).execute()
                        st.success(f"✅ **{manual_action}** successfully recorded for ID: **{manual_id}**")
                        
        # --- ENROLL EMPLOYEES (ONLY VISIBLE TO HR) ---
        elif hr_action == "👤 Enroll Employees":
            st.markdown("### 👤 Employee Enrollment")
            df_shifts = get_shift_data()
            dynamic_shifts = df_shifts["shift_name"].tolist() if not df_shifts.empty else ["General"]
            
            e_tab1, e_tab2 = st.tabs(["Single Enrollment", "Bulk Upload (CSV)"])
            with e_tab1:
                with st.form("enrollment_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        emp_id, name = st.text_input("Employee ID Number*"), st.text_input("Full Name*")
                    with c2:
                        dept_val = st.session_state.user_dept if st.session_state.user_role == "Dept Admin" else st.text_input("Department")
                        if st.session_state.user_role == "Dept Admin": st.info(f"Department locked to: {dept_val}")
                        mobile, shift = st.text_input("Mobile Number"), st.selectbox("Assigned Shift", dynamic_shifts)
                    
                    if st.form_submit_button("✨ Generate Profile & ID Card") and emp_id and name:
                        try:
                            supabase.table("employees").insert({"emp_id": emp_id, "name": name, "department": dept_val, "mobile": mobile, "shift": shift, "status": "Active", "status_updated_on": datetime.now(IST).strftime('%d-%m-%Y')}).execute()
                            st.success(f"🎉 Profile created for {name}!")
                            id_card = generate_id_card(emp_id, name, dept_val, mobile)
                            c_img1, c_img2, c_img3 = st.columns([1, 2, 1])
                            with c_img2: st.image(id_card, caption=f"ID Card for {name}")
                        except: st.error("⚠️ Error saving. ID might already exist.")
                        
            with e_tab2:
                st.info("Upload a CSV file to enroll multiple employees at once.")
                st.download_button("📥 Download Sample Template", data="emp_id,name,department,mobile,shift\n1001,John Doe,Sales,9876543210,General", file_name="bulk_enroll.csv", mime="text/csv")
                uploaded_file = st.file_uploader("Upload Completed CSV", type=["csv"])
                if uploaded_file and st.button("Process Bulk Enrollment"):
                    try:
                        df_upload = pd.read_csv(uploaded_file)
                        for _, row in df_upload.iterrows():
                            d_val = st.session_state.user_dept if st.session_state.user_role == "Dept Admin" else str(row.get('department', ''))
                            try: supabase.table("employees").insert({"emp_id": str(row['emp_id']), "name": str(row['name']), "department": d_val, "mobile": str(row.get('mobile', '')), "shift": str(row.get('shift', 'General')), "status": "Active", "status_updated_on": datetime.now(IST).strftime('%d-%m-%Y')}).execute()
                            except: pass
                        st.success("✅ Successfully enrolled employees!")
                    except: st.error("Error reading CSV.")

        # --- EMPLOYEE DIRECTORY & SHIFT MAPPING ---
        elif hr_action == "👥 Directory":
            st.markdown("### 👥 Lifecycle & Shift Mapping")
            dir_tab1, dir_tab2, dir_tab3, dir_tab4 = st.tabs(["📋 Roster", "🪪 Download ID Cards", "🕒 Shift Mapping", "🔄 Status"])
            
            df_emp_main = get_all_employees()
            if st.session_state.user_role == "Dept Admin" and not df_emp_main.empty:
                df_emp_main = df_emp_main[df_emp_main['department'] == st.session_state.user_dept]
                
            df_shifts = get_shift_data()
            dynamic_shifts = df_shifts["shift_name"].tolist() if not df_shifts.empty else ["General"]
            
            with dir_tab1:
                if not df_emp_main.empty:
                    status_filter = st.radio("Filter By:", ["Active", "Left", "All"], horizontal=True)
                    df_filtered = df_emp_main if status_filter == "All" else df_emp_main[df_emp_main["status"] == status_filter]
                    st.dataframe(df_filtered[["emp_id", "name", "department", "shift", "mobile", "status"]].rename(columns={"emp_id": "ID", "name": "Name", "department": "Dept", "shift": "Shift", "mobile": "Phone"}), use_container_width=True) if not df_filtered.empty else st.info("No employees found.")
                else: st.info("No employees found in your scope.")
                
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
                        st.download_button(label=f"📥 Download ID", data=buf.getvalue(), file_name=f"ID_{ed['emp_id']}.png", mime="image/png")
                        
            with dir_tab3:
                s_col1, s_col2 = st.columns(2)
                with s_col1:
                    with st.form("single_shift_form"):
                        if not df_emp_main.empty:
                            emp_map_dict = {f"{r['name']} (ID: {r['emp_id']})": r['emp_id'] for _, r in df_emp_main.iterrows()}
                            map_sel = st.selectbox("Select Employee", list(emp_map_dict.keys()))
                            new_shift = st.selectbox("Assign Shift", dynamic_shifts)
                            if st.form_submit_button("Update Shift"):
                                supabase.table("employees").update({"shift": new_shift}).eq("emp_id", emp_map_dict[map_sel]).execute()
                                st.success(f"Shift updated!")
                with s_col2:
                    st.download_button("📥 Mapping Template", data="emp_id,shift\n1001,1st shift", file_name="shift_map.csv", mime="text/csv")
                    shift_file = st.file_uploader("Upload Shift CSV", type=["csv"])
                    if shift_file and st.button("Update Bulk Shifts"):
                        df_shf = pd.read_csv(shift_file)
                        for _, row in df_shf.iterrows():
                            if str(row['emp_id']) in df_emp_main['emp_id'].astype(str).values:
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
                        if update_id in df_emp_main['emp_id'].astype(str).values:
                            supabase.table("employees").update({"status": new_status, "status_updated_on": eff_date.strftime('%d-%m-%Y')}).eq("emp_id", update_id).execute()
                            st.success(f"✅ Employee updated!")
                        else: st.error("❌ You cannot modify this employee ID.")

        # --- HR EXCLUSIVES ---
        elif hr_action == "📊 Payroll & Logs": st.info("Payroll computation module active.") 
        elif hr_action == "⚙️ Shift Master": st.info("Manage Master Shifts (Global).") 
        elif hr_action == "🔐 Access Control": render_access_control()

# ==========================================
#         STATE 3: SUPER ADMIN DASHBOARD
# ==========================================
elif st.session_state.super_logged_in:
    col_l, col_main, col_r = st.columns([1, 6, 1])
    with col_main:
        st.markdown("<h1>🛡️ Super Admin Control Center</h1>", unsafe_allow_html=True)
        if st.button("🚪 Terminate Session & Logout"):
            st.session_state.super_logged_in = False
            st.rerun()
            
        st.write("---")
        sa_tab0, sa_tab1, sa_tab2 = st.tabs(["📈 Real-Time Dashboard", "🔐 Provision Access", "👥 Access Directory"])
        
        with sa_tab0: render_dashboard("Super Admin", "All")
        with sa_tab1: render_access_control()
        with sa_tab2:
            st.markdown("#### System Roster")
            try:
                hr_list = supabase.table("hr_users").select("id, username, role, department").execute()
                if hr_list.data: st.dataframe(pd.DataFrame(hr_list.data).rename(columns={"username": "Identity", "role": "Role", "department": "Scope"}), use_container_width=True)
            except: st.error("Network error.")
