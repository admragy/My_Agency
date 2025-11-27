import streamlit as st
import pandas as pd
import requests
from supabase import create_client
import time

# --- 1. إعداد الصفحة ---
st.set_page_config(page_title="Agency Login", layout="wide", page_icon="🔒")

# --- 2. الاتصال بالسحابة ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    API_URL = st.secrets["API_URL"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("⚠️ خطأ في الاتصال بالسيرفر.")
    st.stop()

# --- 3. نظام تسجيل الدخول (Session State) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = ''
    st.session_state['username'] = ''

def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔐 بوابة الوكالة الذكية</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            submit = st.form_submit_button("تسجيل الدخول", use_container_width=True)
            
            if submit:
                try:
                    response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
                    user = response.data
                    
                    if user:
                        if user[0]['is_active']:
                            st.session_state['logged_in'] = True
                            st.session_state['user_role'] = user[0]['role']
                            st.session_state['username'] = user[0]['username']
                            st.success("تم الدخول بنجاح!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("⛔ الحساب موقوف.")
                    else:
                        st.error("❌ بيانات خاطئة.")
                except Exception as e:
                    st.error(f"خطأ: {e}")

# --- 4. التطبيق الرئيسي (Main App) ---
def main_app():
    # الشريط الجانبي وزر الخروج
    with st.sidebar:
        st.write(f"👤 **{st.session_state['username']}** ({st.session_state['user_role']})")
        if st.button("تسجيل الخروج"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.markdown("---")

    # تحديد القائمة حسب الصلاحية
    if st.session_state['user_role'] == 'admin':
        menu = st.sidebar.radio("القائمة", ["📊 الداتا والنتائج", "➕ إضافة عميل يدوي", "🕵️‍♂️ الصياد الذكي", "🚀 إدارة الحملات", "⚙️ الإعدادات", "👥 إدارة المستخدمين"])
    else:
        menu = st.sidebar.radio("القائمة", ["📊 الداتا والنتائج", "➕ إضافة عميل يدوي", "🕵️‍♂️ الصياد الذكي", "🚀 إدارة الحملات"])

    # ==========================
    # صفحة الداتا (شاملة الحذف)
    # ==========================
    if menu == "📊 الداتا والنتائج":
        st.header("💎 كنز العملاء")
        
        # زر التحديث
        if st.button("تحديث الجدول 🔄"): st.rerun()

        # أدوات الحذف (للأدمن فقط أو للكل حسب رغبتك)
        with st.expander("🗑️ أدوات الحذف"):
            c1, c2 = st.columns(2)
            with c1:
                del_phone = st.text_input("مسح رقم محدد:")
                if st.button("مسح الرقم"):
                    supabase.table("leads").delete().eq("phone_number", del_phone).execute()
                    st.success("تم المسح.")
                    st.rerun()
            with c2:
                if st.button("💣 مسح كل الداتا"):
                    supabase.table("leads").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                    st.warning("تم تصفير الخزنة.")
                    st.rerun()

        # عرض الجدول
        response = supabase.table("leads").select("*").order("created_at", desc=True).execute()
        leads = response.data
        if leads:
            df = pd.DataFrame(leads)
            
            m1, m2 = st.columns(2)
            m1.metric("العدد الكلي", len(df))
            if 'quality' in df.columns:
                excellent = len(df[df['quality'].str.contains('Excellent', na=False)])
                m2.metric("🔥 عملاء لقطة", excellent)
            
            st.dataframe(df[['quality', 'phone_number', 'email', 'source', 'notes']], use_container_width=True)
        else:
            st.info("لا توجد بيانات.")

    # ==========================
    # صفحة الإضافة اليدوية
    # ==========================
    elif menu == "➕ إضافة عميل يدوي":
        st.header("📝 تسجيل يدوي")
        with st.form("manual"):
            phone = st.text_input("رقم الموبايل")
            notes = st.text_input("ملاحظات")
            if st.form_submit_button("حفظ"):
                supabase.table("leads").upsert({
                    "phone_number": phone, "source": "Manual", "status": "NEW", "quality": "Manual", "notes": notes
                }, on_conflict="phone_number").execute()
                st.success("تم الحفظ!")

    # ==========================
    # صفحة الصياد الذكي
    # ==========================
    elif menu == "🕵️‍♂️ الصياد الذكي":
        st.header("🎣 الصياد (V18)")
        with st.form("hunt"):
            intent = st.text_input("ماذا تريد؟ (مثال: مطلوب عقارات)")
            city = st.text_input("المدينة", "القاهرة")
            time_filter = st.selectbox("الفترة الزمنية", ["qdr:d (يوم)", "qdr:w (أسبوع)", "qdr:m (شهر)"])
            
            if st.form_submit_button("🚀 اطلق الصياد"):
                try:
                    payload = {"intent_sentence": intent, "city": city, "time_filter": time_filter.split()[0]}
                    requests.post(f"{API_URL}/start_hunt", json=payload)
                    st.success("تم الإطلاق! تابع صفحة الداتا.")
                except: st.error("فشل الاتصال بالمخ.")

    # ==========================
    # صفحة الحملات
    # ==========================
    elif menu == "🚀 إدارة الحملات":
        st.header("📦 إعداد الحملة")
        current = supabase.table("campaigns").select("*").eq("is_active", True).execute().data
        if current: st.info(f"الحملة الحالية: {current[0]['campaign_name']}")
        
        with st.form("camp"):
            name = st.text_input("اسم الحملة")
            desc = st.text_area("وصف المنتج")
            media = st.text_input("رابط الصورة")
            if st.form_submit_button("تفعيل"):
                supabase.table("campaigns").update({"is_active": False}).eq("is_active", True).execute()
                supabase.table("campaigns").insert({"campaign_name": name, "product_description": desc, "media_url": media, "is_active": True}).execute()
                st.success("تم التفعيل.")
                st.rerun()

    # ==========================
    # صفحة الإدارة (Admin Only)
    # ==========================
    elif menu == "👥 إدارة المستخدمين" and st.session_state['user_role'] == 'admin':
        st.header("👮‍♂️ التحكم في الحسابات")
        with st.form("new_user"):
            new_u = st.text_input("يوزر جديد")
            new_p = st.text_input("باسورد")
            if st.form_submit_button("إنشاء"):
                supabase.table("users").insert({"username": new_u, "password": new_p, "role": "client"}).execute()
                st.success("تم الإنشاء.")
                st.rerun()
        
        users = supabase.table("users").select("*").neq("username", "admin").execute().data
        if users:
            for u in users:
                c1, c2 = st.columns([3, 1])
                c1.write(f"👤 {u['username']} - {'✅ نشط' if u['is_active'] else '⛔ موقوف'}")
                if c2.button("تغيير الحالة", key=u['id']):
                    supabase.table("users").update({"is_active": not u['is_active']}).eq("id", u['id']).execute()
                    st.rerun()

# --- 5. تشغيل النظام ---
if st.session_state['logged_in']:
    main_app()
else:
    login_screen()
