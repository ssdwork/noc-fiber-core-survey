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
st.set_page_config(page_title="ফাইবার কোর কানেকশন জরিপ", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

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
    conn = st.connection("gsheets", type=GSheetsConnection)

    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
            <div style="flex: 0 0 100px; text-align: left;">
                <img src="https://raw.githubusercontent.com/ssdwork/bd-broadband-survey/main/Ict Division Logo Vector.svg" style="height: 70px; width: auto;" title="ICT Division">
            </div>
            <div style="flex: 1; text-align: center;">
                <div class="main-title"> ফাইবার কোর কানেকশন জরিপ</div>
            </div>
            <div style="flex: 0 0 100px; text-align: right;">
                <img src="https://raw.githubusercontent.com/ssdwork/bd-broadband-survey/main/Bangladesh_Computer_Council_Logo.svg" style="height: 45px; width: auto;" title="Bangladesh Computer Council">
            </div>
        </div>
    """, unsafe_allow_html=True)

    if 'fiber_rows' not in st.session_state:
        st.session_state.fiber_rows = 1

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

    # --- GEOGRAPHY INFO ---
    st.markdown('<div class="section-head">এলাকার তথ্য</div>', unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        div_list = list(BD_DATA.keys())
        final_div = smart_geo_input('বিভাগ (Division)', div_list, 'geo_div')
    with g2:
        dist_opts = list(BD_DATA[final_div].keys()) if final_div in BD_DATA else []
        final_dist = smart_geo_input('জেলা (District)', dist_opts, 'geo_dist')
    with g3:
        upz_opts = list(BD_DATA[final_div][final_dist].keys()) if (final_div in BD_DATA and final_dist in BD_DATA[final_div]) else []
        final_upz = smart_geo_input('উপজেলা (Upazila)', upz_opts, 'geo_upz')
    with g4:
        uni_opts = BD_DATA[final_div][final_dist][final_upz] if (final_div in BD_DATA and final_dist in BD_DATA[final_div] and final_upz in BD_DATA[final_div][final_dist]) else []
        final_uni = smart_geo_input('ইউনিয়ন (Union)', uni_opts, 'geo_uni_main')

    # --- FIBER CONNECTION INFO ---
    st.markdown('<div class="section-head">ফাইবার কোর কানেকশনের তথ্য</div>', unsafe_allow_html=True)
    
    core_type_opts = ["-- নির্বাচন করুন --", "48", "24", "12"]
    company_opts = ["-- নির্বাচন করুন --", "Fiber@Home", "Summit"]
    
    fiber_records = []

    for i in range(st.session_state.fiber_rows):
        st.markdown(f'<div class="fiber-block">', unsafe_allow_html=True)
        st.markdown(f"#### ফাইবার লাইন - {i+1}")
        
        fc1, fc2 = st.columns(2)
        with fc1:
            comp_name = st.selectbox(f"কোম্পানির নাম (Company) *", company_opts, key=f"comp_{i}")
        with fc2:
            dep_km = st.number_input(f"ডিপেন্ডেন্সি / Dependency (KM) *", min_value=0.0, step=0.1, key=f"dep_{i}")

        st.markdown("**উৎস (Source) এর তথ্য:**")
        s1, s2, s3 = st.columns(3)
        with s1: s_name = st.text_input("উৎস (Source Name) *", key=f"s_name_{i}")
        with s2: s_core = st.selectbox("উৎস কোর টাইপ *", core_type_opts, key=f"s_core_{i}")
        with s3: s_dist = st.number_input("উৎস দূরত্ব / Distance (KM) *", min_value=0.0, step=0.1, key=f"s_dist_{i}")

        st.markdown("**গন্তব্য (Destination) এর তথ্য:**")
        d1, d2, d3 = st.columns(3)
        with d1: d_name = st.text_input("গন্তব্য (Destination Name) *", key=f"d_name_{i}")
        with d2: d_core = st.selectbox("গন্তব্য কোর টাইপ *", core_type_opts, key=f"d_core_{i}")
        with d3: d_dist = st.number_input("গন্তব্য দূরত্ব / Distance (KM) *", min_value=0.0, step=0.1, key=f"d_dist_{i}")
        
        st.markdown('</div>', unsafe_allow_html=True)

        fiber_records.append({
            "company": comp_name, "dep_km": dep_km,
            "s_name": s_name, "s_core": s_core, "s_dist": s_dist,
            "d_name": d_name, "d_core": d_core, "d_dist": d_dist
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
        submit_btn = st.button("Submit", use_container_width=True, type="primary")

    if submit_btn:
        officer_contact_valid = user_contact.isdigit() and len(user_contact) == 11 if user_contact else False
        
        missing_fields = []
        if not name: missing_fields.append("তথ্য প্রদানকারীর নাম (Name) *")
        if not user_contact: missing_fields.append("যোগাযোগ নম্বর *")
        if not designation: missing_fields.append("পদবী (Designation) *")
        if not workplace: missing_fields.append("কর্মস্থলের নাম (Workplace Name) *")
        if not final_div: missing_fields.append("বিভাগ (Division)")
        if not final_dist: missing_fields.append("জেলা (District)")
        if not final_upz: missing_fields.append("উপজেলা (Upazila)")
        if not final_uni: missing_fields.append("ইউনিয়ন (Union)")

        # Validate Fiber fields
        for idx, rec in enumerate(fiber_records):
            if rec["company"] == "-- নির্বাচন করুন --": missing_fields.append(f"কোম্পানির নাম (Company) * (লাইন {idx+1})")
            if not rec["s_name"]: missing_fields.append(f"উৎস (Source Name) * (লাইন {idx+1})")
            if rec["s_core"] == "-- নির্বাচন করুন --": missing_fields.append(f"উৎস কোর টাইপ * (লাইন {idx+1})")
            if not rec["d_name"]: missing_fields.append(f"গন্তব্য (Destination Name) * (লাইন {idx+1})")
            if rec["d_core"] == "-- নির্বাচন করুন --": missing_fields.append(f"গন্তব্য কোর টাইপ * (লাইন {idx+1})")

        if missing_fields:
            st.error("দয়া করে নিচের তথ্যগুলো পূরণ করুন:\n" + ", ".join(missing_fields))
        elif not officer_contact_valid:
            st.error("❌ যোগাযোগ নম্বর সঠিক নয় (১১ ডিজিট ও শুধুমাত্র সংখ্যা হতে হবে)।")
        else:
            try:
                records_to_save = []
                for rec in fiber_records:
                    records_to_save.append({
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "নাম": name,
                        "যোগাযোগ নম্বর": user_contact,
                        "পদবী": designation,
                        "কর্মস্থল": workplace,
                        "বিভাগ": final_div,
                        "জেলা": final_dist,
                        "উপজেলা": final_upz,
                        "ইউনিয়ন": final_uni,
                        "কোম্পানির নাম": rec["company"],
                        "উৎস (Source)": rec["s_name"],
                        "উৎস কোর টাইপ": rec["s_core"],
                        "উৎস দূরত্ব (KM)": rec["s_dist"],
                        "গন্তব্য (Destination)": rec["d_name"],
                        "গন্তব্য কোর টাইপ": rec["d_core"],
                        "গন্তব্য দূরত্ব (KM)": rec["d_dist"],
                        "ডিপেন্ডেন্সি (KM)": rec["dep_km"]
                    })
                
                new_record = pd.DataFrame(records_to_save)
                
                existing_data = conn.read(ttl=0)
                if existing_data is not None and not existing_data.empty:
                    updated_df = pd.concat([existing_data, new_record], ignore_index=True)
                else:
                    updated_df = new_record
                
                expected_order = [
                    "Timestamp", "নাম", " যোগাযোগ নম্বর", "পদবী", "কর্মস্থল", 
                    "বিভাগ", "জেলা", "উপজেলা", "ইউনিয়ন", 
                    "কোম্পানির নাম", "উৎস (Source)", "উৎস কোর টাইপ", "উৎস দূরত্ব (KM)", 
                    "গন্তব্য (Destination)", "গন্তব্য কোর টাইপ", "গন্তব্য দূরত্ব (KM)", "ডিপেন্ডেন্সি (KM)"
                ]
                
                final_columns = [c for c in expected_order if c in updated_df.columns] + [c for c in updated_df.columns if c not in expected_order]
                updated_df = updated_df[final_columns]

                conn.update(data=updated_df)
                
                st.balloons()
                
                success_message = """
                    <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.6); z-index: 999999; display: flex; align-items: center; justify-content: center;">
                        <div style="background-color: #FFFFFF; padding: 40px; border-radius: 20px; border: 3px solid #006400; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3); max-width: 500px; width: 90%;">
                            <h1 style="color: #006400; font-family: 'Calibri', 'Nikosh', sans-serif; font-size: 40px; margin: 0; font-weight: 700;">✅ সফলভাবে সংরক্ষিত হয়েছে!</h1>
                            <p style="color: #000000; font-size: 20px; margin-top: 15px; font-weight: 500;">আপনার তথ্য ডাটাবেজে জমা হয়েছে।</p>
                        </div>
                    </div>
                """
                placeholder = st.empty()
                placeholder.markdown(success_message, unsafe_allow_html=True)
                time.sleep(3)
                placeholder.empty()
                
                # Clear Session State for Fiber records
                current_keys = list(st.session_state.keys())
                for key in current_keys:
                    if any(prefix in key for prefix in ["comp_", "dep_", "s_name_", "s_core_", "s_dist_", "d_name_", "d_core_", "d_dist_", "geo_uni_main"]):
                        del st.session_state[key]
                st.session_state.fiber_rows = 1

                st.rerun()
                
            except Exception as e:
                st.error(f"Error during submission: {e}")

    st.markdown("---")
    st.markdown("""
        <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 20px;">
            <div style="color: #006400; font-size: 14px; font-weight: 700;">যোগাযোগের নম্বর:</div>
            <div style="color: #000000;">+8801677891434</div>
            <div style="color: #000000;">+8801712511005</div>
            <div style="color: #000000;">+880255006823</div>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
