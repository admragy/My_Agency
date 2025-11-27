import streamlit as st
import pandas as pd
import requests
from supabase import create_client
import time

# --- 1. إعداد الصفحة ---
st.set_page_config(page_title="Growth System", layout="wide", page_icon="📈")

# --- 2. تصميم ذكي للموبايل (Mobile-First CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    /* تعميم الخط */
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }
    
    /* ضبط الاتجاه للعربي داخل المحتوى فقط وليس الهيكل */
    .block-container {
        direction: rtl;
        text-align: right;
    }
    
    /* إصلاح القائمة الجانبية للموبايل */
    [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    
    /* تنسيق الكروت (Metrics) لتظهر بشكل سليم */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        text-align: right;
        direction: rtl;
    }
    
    /* الأرقام تظهر بشكل صحيح */
    [data-testid="stMetricValue"] {
        direction: ltr; /* عشان الرقم يظهر صح */
        text-align: right;
    }

    /* إخفاء العناصر الزائدة */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. الاتصال ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    API_URL = st.secrets["API_URL"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.stop()

# --- 4. الدخول ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = ''
    st.session_state['username'] = ''

def login_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 10, 1])
    with c2:
        st.info("👋 أهلاً بك في النظام")
        with st.form("login"):
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول", use_container_width=True):
                res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
                if res.data and res.data[0]['is_active']:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    st.session_state['user_role'] = res.data[0]['role']
                    st.rerun()
                else: st.error("بيانات خطأ")

# --- 5. التطبيق ---
def main_app():
    user = st.session_state['username']
    role = st.session_state['user_role']
    
    with st.sidebar:
        st.write(f"👤 **{user}**")
        st.divider()
        pages = ["الرئيسية", "بحث عن عملاء", "سجل الداتا", "الحملات"]
        if role == 'admin': pages.append("إدارة المستخدمين")
        menu = st.sidebar.radio("القائمة", pages)
        st.markdown("---")
        if st.button("خروج", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    # المحتوى (نفس المنطق السابق مع تحسين العرض)
    if menu == "الرئيسية":
        st.subheader(f"مرحباً {user} ☀️")
        data = supabase.table("leads").select("*").eq("user_id", user).execute().data
        df = pd.DataFrame(data) if data else pd.DataFrame()
        
        # كروت الأرقام (تظهر تحت بعض في الموبايل وجنب بعض في اللابتوب)
        c1, c2 = st.columns(2)
        c1.metric("العملاء", len(df))
        hot = len(df[df['quality'].str.contains('Excellent', na=False)]) if not df.empty else 0
        c2.metric("مهتمين 🔥", hot)

    elif menu == "بحث عن عملاء":
        st.header("🔍 الصياد")
        with st.form("hunt"):
            intent = st.text_input("عايز زبائن إيه؟")
            city = st.text_input("المنطقة")
            time_opt = st.selectbox("الوقت", ["أي وقت", "آخر شهر", "آخر 24 ساعة"])
            time_map = {"أي وقت": "qdr:y", "آخر شهر": "qdr:m", "آخر 24 ساعة": "qdr:d"}
            if st.form_submit_button("بحث 🚀", use_container_width=True):
                try:
                    payload = {"intent_sentence": intent, "city": city, "time_filter": time_map.get(time_opt, "qdr:m"), "user_id": user}
                    requests.post(f"{API_URL}/start_hunt", json=payload)
                    st.success("تم الإطلاق!")
                except: st.error("خطأ اتصال")

    elif menu == "سجل الداتا":
        st.header("📋 السجل")
        if st.button("تحديث 🔄", use_container_width=True): st.rerun()
        leads = supabase.table("leads").select("*").eq("user_id", user).order("created_at", desc=True).execute().data
        if leads:
            df = pd.DataFrame(leads)
            df['رابط'] = df['notes'].str.replace('Link: ', '', regex=False)
            st.dataframe(
                df[['quality', 'phone_number', 'رابط']],
                column_config={"رابط": st.column_config.LinkColumn("المصدر", display_text="فتح")},
                use_container_width=True
            )
            with st.expander("حذف رقم"):
                d = st.text_input("الرقم")
                if st.button("مسح"):
                    supabase.table("leads").delete().eq("phone_number", d).execute()
                    st.rerun()

    elif menu == "الحملات":
        st.header("📩 الرسائل")
        with st.form("camp"):
            n = st.text_input("اسم العرض")
            d = st.text_area("النص")
            if st.form_submit_button("حفظ", use_container_width=True):
                supabase.table("campaigns").update({"is_active": False}).eq("is_active", True).execute()
                supabase.table("campaigns").insert({"campaign_name": n, "product_description": d, "is_active": True}).execute()
                st.success("تم")

    elif menu == "إدارة المستخدمين" and role == 'admin':
        st.header("المستخدمين")
        with st.form("u"):
            u = st.text_input("User")
            p = st.text_input("Pass")
            if st.form_submit_button("Add"):
                supabase.table("users").insert({"username": u, "password": p, "role": "client"}).execute()
                st.success("Done")

if st.session_state['logged_in']: main_app()
else: login_screen()
