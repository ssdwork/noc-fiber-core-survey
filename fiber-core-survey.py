import streamlit as st
import pandas as pd
import json
import urllib.request
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import time

# -----------------------------------------------------------------------------
# 1. GEOGRAPHICAL DATA LOADER
# -----------------------------------------------------------------------------
NUHIL_RAW = {
    "divisions": "https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/divisions/divisions.json",
    "districts": "https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/districts/districts.json",
    "upazilas": "https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/upazilas/upazilas.json",
    "unions": "https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/unions/unions.json",
}

def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

@st.cache_data
def build_bd_data():
    try:
        div_raw = fetch_json(NUHIL_RAW['divisions'])
        dist_raw = fetch_json(NUHIL_RAW['districts'])
        upz_raw = fetch_json(NUHIL_RAW['upazilas'])
        uni_raw = fetch_json(NUHIL_RAW['unions'])
        
        def extract_data(raw):
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict) and 'data' in item: return item['data']
            if isinstance(raw, dict) and 'data' in raw: return raw['data']
            return []

        divs, dists, upzs, unis = extract_data(div_raw), extract_data(dist_raw), extract_data(upz_raw), extract_data(uni_raw)
        div_map = {str(d['id']): d.get('bn_name') or d.get('name') for d in divs}
        dist_map = {str(d['id']): {'bn_name': d.get('bn_name') or d.get('name'), 'division_id': str(d.get('division_id'))} for d in dists}
        upz_map = {str(u['id']): {'bn_name': u.get('bn_name') or u.get('name'), 'district_id': str(u.get('district_id'))} for u in upzs}
        
        uni_map = {}
        for u in unis:
            upid = str(u.get('upazilla_id') or u.get('upazila_id') or '')
            uni_map.setdefault(upid, []).append(u.get('bn_name') or u.get('name'))

        data_tree = {}
        for upz_id, upz in upz_map.items():
            dist_id = upz.get('district_id')
            dist_entry = dist_map.get(dist_id)
            if not dist_entry: continue
            div_name = div_map.get(dist_entry.get('division_id'), 'অন্যান্য')
            dist_name = dist_entry.get('bn_name')
            upz_name = upz.get('bn_name')
            data_tree.setdefault(div_name, {}).setdefault(dist_name, {})[upz_name] = uni_map.get(upz_id, [])
        return data_tree
    except:
        return {}

BD_DATA = build_bd_data()

# -----------------------------------------------------------------------------
# DATABASE SCHEMA
# -----------------------------------------------------------------------------
DB_COLUMNS = [
    "Timestamp", "নাম", "যোগাযোগ নম্বর", "পদবী", "কর্মস্থল", 
    "উৎস বিভাগ", "উৎস জেলা", "উৎস উপজেলা", "উৎস ইউনিয়ন", 
    "উৎস (Source Name)", "উৎস কোর টাইপ", "উৎস দূরত্ব (KM)", 
    "গন্তব্য বিভাগ", "গন্তব্য জেলা", "গন্তব্য উপজেলা", "গন্তব্য ইউনিয়ন",
    "গন্তব্য (Destination Name)", "গন্তব্য কোর টাইপ", "গন্তব্য দূরত্ব (KM)", 
    "ডিপেন্ডেন্সি (KM)", "পয়েন্টসমূহ"
]

# -----------------------------------------------------------------------------
# 2. UI HELPERS
# -----------------------------------------------------------------------------
def smart_geo_input(label, options_list, key):
    opts = ['-- নির্বাচন করুন --'] + (sorted(options_list) if options_list else []) + ['অন্যান্য']
    choice = st.selectbox(label, opts, key=key)
    if choice == 'অন্যান্য':
        return st.text_input(f"অন্যান্য (লিখুন): {label}", key=f"{key}_other")
    return "" if choice == '-- নির্বাচন করুন --' else choice

