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
            # Keep time_logged as object initially to handle timezone safely
            df["time_logged"] = pd.to_datetime(df["time_logged"]).dt.tz_convert('Asia/Kolkata')
            df["date_only"] = df["time_logged"].dt.strftime('%Y-%m-%d')
            
            # Ensure required columns exist with defaults
            defaults = {
                "early_leave_status": "Pending",
                "remarks": "",
                "punch_type": "Punch In"
            }
            for col, default_val in defaults.items():
                if col not in df.columns: df[col] = default_val
                df[col] = df[col].fillna(default_val)
                
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading attendance: {e}")
        return pd.DataFrame()

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

# --- PASSWORD CHANGE MODULE ---
def render_password_change(username):
    st.markdown("### 🔑 Change Account Password")
    with st.form("pwd_change_form", clear_on_submit=True):
        old_pwd = st.text_input("Current Password", type="password") # HIDDEN
        new_pwd = st.text_input("New Password", type="password") # HIDDEN
        confirm_pwd = st.text_input("Confirm New Password", type="password") # HIDDEN
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
                new_pass = st.text_input("Password", type="password") # HIDDEN
            with col2:
                new_role = st.selectbox("Assign Role", ["Dept Incharge", "HR"])
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

# --- DASHBOARD ---
def render_dashboard(role, dept):
    st.markdown("### 📈 Real-Time Attendance Analytics")
    df_emp = get_all_employees()
    df_att = get_all_attendance()
    df_shf = get_shift_data()
    
    if df_emp.empty:
        st.info("No employee data available to generate analytics.")
        return

    if role == "Dept Incharge": df_emp = df_emp[df_emp['department'] == dept]
    
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
    
    df_att_dash = df_att[df_att['emp_id'].isin(valid_emp_ids)].copy() if not df_att.empty and valid_emp_ids else pd.DataFrame(columns=['emp_id', 'date_only', 'punch_type'])
    
    today_str = datetime.now(IST).strftime('%Y-%m-%d')
    yesterday_str = (datetime.now(IST) - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if not df_att_dash.empty:
        today_att = df_att_dash[(df_att_dash['date_only'] == today_str) & (df_att_dash['punch_type
