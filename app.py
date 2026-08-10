import streamlit as st
from supabase import create_client, Client
import qrcode
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta
import base64
import os
import io
from streamlit_qrcode_scanner import qrcode_scanner

# --- SESSION STATE INITIALIZATION (MUST BE FIRST) ---
if "hr_logged_in" not in st.session_state: 
    st.session_state.hr_logged_in = False
if "hr_username" not in st.session_state: 
    st.session_state.hr_username = ""
if "user_role" not in st.session_state: 
    st.session_state.user_role = ""
if "user_dept" not in st.session_state: 
    st.session_state.user_dept = "All"
if "super_logged_in" not in st.session_state: 
    st.session_state.super_logged_in = False
if "camera_key" not in st.session_state: 
    st.session_state.camera_key = 1
if "last_scanned_id" not in st.session_state: 
    st.session_state.last_scanned_id = None
if "success_msg" not in st.session_state: 
    st.session_state.success_msg = ""
if "error_msg" not in st.session_state: 
    st.session_state.error_msg = ""
if "show_id_card" not in st.session_state: 
    st.session_state.show_id_card = False

# --- PAGE CONFIGURATION & ALIGNMENT STYLING ---
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
    h1, h2, h3, h4 { text-align: left !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important; color: #1a365d; }
    p, label, span, div[data-testid="stMarkdownContainer"] > p { text-align: left !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important; }
    
    .stTabs [data-baseweb="tab-list"] { justify-content: flex-start; } 
    div[role="radiogroup"] { justify-content: flex-start; } 
    
    div.stButton > button:first-child { 
        background: linear-gradient(145deg, #f68a28, #df7113) !important; 
        box-shadow: 0px 4px 15px rgba(223, 113, 19, 0.4) !important; 
        color: white !important; border-radius: 12px !important; border: none !important; 
        padding: 10px 24px !important; font-weight: 700 !important; transition: all 0.2s ease-in-out !important; 
    }
    div.stButton > button:first-child * { color: white !important; } 
    div.stButton > button:first-child:hover { background: linear-gradient(145deg, #df7113, #f68a28) !important; transform: translateY(-2px); }
    
    .stForm, div[data-testid="stExpander"] { 
        background: var(--secondary-background-color) !important; backdrop-filter: blur(12px) !important; 
        border-radius: 16px !important; border: 1px solid rgba(128, 128, 128, 0.2) !important; 
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important; padding: 25px !important; 
    }
    
    input, select, .stTextInput > div > div > input, div[data-baseweb="select"] > div { 
        border-radius: 8px !important; background: var(--background-color) !important; 
        border: 1px solid rgba(128, 128, 128, 0.3) !important; text-align: left !important; 
        color: var(--text-color) !important; -webkit-text-fill-color: var(--text-color) !important; 
    }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #df7113 !important; }
    
    /* Hide password visibility */
    input[type="password"] { -webkit-text-security: disc !important; }
    </style>
""", unsafe_allow_html=True)

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- HELPER DATABASE FUNCTIONS ---
def get_shift_data():
    try:
        res = supabase.table("shifts").select("*").execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            for col in ['punch_in_time', 'punch_out_time', 'break_out_time', 'break_complete_time']:
                if col not in df.columns: df[col] = '09:00' if 'in' in col else ('18:00' if 'out' in col else '13:00')
        return df
    except: return pd.DataFrame()

def get_all_employees():
    try:
        res = supabase.table("employees").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['emp_id'] = df['emp_id'].astype(str)
            for col in ["shift", "status", "status_updated_on"]:
                if col not in df.columns: df[col] = "Active" if col == "status" else ("General" if col == "shift" else "N/A")
            df["status"] = df["status"].fillna("Active")
            df["shift"] = df["shift"].fillna("General")
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def get_all_attendance():
    try:
        res = supabase.table("attendance").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['emp_id'] = df['emp_id'].astype(str)
            df["time_logged"] = pd.to_datetime(df["time_logged"]).dt.tz_convert('Asia/Kolkata')
            df["date_only"] = df["time_logged"].dt.strftime('%Y-%m-%d')
            if "early_leave_approved" not in df.columns: df["early_leave_approved"] = False
            if "early_leave_requested" not in df.columns: df["early_leave_requested"] = False
            if "remarks" not in df.columns: df["remarks"] = ""
            if "punch_type" not in df.columns: df["punch_type"] = "Punch In"
            if "requested_by" not in df.columns: df["requested_by"] = ""
            if "approved_by" not in df.columns: df["approved_by"] = ""
            df["early_leave_approved"] = df["early_leave_approved"].fillna(False)
            df["early_leave_requested"] = df["early_leave_requested"].fillna(False)
            df["remarks"] = df["remarks"].fillna("")
            df["punch_type"] = df["punch_type"].fillna("Punch In")
            df["requested_by"] = df["requested_by"].fillna("")
            df["approved_by"] = df["approved_by"].fillna("")
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def generate_id_card(emp_id, name, department, mobile):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(str(emp_id))
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

# --- EARLY LEAVE REQUEST FUNCTIONS ---
def request_early_leave(emp_id, date_str, reason, requested_by):
    """Request early leave approval (Dept Admin only)"""
    try:
        # Check if record exists
        existing = supabase.table("attendance").select("*").eq("emp_id", emp_id).eq("date_only", date_str).execute()
        
        if existing.data:
            # Update existing record with request
            supabase.table("attendance").update({
                "early_leave_requested": True,
                "early_leave_approved": False,
                "remarks": reason,
                "requested_by": requested_by,
                "approved_by": ""
            }).eq("emp_id", emp_id).eq("date_only", date_str).execute()
        else:
            # Create new record with request
            now_ts = datetime.combine(datetime.strptime(date_str, '%Y-%m-%d').date(), datetime.now(IST).time()).isoformat()
            supabase.table("attendance").insert({
                "emp_id": emp_id,
                "method": "Request",
                "punch_type": "Punch Out",
                "early_leave_requested": True,
                "early_leave_approved": False,
                "remarks": reason,
                "requested_by": requested_by,
                "approved_by": "",
                "time_logged": now_ts,
                "date_only": date_str
            }).execute()
        return True, "Early leave request submitted successfully! Waiting for HR approval."
    except Exception as e:
        return False, f"Error submitting request: {str(e)}"

def approve_early_leave(emp_id, date_str, approved, remarks, approver):
    """Approve or reject early leave request (HR only)"""
    try:
        supabase.table("attendance").update({
            "early_leave_approved": approved,
            "remarks": remarks,
            "approved_by": approver
        }).eq("emp_id", emp_id).eq("date_only", date_str).execute()
        status = "approved" if approved else "rejected"
        return True, f"Early leave {status} successfully by {approver}!"
    except Exception as e:
        return False, f"Error approving request: {str(e)}"

# --- SEPARATE EARLY LEAVE FUNCTIONS FOR DIFFERENT ROLES ---
def render_dept_request_tab(df_emp_main):
    """Department Admin - Only can request early leave"""
    st.markdown("##### 📝 Submit Early Leave Request")
    
    if df_emp_main.empty:
        st.warning("No employees found in your department.")
        return
    
    with st.form("early_leave_request_form"):
        c1, c2 = st.columns(2)
        with c1:
            emp_req_dict = {f"{r['name']} (ID: {r['emp_id']})": str(r['emp_id']) for _, r in df_emp_main.iterrows()}
            req_emp = st.selectbox("Select Employee", list(emp_req_dict.keys()))
        with c2:
            req_date = st.date_input("Date of Early Leave", datetime.now(IST).date())
            req_reason = st.text_area("Reason for Early Leave", placeholder="Please provide detailed reason...", height=100)
        
        st.info("ℹ️ Your request will be sent to HR for approval.")
        
        if st.form_submit_button("📤 Submit Request"):
            if req_emp and req_reason:
                emp_id_val = emp_req_dict[req_emp]
                success, message = request_early_leave(
                    emp_id_val,
                    req_date.strftime('%Y-%m-%d'),
                    req_reason,
                    st.session_state.hr_username
                )
                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please fill all required fields.")
    
    # Show pending requests for this department
    st.markdown("---")
    st.markdown("##### 📋 Your Pending Requests")
    df_att_all = get_all_attendance()
    if not df_att_all.empty:
        dept_emp_ids = df_emp_main['emp_id'].tolist()
        pending_reqs = df_att_all[
            (df_att_all['emp_id'].isin(dept_emp_ids)) &
            (df_att_all['early_leave_requested'] == True) &
            (df_att_all['early_leave_approved'] == False)
        ].copy()
        
        if not pending_reqs.empty:
            pending_reqs = pd.merge(
                pending_reqs,
                df_emp_main[['emp_id', 'name', 'department']],
                on='emp_id',
                how='left'
            )
            st.dataframe(
                pending_reqs[['emp_id', 'name', 'department', 'date_only', 'remarks']].rename(
                    columns={'emp_id': 'ID', 'name': 'Name', 'department': 'Dept', 'date_only': 'Date', 'remarks': 'Reason'}
                ),
                use_container_width=True
            )
        else:
            st.info("No pending requests.")

def render_hr_approval_tab(df_att_all, df_emp_main):
    """HR - Only can approve/reject early leave requests"""
    st.markdown("##### ✅ Approve/Reject Early Leave Requests")
    
    if df_att_all.empty:
        st.info("No attendance records found.")
        return
    
    pending_requests = df_att_all[
        (df_att_all['early_leave_requested'] == True) & 
        (df_att_all['early_leave_approved'] == False)
    ].copy()
    
    if pending_requests.empty:
        st.info("No pending early leave requests.")
        return
    
    # Merge with employee data
    pending_requests = pd.merge(
        pending_requests,
        df_emp_main[['emp_id', 'name', 'department']],
        on='emp_id',
        how='left'
    )
    
    st.dataframe(
        pending_requests[['emp_id', 'name', 'department', 'date_only', 'remarks', 'requested_by']].rename(
            columns={'emp_id': 'ID', 'name': 'Name', 'department': 'Dept', 'date_only': 'Date', 'remarks': 'Reason', 'requested_by': 'Requested By'}
        ),
        use_container_width=True
    )
    
    st.write("---")
    st.markdown("##### Process Request")
    
    with st.form("approve_early_leave_form"):
        c1, c2 = st.columns(2)
        with c1:
            request_options = [
                f"{row['name']} (ID: {row['emp_id']}) - {row['date_only']}"
                for _, row in pending_requests.iterrows()
            ]
            selected_request = st.selectbox("Select Request to Process", request_options)
        with c2:
            approval_status = st.selectbox("Decision", ["✅ Approve", "❌ Reject"])
            approver_remarks = st.text_area("Approver Remarks", placeholder="Add any additional notes...", height=100)
        
        if st.form_submit_button("Process Request"):
            if selected_request:
                # Extract emp_id from selection
                emp_id_val = selected_request.split("ID: ")[1].split(")")[0]
                date_val = selected_request.split(" - ")[1]
                approved = approval_status == "✅ Approve"
                
                remarks_text = f"{approver_remarks} (Approved by: {st.session_state.hr_username})" if approver_remarks else f"Request {approval_status.lower()} by {st.session_state.hr_username}"
                
                success, message = approve_early_leave(
                    emp_id_val,
                    date_val,
                    approved,
                    remarks_text,
                    st.session_state.hr_username
                )
                if success:
                    st.success(message)
                    st.balloons() if approved else None
                    st.rerun()
                else:
                    st.error(message)

# --- PASSWORD CHANGE MODULE ---
def render_password_change(username):
    st.markdown("### 🔑 Change Account Password")
    with st.form("pwd_change_form", clear_on_submit=True):
        old_pwd = st.text_input("Current Password", type="password")
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        if st.form_submit_button("Update Password"):
            if not old_pwd or not new_pwd:
                st.error("⚠️ Please fill in all fields.")
            elif new_pwd != confirm_pwd:
                st.error("⚠️ New passwords do not match.")
            else:
                chk = supabase.table("hr_users").select("*").eq("username", username).eq("password", old_pwd).execute()
                if chk.data:
                    supabase.table("hr_users").update({"password": new_pwd}).eq("username", username).execute()
                    st.success("✅ Password updated successfully!")
                else:
                    st.error("❌ Incorrect current password.")

# --- ACCESS MANAGEMENT ---
def render_access_management(is_super_admin=False):
    st.markdown("### 🔐 Provision Department Accounts")
    if is_super_admin:
        tab_add, tab_del = st.tabs(["➕ Provision Access", "🗑️ Manage / Delete Accounts"])
    else:
        tab_add = st.container()
        tab_del = None
    
    with (tab_add if not is_super_admin else tab_add):
        with st.form("new_access_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type="password")
            with col2:
                new_role = st.selectbox("Assign Role", ["Dept Admin", "HR"])
                new_dept = st.text_input("Department Name (Type 'All' for HR)", value="All" if new_role == "HR" else "")
            if st.form_submit_button("Generate Account"):
                if new_user and new_pass and new_dept:
                    try:
                        supabase.table("hr_users").insert({"username": new_user, "password": new_pass, "role": new_role, "department": new_dept}).execute()
                        st.success(f"🎉 Account provisioned successfully for {new_user}")
                        st.rerun()
                    except: st.error("Error creating account. Ensure username is unique.")
                    
    if is_super_admin and tab_del:
        with tab_del:
            st.markdown("#### Existing System Users")
            try:
                hr_res = supabase.table("hr_users").select("id, username, role, department").execute()
                if hr_res.data:
                    df_hr_users = pd.DataFrame(hr_res.data)
                    st.dataframe(df_hr_users.rename(columns={"id": "System ID", "username": "Username", "role": "Role", "department": "Department Scope"}), use_container_width=True)
                    
                    with st.form("delete_user_form"):
                        user_to_delete = st.selectbox("Select Username to Delete", df_hr_users['username'].tolist())
                        if st.form_submit_button("🗑️ Delete Selected User"):
                            if user_to_delete == "SuperAdmin":
                                st.error("❌ You cannot delete the Master Super Admin account!")
                            else:
                                supabase.table("hr_users").delete().eq("username", user_to_delete).execute()
                                st.success(f"✅ User account '{user_to_delete}' has been permanently deleted.")
                                st.rerun()
                else:
                    st.info("No departmental user accounts found.")
            except:
                st.error("Error loading user directory.")

# --- SHIFT MASTER WITH ADVANCED TIMINGS ---
def render_shift_master_ui():
    st.markdown("### ⚙️ Shift Master Management (8Hr Standard + 30m Overtime Rounding)")
    df_shifts = get_shift_data()
    ALLOWED_TIMES = [f"{str(h).zfill(2)}:{m}" for h in range(24) for m in ["00", "30"]]
    
    if not df_shifts.empty:
        disp_cols = [c for c in ["shift_name", "punch_in_time", "punch_out_time", "break_out_time", "break_complete_time", "duration_hrs", "break_mins"] if c in df_shifts.columns]
        st.dataframe(df_shifts[disp_cols].rename(columns={
            "shift_name": "Shift Name", "punch_in_time": "Punch In", "punch_out_time": "Punch Out", 
            "break_out_time": "Break Out", "break_complete_time": "Break Over", "duration_hrs": "Std Hrs", "break_mins": "Break Mins"
        }), use_container_width=True)
        current_shifts = df_shifts["shift_name"].tolist()
    else: current_shifts = []

    tab1, tab_bulk, tab2, tab3 = st.tabs(["➕ Add Shift", "📤 Bulk Upload", "✏️ Edit Shift", "❌ Delete Shift"])
    
    with tab1:
        with st.form("add_shift_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_shift = st.text_input("New Shift Name")
                punch_in = st.selectbox("Punch In Time", ALLOWED_TIMES, index=18) # 09:00
                break_out = st.selectbox("Break Out Time", ALLOWED_TIMES, index=26) # 13:00
            with col2:
                duration = st.number_input("Standard Working Hours", min_value=1.0, max_value=24.0, value=8.0, step=0.5)
                punch_out = st.selectbox("Punch Out Time", ALLOWED_TIMES, index=36) # 18:00
                break_complete = st.selectbox("Break Over Time", ALLOWED_TIMES, index=28) # 14:00
                
            if st.form_submit_button("Add Shift") and new_shift:
                try:
                    brk_duration = 60 # Default or calculated
                    supabase.table("shifts").insert({
                        "shift_name": new_shift, "punch_in_time": punch_in, "punch_out_time": punch_out,
                        "break_out_time": break_out, "break_complete_time": break_complete,
                        "duration_hrs": duration, "break_mins": brk_duration
                    }).execute()
                    st.success(f"✅ Added {new_shift} successfully!")
                    st.rerun()
                except Exception as e: st.error(f"⚠️ Error: {e}")
                
    with tab_bulk:
        st.markdown("**1. Download Template & Prepare Data**")
        st.download_button("📥 Download Shift Template", data="shift_name,punch_in_time,punch_out_time,break_out_time,break_complete_time,duration_hrs,break_mins\nGeneral,09:00,18:00,13:00,14:00,8.0,60", file_name="bulk_shifts_template.csv", mime="text/csv")
        shift_upload_file = st.file_uploader("Upload Shifts CSV", type=["csv"], key="bulk_shift_uploader")
        if shift_upload_file and st.button("Process Bulk Shifts"):
            try:
                df_shf_up = pd.read_csv(shift_upload_file)
                for _, row in df_shf_up.iterrows():
                    try:
                        supabase.table("shifts").insert({
                            "shift_name": str(row['shift_name']), "punch_in_time": str(row['punch_in_time']),
                            "punch_out_time": str(row['punch_out_time']), "break_out_time": str(row['break_out_time']),
                            "break_complete_time": str(row['break_complete_time']), "duration_hrs": float(row['duration_hrs']),
                            "break_mins": int(row['break_mins'])
                        }).execute()
                    except: pass 
                st.success("✅ Successfully added shifts!")
                st.rerun()
            except: st.error("Error reading CSV.")

    with tab2:
        if current_shifts:
            with st.form("edit_shift_form"):
                old_shift = st.selectbox("Select Shift to Edit", current_shifts)
                col1, col2 = st.columns(2)
                with col1:
                    edited_shift = st.text_input("New Name (Leave blank to keep same)")
                    new_in = st.selectbox("New Punch In", ALLOWED_TIMES, index=18)
                    new_bout = st.selectbox("New Break Out", ALLOWED_TIMES, index=26)
                with col2:
                    new_dur = st.number_input("New Working Hours", min_value=1.0, max_value=24.0, value=8.0, step=0.5)
                    new_out = st.selectbox("New Punch Out", ALLOWED_TIMES, index=36)
                    new_bcom = st.selectbox("New Break Over", ALLOWED_TIMES, index=28)
                if st.form_submit_button("Update Shift"):
                    final_name = edited_shift if edited_shift else old_shift
                    try:
                        supabase.table("shifts").update({
                            "shift_name": final_name, "punch_in_time": new_in, "punch_out_time": new_out,
                            "break_out_time": new_bout, "break_complete_time": new_bcom, "duration_hrs": new_dur
                        }).eq("shift_name", old_shift).execute()
                        st.success("✅ Shift updated!")
                        st.rerun()
                    except: st.error("Error updating shift.")

    with tab3:
        if current_shifts:
            with st.form("delete_shift_form"):
                del_shift = st.selectbox("Select Shift to Remove", current_shifts)
                if st.form_submit_button("Delete Shift"):
                    try:
                        supabase.table("shifts").delete().eq("shift_name", del_shift).execute()
                        st.success(f"✅ Deleted {del_shift}!")
                        st.rerun()
                    except: st.error("Error deleting shift.")

# --- DASHBOARD ---
def render_dashboard(role, dept):
    st.markdown("### 📈 Real-Time Attendance Analytics")
    df_emp = get_all_employees()
    df_att = get_all_attendance()
    df_shf = get_shift_data()
    
    if df_emp.empty:
        st.info("No employee data available to generate analytics.")
        return

    if role == "Dept Admin": 
        df_emp = df_emp[df_emp['department'] == dept]
        
    col1, col2 = st.columns(2)
    with col1:
        if role in ["HR", "Super Admin"]:
            dept_set = set()
            if not df_emp.empty: dept_set.update(df_emp['department'].dropna().unique().tolist())
            try:
                hr_users = supabase.table("hr_users").select("department").execute()
                if hr_users.data:
                    for row in hr_users.data:
                        if row.get("department") and row["department"] != "All": dept_set.add(row["department"])
            except: pass
            
            dept_list = ["All"] + sorted(list(dept_set))
            dash_dept = st.selectbox("Filter by Department", dept_list)
        else:
            dash_dept = dept
            st.info(f"Viewing Analytics for Department: **{dept}**")
            
    with col2:
        shift_list = ["All"] + (df_shf["shift_name"].tolist() if not df_shf.empty else [])
        dash_shift = st.selectbox("Filter by Shift", shift_list)
        
    df_dash_emp = df_emp.copy()
    if not df_dash_emp.empty:
        if dash_dept != "All": df_dash_emp = df_dash_emp[df_dash_emp['department'] == dash_dept]
        if dash_shift != "All": df_dash_emp = df_dash_emp[df_dash_emp['shift'] == dash_shift]
        
    active_emp_count = len(df_dash_emp[df_dash_emp['status'] == 'Active']) if not df_dash_emp.empty else 0
    valid_emp_ids = df_dash_emp['emp_id'].tolist() if not df_dash_emp.empty else []
    
    df_att_dash = df_att[df_att['emp_id'].isin(valid_emp_ids)].copy() if not df_att.empty and valid_emp_ids else pd.DataFrame(columns=['emp_id', 'date_only', 'punch_type', 'time_logged'])
        
    today_str = datetime.now(IST).strftime('%Y-%m-%d')
    yesterday_str = (datetime.now(IST) - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if not df_att_dash.empty:
        today_att = df_att_dash[(df_att_dash['date_only'] == today_str) & (df_att_dash['punch_type'].isin(['Punch In', 'QR Code', 'Manual Entry']))]['emp_id'].nunique()
        leave_today = df_att_dash[(df_att_dash['date_only'] == today_str) & (df_att_dash['punch_type'] == 'Leave')]['emp_id'].nunique()
        yest_att = df_att_dash[(df_att_dash['date_only'] == yesterday_str) & (df_att_dash['punch_type'].isin(['Punch In', 'QR Code', 'Manual Entry']))]['emp_id'].nunique()
    else:
        today_att = leave_today = yest_att = 0

    absent_today = max(0, active_emp_count - today_att - leave_today)
    today_pct = round((today_att / active_emp_count * 100) if active_emp_count else 0, 1)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric("Active Employees", f"{active_emp_count}")
    with m2: st.metric("Today Present", f"{today_att} ({today_pct}%)")
    with m3: st.metric("Leave Employees", f"{leave_today}")
    with m4: st.metric("Absent Employees", f"{absent_today}")
    with m5: st.metric("Yesterday Present", f"{yest_att}")

    st.write("---")
    st.markdown("### 🚨 Absenteeism & Leave Analytics")

    today_present_ids = df_att_dash[(df_att_dash['date_only'] == today_str) & (df_att_dash['punch_type'].isin(['Punch In', 'QR Code', 'Manual Entry']))]['emp_id'].unique() if not df_att_dash.empty else []
    today_leave_ids = df_att_dash[(df_att_dash['date_only'] == today_str) & (df_att_dash['punch_type'] == 'Leave')]['emp_id'].unique() if not df_att_dash.empty else []

    if not df_dash_emp.empty:
        def get_status(emp_id):
            if emp_id in today_present_ids: return 'Present'
            elif emp_id in today_leave_ids: return 'Leave'
            else: return 'Absent'

        df_dash_emp['Today Status'] = df_dash_emp['emp_id'].apply(get_status)

        d_tab1, d_tab2, d_tab3 = st.tabs(["🏢 Department-Wise", "🕒 Shift-Wise", "👤 Individual Ranks"])

        with d_tab1:
            dept_summary = df_dash_emp.groupby('department').agg(
                Total_Employees=('emp_id', 'count'),
                Present_Today=('Today Status', lambda x: (x == 'Present').sum()),
                Leave_Today=('Today Status', lambda x: (x == 'Leave').sum()),
                Absent_Today=('Today Status', lambda x: (x == 'Absent').sum())
            ).reset_index()
            st.dataframe(dept_summary.rename(columns={'department': 'Department', 'Total_Employees': 'Total Staff', 'Present_Today': 'Present', 'Leave_Today': 'On Leave', 'Absent_Today': 'Absent'}), use_container_width=True)

        with d_tab2:
            shift_summary = df_dash_emp.groupby('shift').agg(
                Total_Employees=('emp_id', 'count'),
                Present_Today=('Today Status', lambda x: (x == 'Present').sum()),
                Leave_Today=('Today Status', lambda x: (x == 'Leave').sum()),
                Absent_Today=('Today Status', lambda x: (x == 'Absent').sum())
            ).reset_index()
            st.dataframe(shift_summary.rename(columns={'shift': 'Shift Name', 'Total_Employees': 'Total Staff', 'Present_Today': 'Present', 'Leave_Today': 'On Leave', 'Absent_Today': 'Absent'}), use_container_width=True)

        with d_tab3:
            st.markdown("#### 👤 Individual Attendance Summary")
            
            # Date range selection with default "Current Month"
            today = datetime.now(IST).date()
            first_day_of_month = today.replace(day=1)
            
            date_option = st.radio(
                "Select Date Range:",
                ["Current Month", "Custom Range"],
                horizontal=True,
                key="date_range_option"
            )
            
            if date_option == "Current Month":
                summary_start = first_day_of_month
                summary_end = today
                st.info(f"📅 Showing attendance for {first_day_of_month.strftime('%B %Y')} (Current Month)")
            else:
                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    summary_start = st.date_input("Start Date", first_day_of_month)
                with col_date2:
                    summary_end = st.date_input("End Date", today)
            
            if st.button("📊 Generate Individual Attendance Summary", use_container_width=True):
                if not df_att_dash.empty:
                    # Filter attendance data by date range
                    df_att_filtered = df_att_dash[
                        (df_att_dash['date_only'] >= summary_start.strftime('%Y-%m-%d')) &
                        (df_att_dash['date_only'] <= summary_end.strftime('%Y-%m-%d'))
                    ].copy()
                    
                    # Create summary for each employee
                    summary_data = []
                    
                    for _, emp in df_dash_emp.iterrows():
                        emp_id = emp['emp_id']
                        emp_name = emp['name']
                        emp_dept = emp.get('department', 'N/A')
                        emp_shift = emp.get('shift', 'N/A')
                        emp_joining_date = emp.get('joining_date', None)
                        
                        # Get attendance records for this employee
                        emp_att = df_att_filtered[df_att_filtered['emp_id'] == emp_id]
                        
                        # Count present days (Punch In, QR Code, Manual Entry)
                        present_days = emp_att[
                            emp_att['punch_type'].isin(['Punch In', 'QR Code', 'Manual Entry'])
                        ]['date_only'].nunique()
                        
                        # Count leave days
                        leave_days = emp_att[
                            emp_att['punch_type'] == 'Leave'
                        ]['date_only'].nunique()
                        
                        # Calculate working days based on employee's joining date
                        if emp_joining_date:
                            try:
                                joining_date = pd.to_datetime(emp_joining_date).date()
                            except:
                                joining_date = summary_start
                        else:
                            joining_date = summary_start
                        
                        # Determine the actual start date for this employee
                        actual_start = max(joining_date, summary_start)
                        
                        # If employee joined after end date, skip
                        if actual_start > summary_end:
                            continue
                        
                        # Get all days in the range (excluding weekends if needed)
                        date_range = pd.date_range(actual_start, summary_end)
                        total_days = len(date_range)
                        
                        # Absent days = total working days - present days - leave days
                        absent_days = total_days - present_days - leave_days
                        
                        # Calculate attendance percentage
                        attendance_pct = round((present_days / total_days * 100), 1) if total_days > 0 else 0
                        
                        # Determine status based on attendance percentage
                        if attendance_pct >= 90:
                            status = "🟢 Excellent"
                        elif attendance_pct >= 75:
                            status = "🟡 Good"
                        elif attendance_pct >= 50:
                            status = "🟠 Needs Improvement"
                        else:
                            status = "🔴 Poor"
                        
                        summary_data.append({
                            'ID': emp_id,
                            'Name': emp_name,
                            'Dept': emp_dept,
                            'Shift': emp_shift,
                            'Present Days': present_days,
                            'Leave Days': leave_days,
                            'Absent Days': max(0, absent_days),
                            'Total Days': total_days,
                            'Attendance %': attendance_pct,
                            'Status': status
                        })
                    
                    if summary_data:
                        # Create DataFrame and sort by attendance percentage
                        df_summary = pd.DataFrame(summary_data)
                        df_summary = df_summary.sort_values('Attendance %', ascending=False)
                        
                        # Display the summary
                        st.dataframe(df_summary, use_container_width=True, hide_index=True)
                        
                        # Download button
                        csv = df_summary.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download Attendance Summary CSV",
                            data=csv,
                            file_name=f"Attendance_Summary_{summary_start.strftime('%Y%m%d')}_to_{summary_end.strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                        
                        # Show some statistics
                        st.write("---")
                        st.markdown("#### 📊 Summary Statistics")
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        
                        total_employees = len(df_summary)
                        avg_attendance = df_summary['Attendance %'].mean()
                        best_employee = df_summary.iloc[0]['Name'] if not df_summary.empty else "N/A"
                        worst_employee = df_summary.iloc[-1]['Name'] if not df_summary.empty else "N/A"
                        
                        with col_stat1:
                            st.metric("Total Employees", total_employees)
                        with col_stat2:
                            st.metric("Avg Attendance %", f"{round(avg_attendance, 1)}%")
                        with col_stat3:
                            st.metric("Best Performance", best_employee)
                        with col_stat4:
                            st.metric("Needs Improvement", worst_employee)
                        
                        # Show distribution chart
                        st.write("---")
                        st.markdown("#### 📊 Attendance Distribution")
                        
                        # Count employees by status
                        status_counts = df_summary['Status'].value_counts()
                        
                        # Create bar chart data
                        chart_data = pd.DataFrame({
                            'Status': status_counts.index,
                            'Count': status_counts.values
                        })
                        
                        st.bar_chart(chart_data.set_index('Status'))
                    else:
                        st.info("No employees found in the selected date range.")
                else:
                    st.info("No attendance data available.")

# --- MAIN APP LOGIC ---
# SESSION STATE is already initialized at the top

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
                        st.session_state.user_role = user_data.get("role") or "HR"
                        st.session_state.user_dept = user_data.get("department") or "All"
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
#         STATE 2: GENERAL DASHBOARD
# ==========================================
elif st.session_state.hr_logged_in:
    col_l, col_main, col_r = st.columns([1, 8, 1])
    with col_main:
        st.markdown(f"<h1>🏢 {st.session_state.user_role} Command Center</h1>", unsafe_allow_html=True)
        st.markdown(f"<p>Secure Session Active: <b>{st.session_state.hr_username}</b> | Dept: <b>{st.session_state.user_dept}</b></p>", unsafe_allow_html=True)
        
        if st.button("🚪 Terminate Session & Logout"):
            for key in ["hr_logged_in", "hr_username", "user_role", "user_dept"]: 
                st.session_state[key] = ""
            st.session_state.hr_logged_in = False
            st.rerun()
            
        st.write("---")
        
        menu_options = ["📈 Dashboard", "⏱️ Record Attendance", "📊 Payroll & Logs", "👥 Directory", "🔑 Change Password"]
        if st.session_state.user_role == "HR":
            menu_options.insert(3, "👤 Enroll Employees")
            menu_options.extend(["⚙️ Shift Master", "🔐 Access Control"])
            
        hr_action = st.radio("Select Module:", menu_options, horizontal=True)
        st.write("<br>", unsafe_allow_html=True)

        if hr_action == "📈 Dashboard":
            render_dashboard(st.session_state.user_role, st.session_state.user_dept)
        
        elif hr_action == "🔑 Change Password":
            render_password_change(st.session_state.hr_username)
        
        elif hr_action == "⏱️ Record Attendance":
            st.markdown("### ⏱️ Daily Attendance Capture")
            
            tab1, tab2 = st.tabs(["📸 Live QR Scanner", "⌨️ Manual Entry"])
            actions_list = ["Punch In", "Punch Out", "Break Out", "Break Over", "Leave"]
            
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
                    punch_action = st.radio("Select Action to Enable Scanner:", actions_list, horizontal=True, index=None)
                    st.write("---") 
                    if punch_action is None: st.warning("⚠️ Please select an action above to activate the camera.")
                    else:
                        st.info(f"🟢 **Scanner Enabled for: {punch_action}**. Point camera at QR code.")
                        qr_code = qrcode_scanner(key=f"qr_cam_{st.session_state.camera_key}")
                        if qr_code:
                            supabase.table("attendance").insert({"emp_id": str(qr_code), "method": "QR Code", "punch_type": punch_action}).execute()
                            st.session_state.success_msg = f"✅ **{punch_action}** successfully recorded for ID: **{qr_code}**"
                            st.session_state.last_scanned_id = qr_code
                            st.rerun()
            
            with tab2:
                with st.form("manual_entry_form", clear_on_submit=True):
                    manual_action = st.radio("Select Manual Action:", actions_list, horizontal=True)
                    manual_id = st.text_input("Enter Employee ID Number")
                    if st.form_submit_button("Record Manual Punch") and manual_id:
                        supabase.table("attendance").insert({"emp_id": str(manual_id), "method": "Manual Entry", "punch_type": manual_action}).execute()
                        st.success(f"✅ **{manual_action}** successfully recorded for ID: **{manual_id}**")
                        
        elif hr_action == "👤 Enroll Employees":
            st.markdown("### 👤 Employee Enrollment")
            df_shifts = get_shift_data()
            dynamic_shifts = df_shifts["shift_name"].tolist() if not df_shifts.empty else ["General"]
            
            e_tab1, e_tab2 = st.tabs(["Single Enrollment", "Bulk Upload (CSV)"])
            with e_tab1:
                with st.form("enrollment_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        emp_id = st.text_input("Employee ID Number*")
                        name = st.text_input("Full Name*")
                        joining_date = st.date_input("Date of Joining", datetime.now(IST).date())
                    with c2:
                        dept_val = st.session_state.user_dept if st.session_state.user_role == "Dept Admin" else st.text_input("Department")
                        mobile = st.text_input("Mobile Number")
                        shift = st.selectbox("Assigned Shift", dynamic_shifts)
                    
                    if st.form_submit_button("✨ Generate Profile & ID Card") and emp_id and name:
                        try:
                            supabase.table("employees").insert({
                                "emp_id": str(emp_id), 
                                "name": name, 
                                "department": dept_val, 
                                "mobile": mobile, 
                                "shift": shift, 
                                "status": "Active", 
                                "joining_date": joining_date.strftime('%Y-%m-%d'),
                                "status_updated_on": datetime.now(IST).strftime('%d-%m-%Y')
                            }).execute()
                            st.success(f"🎉 Profile created for {name}!")
                        except Exception as e:
                            st.error(f"⚠️ Error saving: {str(e)}")
                        
            with e_tab2:
                st.markdown("**1. Download Template & Prepare Data**")
                st.download_button("📥 Download Sample Template", 
                    data="emp_id,name,department,mobile,shift,joining_date\n1001,John Doe,Sales,9876543210,General,2024-01-01", 
                    file_name="bulk_enroll.csv", mime="text/csv")
                st.markdown("**2. Upload File**")
                uploaded_file = st.file_uploader("Upload Completed CSV", type=["csv"])
                st.write("---")
                if uploaded_file and st.button("Process Bulk Enrollment"):
                    try:
                        df_upload = pd.read_csv(uploaded_file)
                        for _, row in df_upload.iterrows():
                            d_val = st.session_state.user_dept if st.session_state.user_role == "Dept Admin" else str(row.get('department', ''))
                            joining_date = row.get('joining_date', datetime.now(IST).strftime('%Y-%m-%d'))
                            try: 
                                supabase.table("employees").insert({
                                    "emp_id": str(row['emp_id']), 
                                    "name": str(row['name']), 
                                    "department": d_val, 
                                    "mobile": str(row.get('mobile', '')), 
                                    "shift": str(row.get('shift', 'General')), 
                                    "status": "Active",
                                    "joining_date": joining_date,
                                    "status_updated_on": datetime.now(IST).strftime('%d-%m-%Y')
                                }).execute()
                            except: pass
                        st.success("✅ Successfully enrolled employees!")
                    except: st.error("Error reading CSV.")

        # --- EMPLOYEE DIRECTORY ---
        elif hr_action == "👥 Directory":
            st.markdown("### 👥 Directory, Lifecycle & ID Management")
            
            dir_tab1, dir_tab2, dir_tab3, dir_tab4, dir_tab5 = st.tabs(["📋 Employee Directory", "🪪 ID Cards & Eye Preview", "🕒 Shift Mapping", "🔄 Status Update", "🚪 Early Leave Management"])
            
            df_emp_main = get_all_employees()
            if st.session_state.user_role == "Dept Admin" and not df_emp_main.empty:
                df_emp_main = df_emp_main[df_emp_main['department'] == st.session_state.user_dept]
                
            df_shifts = get_shift_data()
            dynamic_shifts = df_shifts["shift_name"].tolist() if not df_shifts.empty else ["General"]
            
            with dir_tab1:
                status_filter = st.radio("Filter By Status:", ["Active", "Left", "All"], horizontal=True, key="dir_status_filter")
                st.write("---")
                if not df_emp_main.empty:
                    df_filtered = df_emp_main if status_filter == "All" else df_emp_main[df_emp_main["status"] == status_filter]
                    if not df_filtered.empty:
                        dir_disp = df_filtered[["emp_id", "name", "department", "shift", "mobile", "status"]].rename(columns={"emp_id": "ID", "name": "Name", "department": "Dept", "shift": "Shift", "mobile": "Phone"})
                        st.dataframe(dir_disp, use_container_width=True)
                        csv_dir = dir_disp.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Export Directory CSV", data=csv_dir, file_name="Joy_Employee_Directory.csv", mime="text/csv")
                    else: st.info("No employees found.")
                else: st.info("No employees found in your scope.")
                
            with dir_tab2:
                if not df_emp_main.empty:
                    active_emps = df_emp_main[df_emp_main["status"] == "Active"]
                    emp_dict = {f"{r['name']} (ID: {r['emp_id']})": r for _, r in active_emps.iterrows()}
                    selected_emp = st.selectbox("Select Employee for ID Card", list(emp_dict.keys()))
                    st.write("---") 
                    if selected_emp:
                        ed = emp_dict[selected_emp]
                        id_img = generate_id_card(ed['emp_id'], ed['name'], ed.get('department',''), ed.get('mobile',''))
                        
                        col_eye1, col_eye2 = st.columns([1, 3])
                        with col_eye1:
                            view_toggle = st.checkbox("👁️ View ID Card Preview", value=st.session_state.show_id_card)
                        
                        buf = io.BytesIO()
                        id_img.save(buf, format="PNG")
                        
                        if view_toggle:
                            st.image(id_img, width=300, caption=f"ID Card Preview for {ed['name']}")
                            
                        st.download_button(label=f"📥 Download ID Card", data=buf.getvalue(), file_name=f"ID_{ed['emp_id']}.png", mime="image/png")
                        
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
                                supabase.table("employees").update({"shift": new_shift}).eq("emp_id", str(emp_map_dict[map_sel])).execute()
                                st.success(f"Shift updated!")
                with s_col2:
                    st.markdown("**Bulk Update**")
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
                st.markdown("#### 🔄 Update Employee Status (Active / Inactive)")
                with st.form("status_update_only_form"):
                    c1, c2, c3 = st.columns(3)
                    with c1: update_id = st.text_input("Enter Employee ID")
                    with c2: new_status = st.selectbox("New Status", ["Active", "Inactive"])
                    with c3: eff_date = st.date_input("Effective Date", datetime.now(IST).date())
                    
                    if st.form_submit_button("Update Status"):
                        if update_id and str(update_id) in df_emp_main['emp_id'].astype(str).values:
                            supabase.table("employees").update({"status": new_status, "status_updated_on": eff_date.strftime('%d-%m-%Y')}).eq("emp_id", str(update_id)).execute()
                            st.success(f"✅ Employee status updated to {new_status}!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid employee ID or outside your scope.")

            with dir_tab5:
                st.markdown("#### 🚪 Early Leave Management")
                df_att_all = get_all_attendance()
                
                # Check user role - show appropriate tabs
                if st.session_state.user_role == "HR":
                    # HR sees only approval tab
                    st.info("👤 You are logged in as HR - you can approve or reject early leave requests.")
                    st.markdown("---")
                    render_hr_approval_tab(df_att_all, df_emp_main)
                
                elif st.session_state.user_role == "Dept Admin":
                    # Dept Admin sees only request tab
                    st.info("👤 You are logged in as Department Incharge - you can submit early leave requests.")
                    st.markdown("---")
                    render_dept_request_tab(df_emp_main)
                
                else:
                    st.warning("⚠️ Your role doesn't have permission for early leave management.")

        # --- VIEW PAYROLL & LOGS WITH 30-MIN ROUNDED OVERTIME ---
        elif hr_action == "📊 Payroll & Logs":
            st.markdown("### 📊 Automated Payroll & Attendance Logs (8Hr Std + 30m Rounded OT)")
            
            p_tab1, p_tab2, p_tab3 = st.tabs(["🧮 Payroll & Penalty Summary", "📜 Raw Punch Logs", "🚪 Approved Early Leaves"])
            
            df_att_all = get_all_attendance()
            df_emp_all = get_all_employees()
            df_shf_all = get_shift_data()
            
            if st.session_state.user_role == "Dept Admin" and not df_emp_all.empty:
                df_emp_all = df_emp_all[df_emp_all['department'] == st.session_state.user_dept]
                
            valid_scope_ids = df_emp_all['emp_id'].astype(str).tolist() if not df_emp_all.empty else []
            if not df_att_all.empty and valid_scope_ids: df_att_all = df_att_all[df_att_all['emp_id'].astype(str).isin(valid_scope_ids)]

            report_type = st.radio("Choose Report Scope:", ["Daily Report", "Monthly Report", "Custom Date Range"], horizontal=True)
            today = datetime.now(IST).date()
            
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

            st.write("---") 
            
            with p_tab1:
                if st.button("Generate Payroll Report"):
                    if not df_att_all.empty and not df_emp_all.empty and not df_shf_all.empty:
                        df_att_sorted = df_att_all.sort_values(by=["emp_id", "time_logged"]).copy()
                        
                        records = []
                        for emp_id, grp in df_att_sorted.groupby("emp_id"):
                            current_in = None
                            for _, row in grp.iterrows():
                                p_type = row.get("punch_type", "")
                                if p_type in ["Punch In", "QR Code", "Manual Entry"]:
                                    if current_in is not None:
                                        records.append({"emp_id": str(emp_id), "Punch In": current_in["time_logged"], "Punch Out": pd.NaT, "early_leave_approved": current_in.get("early_leave_approved", False), "remarks": current_in.get("remarks", "")})
                                    current_in = row
                                elif p_type == "Punch Out" and current_in is not None:
                                    records.append({"emp_id": str(emp_id), "Punch In": current_in["time_logged"], "Punch Out": row["time_logged"], "early_leave_approved": row.get("early_leave_approved", False) or current_in.get("early_leave_approved", False), "remarks": f"{current_in.get('remarks', '')} {row.get('remarks', '')}".strip()})
                                    current_in = None
                            if current_in is not None:
                                records.append({"emp_id": str(emp_id), "Punch In": current_in["time_logged"], "Punch Out": pd.NaT, "early_leave_approved": current_in.get("early_leave_approved", False), "remarks": current_in.get("remarks", "")})
                        
                        df_pairs = pd.DataFrame(records)
                        
                        if not df_pairs.empty:
                            df_pairs['Punch In'] = pd.to_datetime(df_pairs['Punch In']).dt.tz_convert('Asia/Kolkata')
                            df_pairs['Punch Out'] = pd.to_datetime(df_pairs['Punch Out']).dt.tz_convert('Asia/Kolkata')
                            df_pairs['Shift Date'] = df_pairs['Punch In'].dt.date
                            
                            if report_type == "Daily Report": df_pairs = df_pairs[df_pairs["Shift Date"] == search_date]
                            elif report_type == "Monthly Report": df_pairs = df_pairs[(df_pairs['Punch In'].dt.month == month_num) & (df_pairs['Punch In'].dt.year == selected_year)]
                            elif report_type == "Custom Date Range" and len(date_range) == 2: df_pairs = df_pairs[(df_pairs["Shift Date"] >= date_range[0]) & (df_pairs["Shift Date"] <= date_range[1])]
                            
                            if not df_pairs.empty:
                                df_merged = pd.merge(df_pairs, df_emp_all, on="emp_id", how="left")
                                df_merged = pd.merge(df_merged, df_shf_all.rename(columns={"shift_name": "shift"}), on="shift", how="left")
                                
                                df_merged['punch_in_time'] = df_merged['punch_in_time'].fillna('09:00')
                                df_merged['duration_hrs'] = pd.to_numeric(df_merged['duration_hrs'], errors='coerce').fillna(8.0)
                                
                                df_merged['Start Limit'] = pd.to_datetime(df_merged['Shift Date'].astype(str) + ' ' + df_merged['punch_in_time']).dt.tz_localize('Asia/Kolkata')
                                df_merged['End Limit'] = df_merged['Start Limit'] + pd.to_timedelta(df_merged['duration_hrs'], unit='h')
                                
                                df_merged['Is_Late'] = df_merged['Punch In'] > df_merged['Start Limit']
                                df_merged['Raw_Early'] = df_merged['Punch Out'].notna() & (df_merged['Punch Out'] < df_merged['End Limit'])
                                df_merged['Is_Early_Penalized'] = df_merged['Raw_Early'] & (~df_merged['early_leave_approved'])
                                
                                df_merged['Status'] = 'Present'
                                df_merged.loc[df_merged['Is_Late'], 'Status'] = 'Half Day Absent (Late)'
                                df_merged.loc[df_merged['Raw_Early'] & df_merged['early_leave_approved'], 'Status'] = 'Early Exit (Approved)'
                                df_merged.loc[df_merged['Is_Early_Penalized'], 'Status'] = 'Early Exit (Penalized -1Hr)'
                                df_merged.loc[df_merged['Punch Out'].isna(), 'Status'] = 'Missing Punch Out'
                                
                                df_merged['Worked Hrs'] = (df_merged['Punch Out'] - df_merged['Punch In']).dt.total_seconds() / 3600.0
                                df_merged['Effective Hrs'] = df_merged['Worked Hrs']
                                df_merged.loc[df_merged['Is_Early_Penalized'], 'Effective Hrs'] = df_merged['Effective Hrs'] - 1.0 
                                
                                # 30-MINUTE ROUNDED OVERTIME CALCULATION
                                def round_to_nearest_30mins(val):
                                    if pd.isna(val) or val <= 0: return 0.0
                                    return round(np.round(val * 2) / 2, 2)

                                df_merged['Raw OT'] = (df_merged['Effective Hrs'] - df_merged['duration_hrs']).apply(lambda x: max(0, x))
                                df_merged['OT Hrs'] = df_merged['Raw OT'].apply(round_to_nearest_30mins)
                                
                                df_merged['Punch In Time'] = df_merged['Punch In'].dt.strftime('%I:%M %p')
                                df_merged['Punch Out Time'] = df_merged['Punch Out'].dt.strftime('%I:%M %p').fillna('--')
                                df_merged['Worked Hrs'] = df_merged['Worked Hrs'].round(2).fillna(0)
                                
                                cols = ["Shift Date", "emp_id", "name", "department", "shift", "Punch In Time", "Punch Out Time", "Status", "Worked Hrs", "OT Hrs", "remarks"]
                                final_report = df_merged[[c for c in cols if c in df_merged.columns]].rename(columns={"emp_id": "ID", "name": "Name", "department": "Dept", "shift": "Shift", "remarks": "Remarks"})
                                
                                st.dataframe(final_report, use_container_width=True)
                                csv = final_report.to_csv(index=False).encode('utf-8')
                                st.download_button(f"📥 Export Payroll CSV", data=csv, file_name=f'Joy_Payroll_{report_name}.csv', mime='text/csv')
                            else: st.info("No paired attendance records found for selected date scope.")
                        else: st.info("No punch pairs generated.")
                    else: st.info("No attendance data recorded yet for your department scope.")

            with p_tab2:
                st.markdown("#### Raw Punch Log Stream")
                if st.button("Generate Raw Log Stream"):
                    if not df_att_all.empty:
                        df_raw_filtered = df_att_all.copy()
                        if report_type == "Daily Report": df_raw_filtered = df_raw_filtered[df_raw_filtered["date_only"] == str(search_date)]
                        elif report_type == "Monthly Report": df_raw_filtered = df_raw_filtered[(pd.to_datetime(df_raw_filtered['date_only']).dt.month == month_num) & (pd.to_datetime(df_raw_filtered['date_only']).dt.year == selected_year)]
                        elif report_type == "Custom Date Range" and len(date_range) == 2: df_raw_filtered = df_raw_filtered[(df_raw_filtered["date_only"] >= str(date_range[0])) & (df_raw_filtered["date_only"] <= str(date_range[1]))]

                        if not df_raw_filtered.empty:
                            df_raw_disp = df_raw_filtered.copy()
                            df_raw_disp['Punch Time'] = pd.to_datetime(df_raw_disp['time_logged']).dt.strftime('%d-%m-%Y %I:%M:%S %p')
                            df_raw_disp = pd.merge(df_raw_disp, df_emp_all[['emp_id', 'name', 'department']], on='emp_id', how='left')
                            
                            raw_cols = ['date_only', 'emp_id', 'name', 'department', 'punch_type', 'method', 'Punch Time', 'early_leave_approved', 'early_leave_requested', 'remarks', 'requested_by', 'approved_by']
                            raw_disp_final = df_raw_disp[[c for c in raw_cols if c in df_raw_disp.columns]].rename(
                                columns={'date_only': 'Date', 'emp_id': 'ID', 'name': 'Name', 'department': 'Dept', 'punch_type': 'Action', 'method': 'Method', 'early_leave_approved': 'Approved Early Leave', 'early_leave_requested': 'Requested Early Leave', 'remarks': 'Remarks', 'requested_by': 'Requested By', 'approved_by': 'Approved By'}
                            )
                            st.dataframe(raw_disp_final, use_container_width=True)
                            csv_raw = raw_disp_final.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 Export Raw Logs CSV", data=csv_raw, file_name=f"Joy_Raw_Logs_{report_name}.csv", mime="text/csv")
                        else:
                            st.info("No raw logs found for the selected date scope.")
                    else: st.info("No raw punch logs available.")

            with p_tab3:
                st.markdown("#### 🚪 Approved Early Leave Records")
                if not df_att_all.empty:
                    el_df = df_att_all[df_att_all['early_leave_approved'] == True].copy()
                    
                    if report_type == "Daily Report": el_df = el_df[el_df["date_only"] == str(search_date)]
                    elif report_type == "Monthly Report": el_df = el_df[(pd.to_datetime(el_df['date_only']).dt.month == month_num) & (pd.to_datetime(el_df['date_only']).dt.year == selected_year)]
                    elif report_type == "Custom Date Range" and len(date_range) == 2: el_df = el_df[(el_df["date_only"] >= str(date_range[0])) & (el_df["date_only"] <= str(date_range[1]))]
                    
                    if not el_df.empty:
                        el_merged = pd.merge(el_df, df_emp_all[['emp_id', 'name', 'department']], on='emp_id', how='left')
                        el_merged['Punch Time'] = pd.to_datetime(el_merged['time_logged']).dt.strftime('%d-%m-%Y %I:%M:%S %p')
                        
                        disp_cols = ['date_only', 'emp_id', 'name', 'department', 'Punch Time', 'remarks', 'requested_by', 'approved_by']
                        el_disp = el_merged[[c for c in disp_cols if c in el_merged.columns]].rename(
                            columns={'date_only': 'Date', 'emp_id': 'ID', 'name': 'Name', 'department': 'Dept', 'remarks': 'Reason/Remarks', 'requested_by': 'Requested By', 'approved_by': 'Approved By'}
                        )
                        st.dataframe(el_disp, use_container_width=True)
                        csv_el = el_disp.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Export Early Leaves CSV", data=csv_el, file_name=f"Joy_EarlyLeaves_{report_name}.csv", mime="text/csv")
                    else:
                        st.info("No approved early leaves found for the selected date range.")
                else:
                    st.info("No records available.")

        elif hr_action == "⚙️ Shift Master": 
            render_shift_master_ui()
        elif hr_action == "🔐 Access Control": 
            render_access_management(is_super_admin=False)

# ==========================================
#         STATE 3: SUPER ADMIN DASHBOARD
# ==========================================
elif st.session_state.super_logged_in:
    col_l, col_main, col_r = st.columns([1, 6, 1])
    with col_main:
        st.markdown("<h1>🛡️ Super Admin Control Center</h1>", unsafe_allow_html=True)
        
        sa_action = st.radio("Select Module:", ["📈 Real-Time Dashboard", "🔐 Access Management", "🔑 Change Password"], horizontal=True)
        st.write("---")
        
        if st.button("🚪 Terminate Session & Logout"):
            st.session_state.super_logged_in = False
            st.rerun()
            
        if sa_action == "📈 Real-Time Dashboard": 
            render_dashboard("Super Admin", "All")
        elif sa_action == "🔐 Access Management": 
            render_access_management(is_super_admin=True)
        elif sa_action == "🔑 Change Password": 
            render_password_change("SuperAdmin")