# -----------------------------------------------------------------------------
# 3. PAGE SETUP & DESIGN
# -----------------------------------------------------------------------------
st.set_page_config(page_title="ফাইবার কানেকশন জরিপ", page_icon="🖱", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 1. Main Background */
    .stApp {
        background: linear-gradient(rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.95)),
            url('https://raw.githubusercontent.com/ssdwork/noc-fiber-core-survey/main/other%20resources/background%20image.webp'); 
        background-size: cover; background-position: center; background-attachment: fixed;
    }

    /* 2. Global Text Color */
    html, body, [class*="css"], .stMarkdown, p, label, .stTextInput > label, .stNumberInput > label { 
        font-family: 'Calibri', 'Nikosh', sans-serif; 
        color: #000000 !important; 
        font-weight: 700 !important; 
        font-size: 14px !important;
    }
    
    /* 3. Headers */
    h1, h2, h3, h4 { color: #000000 !important; }

    /* 4. Input Fields */
    div[data-baseweb="input"] input, 
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] span,
    div[data-baseweb="base-input"] {
        color: #000000 !important; 
        -webkit-text-fill-color: #000000 !important;
        font-family: 'Calibri', 'Nikosh', sans-serif !important;
        font-weight: 400 !important;
    }

    div[data-baseweb="input"], 
    div[data-baseweb="select"] { 
        background-color: #FFFFFF !important; 
        border: 1px solid #006400 !important; 
        border-radius: 8px !important; 
    }
    
    /* Dropdown Options */
    ul[data-baseweb="menu"], div[data-baseweb="popover"] { background-color: #FFFFFF !important; }
    li[data-baseweb="option"] { color: #000000 !important; }

    /* 5. Buttons */
    div.stButton > button { 
        color: #006400 !important; 
        border: 1px solid #006400 !important; 
        background-color: #FFFFFF !important; 
        font-weight: 600 !important; 
        border-radius: 6px !important;
    }
    div.stButton > button:hover {
        background-color: #006400 !important;
        color: #FFFFFF !important;
    }
    div.stButton > button[kind="primary"] { 
        background: linear-gradient(to bottom, #007bff, #0056b3) !important; 
        color: #FFFFFF !important; 
        border: none !important;
    }

    /* 6. Custom Classes */
    .main-title { 
        color: #006400 !important; 
        text-align: center; 
        font-size: 1.4rem !important; 
        font-weight: 700; 
        border-bottom: 3px solid #F42A41; 
        padding-bottom: 5px; 
        display: inline-block;
    }
    .section-head { 
        color: #006400 !important; 
        font-family: 'Calibri', 'Nikosh', sans-serif;
        font-weight: 700; 
        margin: 15px 0 5px 0; 
        border-bottom: 2px solid #006400; 
        font-size: 16px !important;
        padding-bottom: 5px;
    }
    .fiber-block {
        background: #f1f8e9;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #c5e1a5;
        margin-bottom: 15px;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    </style>
""", unsafe_allow_html=True)

def main():
    # -----------------------------------------------------------------------------
    # AUTHENTICATION
    # -----------------------------------------------------------------------------
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h2 style='text-align: center; color: #006400;'>লগইন করুন</h2>", unsafe_allow_html=True)
            password = st.text_input("পাসওয়ার্ড (Password)", type="password", key="auth_pass")
            if st.button("প্রবেশ করুন (Login)", use_container_width=True):
                if password == 'Bccuser2026':
                    st.session_state.authenticated = True
                    st.session_state.user_role = 'USER'
                    st.rerun()
                elif password == 'Bccadmin2026':
                    st.session_state.authenticated = True
                    st.session_state.user_role = 'ADMIN'
                    st.rerun()
                else:
                    st.error("❌ ভুল পাসওয়ার্ড! আবার চেষ্টা করুন।")
        return

    conn = st.connection("gsheets", type=GSheetsConnection)

    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
            <div style="flex: 0 0 100px; text-align: left;">
                <img src="https://raw.githubusercontent.com/ssdwork/bd-broadband-survey/main/Ict Division Logo Vector.svg" style="height: 70px; width: auto;" title="ICT Division">
            </div>
            <div style="flex: 1; text-align: center;">
                <div class="main-title"> ফাইবার কানেকশন জরিপ</div>
            </div>
            <div style="flex: 0 0 100px; text-align: right;">
                <img src="https://raw.githubusercontent.com/ssdwork/bd-broadband-survey/main/Bangladesh_Computer_Council_Logo.svg" style="height: 45px; width: auto;" title="Bangladesh Computer Council">
            </div>
        </div>
    """, unsafe_allow_html=True)

    if 'fiber_rows' not in st.session_state:
        st.session_state.fiber_rows = 1
    if 'point_rows' not in st.session_state:
        st.session_state.point_rows = {}

    desig_list = [
        "প্রোগ্রামার", "মেইনটেন্যান্স ইঞ্জিনিয়ার", 
        "নেটওয়ার্ক ইঞ্জিনিয়ার", "সহকারী পরিচালক", "সহকারী প্রোগ্রামার", 
        "সহকারী মেইনটেন্যান্স ইঞ্জিনিয়ার", "সহকারী নেটওয়ার্ক ইঞ্জিনিয়ার", 
        "ওয়েবসাইট এ্যাডমিনিস্ট্রেটর"
    ]

    # --- OFFICER INFO ---
    st.markdown('<div class="section-head"> তথ্য প্রদানকারী</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: name = st.text_input("তথ্য প্রদানকারীর নাম (Name) *", key="user_name") 
    with c2:
        user_contact = st.text_input("যোগাযোগ নম্বর *", key="user_contact_input")
        if user_contact and (not user_contact.isdigit() or len(user_contact) != 11):
            st.warning("⚠️ নম্বরটি অবশ্যই ১১ ডিজিটের হতে হবে")
    with c3:
        selected_desig = st.selectbox("পদবী (Designation) *", ["-- নির্বাচন করুন --"] + desig_list + ["অন্যান্য"], key="desig_select")
        if selected_desig == "অন্যান্য": designation = st.text_input("আপনার পদবী লিখুন *", key="desig_other_input")
        elif selected_desig == "-- নির্বাচন করুন --": designation = ""
        else: designation = selected_desig
    with c4: workplace = st.text_input("কর্মস্থলের নাম (Workplace Name) *", key="workplace_input")

    # --- FIBER CONNECTION INFO ---
    st.markdown('<div class="section-head">ফাইবার কোর কানেকশনের তথ্য</div>', unsafe_allow_html=True)
    core_type_opts = ["-- নির্বাচন করুন --", "48", "24", "12"]
    fiber_records = []
    for i in range(st.session_state.fiber_rows):
        st.markdown(f'<div class="fiber-block">', unsafe_allow_html=True)
        st.markdown(f"#### ফাইবার লাইন - {i+1}")
        
        # --- GEOGRAPHY INFO ---
        st.markdown('<div class="section-head">উৎস এলাকার তথ্য</div>', unsafe_allow_html=True)
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            div_list = list(BD_DATA.keys())
            final_div = smart_geo_input('উৎস বিভাগ (Division)', div_list, f'geo_div_{i}')
        with g2:
            dist_opts = list(BD_DATA[final_div].keys()) if final_div in BD_DATA else []
            final_dist = smart_geo_input('উৎস জেলা (District)', dist_opts, f'geo_dist_{i}')
        with g3:
            upz_opts = list(BD_DATA[final_div][final_dist].keys()) if (final_div in BD_DATA and final_dist in BD_DATA[final_div]) else []
            final_upz = smart_geo_input('উৎস উপজেলা (Upazila)', upz_opts, f'geo_upz_{i}')
        with g4:
            uni_opts = BD_DATA[final_div][final_dist][final_upz] if (final_div in BD_DATA and final_dist in BD_DATA[final_div] and final_upz in BD_DATA[final_div][final_dist]) else []
            final_uni = smart_geo_input('উৎস ইউনিয়ন (Union)', uni_opts, f'geo_uni_{i}')

        s1, s2, s3 = st.columns(3)
        with s1: s_name = st.text_input("উৎস (Source Name) *", key=f"s_name_{i}")
        with s2: s_core = st.selectbox("উৎস কোর টাইপ *", core_type_opts, key=f"s_core_{i}")
        with s3: s_dist = st.number_input("উৎস দূরত্ব / Distance (KM) *", min_value=0.0, step=0.1, key=f"s_dist_{i}")

        # --- Intermediate Points ---
        points_for_this_fiber = []
        num_points = st.session_state.point_rows.get(i, 0)

        if num_points > 0:
            st.markdown('<div class="section-head" style="margin-top: 15px; margin-bottom: 10px;">পয়েন্টের তথ্য</div>', unsafe_allow_html=True)

        for j in range(num_points):
            st.markdown(f"<h6>&nbsp;&nbsp;&nbsp;পয়েন্ট - {j+1}</h6>", unsafe_allow_html=True)
            p_c1, p_c2, p_c3 = st.columns(3)
            with p_c1:
                p_name = st.text_input(f"পয়েন্ট {j+1} এর নাম (Point {j+1} Name)", key=f"p_name_{i}_{j}")
            with p_c2:
                p_core = st.selectbox("পয়েন্ট কোর টাইপ", core_type_opts, key=f"p_core_{i}_{j}")
            with p_c3:
                p_dist = st.number_input("পয়েন্ট দূরত্ব / Point  Distance (KM)", min_value=0.0, step=0.1, key=f"p_dist_{i}_{j}")
            
            points_for_this_fiber.append({
                "name": p_name,
                "core": p_core,
                "dist": p_dist
            })

        # Add/Remove Point Buttons for this specific fiber line
        p_btn1, p_btn2, p_btn_spacer = st.columns([2, 1, 3])
        with p_btn1:
            if st.button("➕ পয়েন্টের তথ্য যোগ করুন", key=f"add_point_{i}", use_container_width=True):
                st.session_state.point_rows[i] = st.session_state.point_rows.get(i, 0) + 1
                st.rerun()
        with p_btn2:
            if st.button("➖ বাদ দিন", key=f"rem_point_{i}", use_container_width=True) and st.session_state.point_rows.get(i, 0) > 0:
                current_points = st.session_state.point_rows.get(i, 0)
                st.session_state.point_rows[i] = current_points - 1
                # Clean up state for the removed widget to prevent issues
                for prefix in ["p_name_", "p_core_", "p_dist_"]:
                    key_to_del = f"{prefix}{i}_{current_points - 1}"
                    if key_to_del in st.session_state: del st.session_state[key_to_del]
                st.rerun()

        st.markdown('<div class="section-head">গন্তব্য এলাকার তথ্য</div>', unsafe_allow_html=True)
        gd1, gd2, gd3, gd4 = st.columns(4)
        with gd1:
            d_div_list = list(BD_DATA.keys())
            d_final_div = smart_geo_input('গন্তব্য বিভাগ (Division)', d_div_list, f'd_geo_div_{i}')
        with gd2:
            d_dist_opts = list(BD_DATA[d_final_div].keys()) if d_final_div in BD_DATA else []
            d_final_dist = smart_geo_input('গন্তব্য জেলা (District)', d_dist_opts, f'd_geo_dist_{i}')
        with gd3:
            d_upz_opts = list(BD_DATA[d_final_div][d_final_dist].keys()) if (d_final_div in BD_DATA and d_final_dist in BD_DATA[d_final_div]) else []
            d_final_upz = smart_geo_input('গন্তব্য উপজেলা (Upazila)', d_upz_opts, f'd_geo_upz_{i}')
        with gd4:
            d_uni_opts = BD_DATA[d_final_div][d_final_dist][d_final_upz] if (d_final_div in BD_DATA and d_final_dist in BD_DATA[d_final_div] and d_final_upz in BD_DATA[d_final_div][d_final_dist]) else []
            d_final_uni = smart_geo_input('গন্তব্য ইউনিয়ন (Union)', d_uni_opts, f'd_geo_uni_{i}')

        d1, d2, d3 = st.columns(3)
        with d1: d_name = st.text_input("গন্তব্য (Destination Name) *", key=f"d_name_{i}")
        with d2: d_core = st.selectbox("গন্তব্য কোর টাইপ *", core_type_opts, key=f"d_core_{i}")
        with d3: d_dist = st.number_input("গন্তব্য দূরত্ব / Distance (KM) *", min_value=0.0, step=0.1, key=f"d_dist_{i}")
        
        dep_km = st.number_input(f"ডিপেন্ডেন্সি / Dependency (KM) *", min_value=0.0, step=0.1, key=f"dep_{i}")

        st.markdown('</div>', unsafe_allow_html=True)

        fiber_records.append({
            "div": final_div, "dist": final_dist, "upz": final_upz, "uni": final_uni,
            "d_div": d_final_div, "d_district": d_final_dist, "d_upz": d_final_upz, "d_uni": d_final_uni,
            "dep_km": dep_km,
            "s_name": s_name, "s_core": s_core, "s_dist": s_dist,
            "d_name": d_name, "d_core": d_core, "d_dist": d_dist,
            "points": points_for_this_fiber
        })

    # Add/Remove Line Buttons
    _, btn_add, btn_rem = st.columns([4, 1, 1])
    with btn_add:
        if st.button("➕ আরও ফাইবার লাইন যোগ করুন", use_container_width=True):
            st.session_state.fiber_rows += 1
            st.rerun()
    with btn_rem:
        if st.button("➖ বাদ দিন", use_container_width=True) and st.session_state.fiber_rows > 1:
            st.session_state.fiber_rows -= 1
            st.rerun()

    # --- SUBMIT ---
    st.markdown("<br>", unsafe_allow_html=True)
    _, c_sub, _ = st.columns([4, 2, 4])
    with c_sub:
        submit_btn = st.button("জমা দিন", use_container_width=True, type="primary")

    if submit_btn:
        officer_contact_valid = user_contact.isdigit() and len(user_contact) == 11 if user_contact else False
        
        validation_errors = []
        missing_fields = []
        if not name: missing_fields.append("তথ্য প্রদানকারীর নাম (Name) *")
        if not user_contact: missing_fields.append("যোগাযোগ নম্বর *")
        if not designation: missing_fields.append("পদবী (Designation) *")
        if not workplace: missing_fields.append("কর্মস্থলের নাম (Workplace Name) *")

        # Validate Fiber fields
        for idx, rec in enumerate(fiber_records):
            if not rec["div"]: missing_fields.append(f"উৎস বিভাগ (Division) (লাইন {idx+1})")
            if not rec["dist"]: missing_fields.append(f"উৎস জেলা (District) (লাইন {idx+1})")
            if not rec["upz"]: missing_fields.append(f"উৎস উপজেলা (Upazila) (লাইন {idx+1})")
            if not rec["uni"]: missing_fields.append(f"উৎস ইউনিয়ন (Union) (লাইন {idx+1})")
            if not rec["d_div"]: missing_fields.append(f"গন্তব্য বিভাগ (Division) (লাইন {idx+1})")
            if not rec["d_district"]: missing_fields.append(f"গন্তব্য জেলা (District) (লাইন {idx+1})")
            if not rec["d_upz"]: missing_fields.append(f"গন্তব্য উপজেলা (Upazila) (লাইন {idx+1})")
            if not rec["d_uni"]: missing_fields.append(f"গন্তব্য ইউনিয়ন (Union) (লাইন {idx+1})")
            if not rec["s_name"]: missing_fields.append(f"উৎস (Source Name) * (লাইন {idx+1})")
            if rec["s_core"] == "-- নির্বাচন করুন --": missing_fields.append(f"উৎস কোর টাইপ * (লাইন {idx+1})")
            if not rec["d_name"]: missing_fields.append(f"গন্তব্য (Destination Name) * (লাইন {idx+1})")
            if rec["d_core"] == "-- নির্বাচন করুন --": missing_fields.append(f"গন্তব্য কোর টাইপ * (লাইন {idx+1})")

        all_errors = []
        if missing_fields:
            all_errors.append("দয়া করে নিচের তথ্যগুলো পূরণ করুন:\n" + ", ".join(missing_fields))
        if validation_errors:
            all_errors.extend(validation_errors)

        if all_errors:
            st.error("\n\n".join(all_errors))
        elif not officer_contact_valid:
            st.error("❌ যোগাযোগ নম্বর সঠিক নয় (১১ ডিজিট ও শুধুমাত্র সংখ্যা হতে হবে)।")
        else:
            submission_success = False
            try:
                records_to_save = []
                for rec in fiber_records:
                    records_to_save.append({
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "নাম": name,
                        "যোগাযোগ নম্বর": user_contact,
                        "পদবী": designation,
                        "কর্মস্থল": workplace,
                        "উৎস বিভাগ": rec["div"],
                        "উৎস জেলা": rec["dist"],
                        "উৎস উপজেলা": rec["upz"],
                        "উৎস ইউনিয়ন": rec["uni"],
                        "উৎস (Source Name)": rec["s_name"],
                        "উৎস কোর টাইপ": rec["s_core"],
                        "উৎস দূরত্ব (KM)": rec["s_dist"],
                        "গন্তব্য বিভাগ": rec["d_div"],
                        "গন্তব্য জেলা": rec["d_district"],
                        "গন্তব্য উপজেলা": rec["d_upz"],
                        "গন্তব্য ইউনিয়ন": rec["d_uni"],
                        "গন্তব্য (Destination Name)": rec["d_name"],
                        "গন্তব্য কোর টাইপ": rec["d_core"],
                        "গন্তব্য দূরত্ব (KM)": rec["d_dist"],
                        "ডিপেন্ডেন্সি (KM)": rec["dep_km"],
                        "পয়েন্টসমূহ": json.dumps(rec["points"], ensure_ascii=False) if rec.get("points") else ""
                    })
                
                new_record = pd.DataFrame(records_to_save)
                
                existing_data = conn.read(ttl=0)
                if existing_data is not None and not existing_data.empty:
                    updated_df = pd.concat([existing_data, new_record], ignore_index=True)
                else:
                    updated_df = new_record
                
                expected_order = DB_COLUMNS
                
                final_columns = [c for c in expected_order if c in updated_df.columns] + [c for c in updated_df.columns if c not in expected_order]
                updated_df = updated_df[final_columns]

                conn.update(data=updated_df)
                submission_success = True

            except Exception as e:
                st.error(f"Error during submission: {e}")

            if submission_success:
                st.snow()
                
                success_message = """
                    <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.6); z-index: 999999; display: flex; align-items: center; justify-content: center;">
                        <div style="background-color: #FFFFFF; padding: 40px; border-radius: 20px; border: 3px solid #006400; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3); max-width: 500px; width: 90%;">
                            <h1 style="color: #006400; font-family: 'Calibri', 'Nikosh', sans-serif; font-size: 40px; margin: 0; font-weight: 700;">✅ সফলভাবে সংরক্ষিত হয়েছে! 🎆</h1>
                            <p style="color: #000000; font-size: 20px; margin-top: 15px; font-weight: 500;">আপনার তথ্য ডাটাবেজে জমা হয়েছে।</p>
                        </div>
                    </div>
                """
                placeholder = st.empty()
                placeholder.markdown(success_message, unsafe_allow_html=True)
                time.sleep(3)
                placeholder.empty()
                
                # Clear all state except authentication
                for key in list(st.session_state.keys()):
                    if key not in ['authenticated', 'user_role']:
                        del st.session_state[key]

                st.markdown("<meta http-equiv='refresh' content='0'>", unsafe_allow_html=True)

    st.markdown("---")
    #st.markdown("""
     #   <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 20px;">
      #      <div style="color: #006400; font-size: 14px; font-weight: 700;">যোগাযোগের নম্বর:</div>
       #     <div style="color: #000000;">+8801677891434</div>
        #    <div style="color: #000000;">+8801712511005</div>
         #   <div style="color: #000000;">+880255006823</div>
        #</div>
    #""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
