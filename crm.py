import streamlit as st
import pandas as pd
import requests
from supabase import create_client
import time

# --- 1. إعداد الصفحة ---
st.set_page_config(page_title="Growth System", layout="wide", page_icon="📈")

# --- 2. التصميم (Mobile Fixed) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .block-container { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { direction: rtl; text-align: right; }
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
    [data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 10px; direction: rtl; text-align: right; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. الاتصال ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    API_URL = st.secrets["API_URL"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except: st.stop()

# --- 4. الدخول ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = ''
    st.session_state['username'] = ''

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 10, 1])
    with c2:
        st.info("👋 أهلاً بك في النظام")
        with st.form("login"):
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول", use_container_width=True):
                try:
                    res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
                    if res.data and res.data[0]['is_active']:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.session_state['user_role'] = res.data[0]['role']
                        st.rerun()
                    else: st.error("بيانات خطأ أو حساب موقوف")
                except: st.error("خطأ اتصال")

# --- 5. التطبيق ---
def main_app():
    user = st.session_state['username']
    role = st.session_state['user_role']
    
    with st.sidebar:
        st.write(f"👤 **{user}** ({role})")
        if st.button("خروج"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.divider()
        
        pages = ["الرئيسية", "بحث عن عملاء", "سجل الداتا", "الحملات"]
        if role == 'admin': pages.extend(["👮‍♂️ توزيع الداتا", "👥 إدارة المستخدمين"])
        
        menu = st.sidebar.radio("القائمة", pages)

    # 1. الرئيسية
    if menu == "الرئيسية":
        st.subheader(f"مرحباً {user} ☀️")
        # حساب داتا اليوزر فقط
        count = supabase.table("leads").select("*", count="exact").eq("user_id", user).execute().count
        c1, c2 = st.columns(2)
        c1.metric("رصيد عملائك", count)
        c2.metric("الحالة", "نشط ✅")

    # 2. البحث (الصياد)
    elif menu == "بحث عن عملاء":
        st.header("🔍 الصياد")
        with st.form("hunt"):
            intent = st.text_input("عايز زبائن إيه؟")
            city = st.text_input("المنطقة")
            time_opt = st.selectbox("الوقت", ["أي وقت", "آخر شهر", "آخر 24 ساعة"])
            time_map = {"أي وقت": "qdr:y", "آخر شهر": "qdr:m", "آخر 24 ساعة": "qdr:d"}
            
            if st.form_submit_button("بحث 🚀", use_container_width=True):
                try:
                    payload = {
                        "intent_sentence": intent, 
                        "city": city, 
                        "time_filter": time_map.get(time_opt, "qdr:m"), 
                        "user_id": user # بنبعت اسم اليوزر عشان الداتا تتسجل باسمه
                    }
                    requests.post(f"{API_URL}/start_hunt", json=payload)
                    st.success("تم الإطلاق! النتائج ستظهر في 'سجل الداتا' الخاص بك.")
                except: st.error("خطأ اتصال")

    # 3. السجل
    elif menu == "سجل الداتا":
        st.header("📋 عملائي")
        if st.button("تحديث 🔄"): st.rerun()
        
        # عرض داتا اليوزر فقط
        leads = supabase.table("leads").select("*").eq("user_id", user).order("created_at", desc=True).execute().data
        if leads:
            df = pd.DataFrame(leads)
            df['رابط'] = df['notes'].str.replace('Link: ', '', regex=False)
            st.dataframe(
                df[['quality', 'phone_number', 'email', 'رابط']],
                column_config={"رابط": st.column_config.LinkColumn("المصدر", display_text="فتح")},
                use_container_width=True
            )
        else: st.info("ليس لديك داتا.")

    # 4. الحملات
    elif menu == "الحملات":
        st.header("📩 الرسائل")
        with st.form("camp"):
            n = st.text_input("اسم العرض")
            d = st.text_area("النص")
            if st.form_submit_button("حفظ"):
                supabase.table("campaigns").update({"is_active": False}).eq("is_active", True).execute()
                supabase.table("campaigns").insert({"campaign_name": n, "product_description": d, "is_active": True}).execute()
                st.success("تم")

    # 5. توزيع الداتا (أدمن فقط)
    elif menu == "👮‍♂️ توزيع الداتا" and role == 'admin':
        st.header("📦 توزيع الأرقام")
        
        # إحصائيات المخزن
        admin_leads = supabase.table("leads").select("*", count="exact").eq("user_id", "admin").execute().count
        st.info(f"المخزن الرئيسي (Admin) فيه: {admin_leads} عميل متاح للتوزيع.")
        
        c1, c2 = st.columns(2)
        with c1:
            users_res = supabase.table("users").select("username").neq("username", "admin").execute().data
            target = st.selectbox("إرسال إلى:", [u['username'] for u in users_res])
            amount = st.number_input("العدد", 1, 1000, 50)
            
            if st.button("تحويل"):
                # نجيب أرقام من الأدمن
                leads_to_move = supabase.table("leads").select("id").eq("user_id", "admin").limit(amount).execute().data
                if leads_to_move:
                    for l in leads_to_move:
                        supabase.table("leads").update({"user_id": target}).eq("id", l['id']).execute()
                    st.success(f"تم نقل {len(leads_to_move)} عميل لـ {target}")
                    time.sleep(1)
                    st.rerun()
                else: st.error("المخزن فاضي!")

    # 6. إدارة المستخدمين (أدمن فقط)
    elif menu == "👥 إدارة المستخدمين" and role == 'admin':
        st.header("المستخدمين")
        with st.form("new"):
            u = st.text_input("User")
            p = st.text_input("Pass")
            if st.form_submit_button("Add"):
                supabase.table("users").insert({"username": u, "password": p}).execute()
                st.success("Done")
                st.rerun()
        
        users = supabase.table("users").select("*").neq("username", "admin").execute().data
        if users:
            for u in users:
                st.write(f"👤 {u['username']} - {'✅' if u['is_active'] else '⛔'}")

if st.session_state['logged_in']: main_app()
else: login_screen()
