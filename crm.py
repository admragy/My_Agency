import streamlit as st
import pandas as pd
import requests
from supabase import create_client
import time

# --- إعداد الصفحة ---
st.set_page_config(page_title="Growth System", layout="wide", page_icon="📈")

# --- CSS (التصميم) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; }
    header {visibility: hidden;} footer {visibility: hidden;}
    .stMetric { background-color: white; border: 1px solid #ddd; border-radius: 10px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- الاتصال ---
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    API_URL = st.secrets["API_URL"]
except: st.stop()

# --- الدخول ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = ''
    st.session_state['username'] = ''

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
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

# --- التطبيق ---
def main_app():
    user = st.session_state['username']
    role = st.session_state['user_role']
    
    with st.sidebar:
        st.write(f"👤 **{user}**")
        if st.button("خروج"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.divider()
        
        pages = ["الرئيسية", "بحث عن عملاء", "سجل الداتا", "الحملات"]
        if role == 'admin': pages.append("إدارة المستخدمين")
        menu = st.sidebar.radio("القائمة", pages)

    # 1. الرئيسية
    if menu == "الرئيسية":
        st.subheader(f"مرحباً {user}")
        data = supabase.table("leads").select("*").eq("user_id", user).execute().data
        df = pd.DataFrame(data) if data else pd.DataFrame()
        c1, c2 = st.columns(2)
        c1.metric("إجمالي العملاء", len(df))
        hot = len(df[df['quality'].str.contains('Excellent', na=False)]) if not df.empty else 0
        c2.metric("عملاء مهتمين 🔥", hot)

    # 2. البحث (الصياد)
    elif menu == "بحث عن عملاء":
        st.header("🔍 البحث عن عملاء")
        with st.form("hunt"):
            intent = st.text_input("عايز زبائن بتدور على إيه؟")
            city = st.text_input("المنطقة / المدينة")
            time_opt = st.selectbox("الوقت", ["أي وقت", "آخر شهر", "آخر 24 ساعة"])
            time_map = {"أي وقت": "qdr:y", "آخر شهر": "qdr:m", "آخر 24 ساعة": "qdr:d"}
            
            if st.form_submit_button("ابدأ البحث 🚀"):
                try:
                    payload = {"intent_sentence": intent, "city": city, "time_filter": time_map[time_opt], "user_id": user}
                    requests.post(f"{API_URL}/start_hunt", json=payload)
                    st.success("تم الإطلاق! تابع السجل.")
                except: st.error("خطأ اتصال")

    # 3. السجل
    elif menu == "سجل الداتا":
        st.header("📋 العملاء")
        if st.button("تحديث"): st.rerun()
        leads = supabase.table("leads").select("*").eq("user_id", user).order("created_at", desc=True).execute().data
        if leads:
            df = pd.DataFrame(leads)
            df['رابط'] = df['notes'].str.replace('Link: ', '', regex=False)
            st.dataframe(
                df[['quality', 'phone_number', 'email', 'رابط']],
                column_config={"رابط": st.column_config.LinkColumn("المصدر", display_text="فتح")},
                use_container_width=True
            )
            # أدوات الحذف
            with st.expander("🗑️ حذف"):
                del_ph = st.text_input("حذف رقم:")
                if st.button("مسح"):
                    supabase.table("leads").delete().eq("phone_number", del_ph).execute()
                    st.rerun()

    # 4. الحملات
    elif menu == "الحملات":
        st.header("📩 الرسائل")
        with st.form("camp"):
            name = st.text_input("اسم العرض")
            desc = st.text_area("نص الرسالة")
            if st.form_submit_button("حفظ"):
                supabase.table("campaigns").update({"is_active": False}).eq("is_active", True).execute()
                supabase.table("campaigns").insert({"campaign_name": name, "product_description": desc, "is_active": True}).execute()
                st.success("تم")

    # 5. الأدمن
    elif menu == "إدارة المستخدمين" and role == 'admin':
        st.header("👮‍♂️ المستخدمين")
        with st.form("new_user"):
            u = st.text_input("User")
            p = st.text_input("Pass")
            if st.form_submit_button("Add Client"):
                supabase.table("users").insert({"username": u, "password": p, "role": "client"}).execute()
                st.success("Added")

if st.session_state['logged_in']: main_app()
else: login_screen()
