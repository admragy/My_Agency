import streamlit as st
import pandas as pd
import requests
from supabase import create_client
import time

# --- 1. إعداد الصفحة ---
st.set_page_config(page_title="Agency Hub", layout="wide", page_icon="🌐")

# --- 2. التصميم (CSS - Mobile Friendly & RTL) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }
    
    /* ضبط الاتجاه يمين */
    .block-container {
        direction: rtl;
        text-align: right;
    }
    
    /* إصلاح القائمة الجانبية */
    [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    
    /* تحسين الكروت */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 10px;
        direction: rtl;
        text-align: right;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* إخفاء الفوتر */
    footer {visibility: hidden;}
    
    /* تلوين الهيدر ليكون واضح */
    header {background-color: white !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. الاتصال بالسحابة ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    API_URL = st.secrets["API_URL"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("⚠️ جاري الاتصال بالسيرفر...")
    st.stop()

# --- 4. نظام الدخول ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = ''
    st.session_state['username'] = ''

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 10, 1])
    with c2:
        st.info("👋 أهلاً بك في نظام الوكالة")
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
                    else: st.error("بيانات خطأ أو حساب موقوف.")
                except: st.error("خطأ في الاتصال.")

# --- 5. التطبيق الرئيسي ---
def main_app():
    user = st.session_state['username']
    role = st.session_state['user_role']
    
    # القائمة الجانبية
    with st.sidebar:
        st.write(f"👤 **{user}** ({role})")
        if st.button("خروج", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
        st.divider()
        
        # صفحات التطبيق
        pages = ["الرئيسية", "بحث عن عملاء", "سجل الداتا (CRM)", "الحملات"]
        if role == 'admin': pages.append("👮‍♂️ توزيع الداتا & إدارة")
        
        menu = st.sidebar.radio("القائمة", pages)

    # === 1. الرئيسية ===
    if menu == "الرئيسية":
        st.subheader(f"مرحباً {user} ☀️")
        
        # إحصائيات اليوزر
        leads = supabase.table("leads").select("*").eq("user_id", user).execute().data
        df = pd.DataFrame(leads) if leads else pd.DataFrame()
        
        c1, c2, c3 = st.columns(3)
        count = len(df) if not df.empty else 0
        hot = len(df[df['quality'].str.contains('Excellent', na=False)]) if not df.empty else 0
        sold = len(df[df['feedback_status'] == 'تم البيع']) if not df.empty else 0
        
        c1.metric("إجمالي العملاء", count)
        c2.metric("فرص ذهبية 🔥", hot)
        c3.metric("مبيعات ناجحة 💰", sold)

    # === 2. الصياد (المربوط بالحملة) ===
    elif menu == "بحث عن عملاء":
        st.header("🔍 الصياد الموجه")
        
        # جلب الحملة النشطة للربط
        active_camp = supabase.table("campaigns").select("id, campaign_name").eq("is_active", True).execute().data
        campaign_id = active_camp[0]['id'] if active_camp else None
        
        if active_camp:
            st.success(f"✅ سيتم ربط العملاء بحملة: **{active_camp[0]['campaign_name']}**")
        else:
            st.warning("⚠️ لا توجد حملة نشطة! الصيد سيكون عام.")

        with st.form("hunt"):
            intent = st.text_input("عايز زبائن بتدور على إيه؟")
            city = st.text_input("المنطقة / المدينة", "القاهرة")
            time_opt = st.selectbox("الوقت", ["أي وقت", "آخر شهر", "آخر 24 ساعة"])
            time_map = {"أي وقت": "qdr:y", "آخر شهر": "qdr:m", "آخر 24 ساعة": "qdr:d"}
            
            if st.form_submit_button("ابدأ البحث 🚀", use_container_width=True):
                try:
                    payload = {
                        "intent_sentence": intent, 
                        "city": city, 
                        "time_filter": time_map.get(time_opt, "qdr:m"), 
                        "user_id": user,
                        "campaign_id": campaign_id
                    }
                    requests.post(f"{API_URL}/start_hunt", json=payload)
                    st.success("تم الإطلاق! النتائج ستظهر في السجل.")
                except: st.error("خطأ اتصال.")

    # === 3. سجل الداتا (CRM كامل) ===
    elif menu == "سجل الداتا (CRM)":
        st.header("📋 إدارة العملاء")
        
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button("تحديث 🔄", use_container_width=True): st.rerun()
            
        # جلب داتا اليوزر فقط
        leads = supabase.table("leads").select("*").eq("user_id", user).order("created_at", desc=True).execute().data
        
        if leads:
            df = pd.DataFrame(leads)
            
            # عرض العملاء كـ كروت قابلة للتعديل (Expander)
            for lead in leads:
                # أيقونة حسب الجودة
                icon = "🔥" if "Excellent" in str(lead['quality']) else "👤"
                status_label = lead['feedback_status'] if lead['feedback_status'] else "جديد"
                
                with st.expander(f"{icon} {lead['phone_number']} | {status_label}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        # تعديل الحالة
                        new_stat = st.selectbox(
                            "تحديث الحالة", 
                            ["جديد", "مهتم", "تم البيع 💰", "لم يرد", "غير مهتم"], 
                            index=0, 
                            key=f"st_{lead['id']}"
                        )
                    with ec2:
                        # حفظ التعديل
                        if st.button("حفظ الحالة", key=f"btn_{lead['id']}"):
                            supabase.table("leads").update({"feedback_status": new_stat}).eq("id", lead['id']).execute()
                            st.success("تم!")
                            st.rerun()
                    
                    # تفاصيل إضافية
                    st.caption(f"المصدر: {lead['source']}")
                    if lead['notes'] and "Link" in lead['notes']:
                        link = lead['notes'].replace('Link: ', '')
                        st.markdown(f"[🔗 فتح المصدر]({link})")
                        
        else:
            st.info("ليس لديك داتا حالياً.")

    # === 4. الحملات ===
    elif menu == "الحملات":
        st.header("📦 إعداد العرض")
        with st.form("camp"):
            name = st.text_input("اسم الحملة")
            desc = st.text_area("نص الرسالة (للـ AI والواتساب)")
            media = st.text_input("رابط الصورة")
            if st.form_submit_button("تفعيل الحملة", use_container_width=True):
                supabase.table("campaigns").update({"is_active": False}).eq("is_active", True).execute()
                supabase.table("campaigns").insert({
                    "campaign_name": name, "product_description": desc, "media_url": media, "is_active": True
                }).execute()
                st.success("تم التفعيل.")
                st.rerun()

    # === 5. الأدمن (توزيع الداتا) ===
    elif menu == "👮‍♂️ توزيع الداتا & إدارة" and role == 'admin':
        st.header("مخزن التوزيع")
        
        # عدد الداتا عند الأدمن
        admin_count = supabase.table("leads").select("*", count="exact").eq("user_id", "admin").execute().count
        st.info(f"متاح في المخزن الرئيسي: {admin_count} عميل")
        
        st.write("---")
        
        # أداة التوزيع
        st.subheader("توزيع أرقام على عميل")
        users_res = supabase.table("users").select("username").neq("username", "admin").execute().data
        
        if users_res:
            c1, c2, c3 = st.columns(3)
            target = c1.selectbox("اختر العميل", [u['username'] for u in users_res])
            amount = c2.number_input("العدد", 1, 1000, 50)
            
            if c3.button("نقل الداتا", use_container_width=True):
                # نقل داتا من admin لليوزر المختار
                leads_to_move = supabase.table("leads").select("id").eq("user_id", "admin").limit(amount).execute().data
                if leads_to_move:
                    for l in leads_to_move:
                        supabase.table("leads").update({"user_id": target}).eq("id", l['id']).execute()
                    st.success(f"تم نقل {len(leads_to_move)} عميل لـ {target}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("المخزن فارغ!")
        
        st.write("---")
        
        # إضافة مستخدم جديد
        with st.expander("➕ إنشاء حساب جديد"):
            with st.form("new_user"):
                u = st.text_input("Username")
                p = st.text_input("Password")
                if st.form_submit_button("Create"):
                    try:
                        supabase.table("users").insert({"username": u, "password": p, "role": "client"}).execute()
                        st.success("تم الإنشاء")
                    except: st.error("موجود بالفعل")

if st.session_state['logged_in']: main_app()
else: login_screen()
