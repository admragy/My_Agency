import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from io import BytesIO
import time
import datetime
from streamlit_option_menu import option_menu

# --- 1. إعداد الصفحة ---
st.set_page_config(page_title="Growth System", layout="wide", page_icon="📈")

# --- 2. التصميم (Mobile Friendly + Professional) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .block-container { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { direction: rtl; text-align: right; }
    /* إظهار السهم */
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); z-index: 99999; }
    button[kind="header"] { color: #2563EB !important; }
    /* تنسيق الكروت */
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
    st.session_state.update({'logged_in': False, 'user': '', 'role': '', 'perms': {}})

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 10, 1])
    with c2:
        st.info("👋 مرحباً بك في النظام")
        with st.form("login"):
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول", use_container_width=True):
                try:
                    res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
                    if res.data and res.data[0]['is_active']:
                        user_data = res.data[0]
                        st.session_state['logged_in'] = True
                        st.session_state['user'] = u
                        st.session_state['role'] = user_data['role']
                        # حفظ الصلاحيات
                        st.session_state['perms'] = {
                            'hunt': user_data.get('can_hunt', True),
                            'camp': user_data.get('can_campaign', True),
                            'share': user_data.get('can_share', True)
                        }
                        st.rerun()
                    else: st.error("بيانات خطأ")
                except: st.error("خطأ اتصال")

# --- 5. التطبيق ---
def main_app():
    user = st.session_state['user']
    role = st.session_state['role']
    perms = st.session_state['perms']
    
    with st.sidebar:
        st.write(f"👤 **{user}**")
        
        opts = ["الرئيسية", "قاعدة البيانات"]
        icons = ["house", "table"]
        
        if perms['hunt']: 
            opts.append("الصياد الذكي")
            icons.append("search")
        if perms['camp']:
            opts.append("الحملات")
            icons.append("send")
        
        opts.append("إضافة يدوية")
        icons.append("plus-circle")
        
        if role == 'admin':
            opts.append("الإدارة والتوزيع")
            icons.append("gear")
            
        selected = option_menu("القائمة", opts, icons=icons, default_index=0)
        
        st.divider()
        if st.button("خروج", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    # === 1. الرئيسية ===
    if selected == "الرئيسية":
        st.subheader("لوحة المعلومات")
        data = supabase.table("leads").select("*").eq("user_id", user).execute().data
        df = pd.DataFrame(data) if data else pd.DataFrame()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي العملاء", len(df))
        hot = len(df[df['quality'].str.contains('Excellent|Target', na=False)]) if not df.empty else 0
        c2.metric("عملاء لقطة 🔥", hot)
        c3.metric("من القناص", len(df[df['source'].str.contains('Sniper', na=False)]) if not df.empty else 0)

    # === 2. قاعدة البيانات (Data) ===
    elif selected == "قاعدة البيانات":
        st.subheader("🗂️ إدارة الداتا")
        
        c1, c2, c3 = st.columns(3)
        status_filter = c1.selectbox("الحالة", ["الكل", "جديد", "تم التواصل"])
        source_filter = c2.selectbox("المصدر", ["الكل", "صيد", "قنص", "يدوي"])
        if c3.button("تحديث 🔄", use_container_width=True): st.rerun()
        
        query = supabase.table("leads").select("*").eq("user_id", user).order("created_at", desc=True)
        if status_filter == "جديد": query = query.eq("status", "NEW")
        elif status_filter == "تم التواصل": query = query.eq("status", "CONTACTED")
        if source_filter == "صيد": query = query.ilike("source", "%Hunter%")
        elif source_filter == "قنص": query = query.ilike("source", "%Sniper%")
        
        leads = query.execute().data
        
        if leads:
            df = pd.DataFrame(leads)
            
            # زرار التحميل
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 تحميل Excel", output.getvalue(), f"leads_{user}.xlsx", "application/vnd.ms-excel")
            
            df['Link'] = df['notes'].str.replace('Link: ', '', regex=False)
            st.dataframe(
                df[['quality', 'phone_number', 'email', 'source', 'Link']],
                column_config={"Link": st.column_config.LinkColumn("المصدر", display_text="فتح")},
                use_container_width=True
            )
            
            with st.expander("🗑️ حذف"):
                d = st.text_input("رقم للحذف")
                if st.button("مسح"):
                    supabase.table("leads").delete().eq("phone_number", d).execute()
                    st.rerun()
        else: st.info("لا توجد بيانات.")

    # === 3. الصياد (Hunter + Sniper) ===
    elif selected == "الصياد الذكي":
        st.subheader("🎣 محرك الصيد")
        
        mode = st.radio("الوضع:", ["🌊 صيد عام (كلمات)", "🏹 قناص (منافسين)"], horizontal=True)
        
        with st.form("hunt"):
            c1, c2 = st.columns([3, 1])
            with c1:
                if "قناص" in mode:
                    intent = st.text_input("اسم المنافس / البراند", placeholder="مثال: فودافون / مدينتي")
                else:
                    intent = st.text_input("هدفك (بصيغة الزبون)", placeholder="مثال: مطلوب شقة / عايز استثمر")
            with c2:
                city = st.text_input("المنطقة", "القاهرة")
            
            time_opt = st.selectbox("الزمن", ["أي وقت", "آخر شهر", "آخر 24 ساعة"])
            time_map = {"أي وقت": "qdr:y", "آخر شهر": "qdr:m", "آخر 24 ساعة": "qdr:d"}
            
            if st.form_submit_button("إطلاق 🚀", use_container_width=True):
                try:
                    search_mode = "sniper" if "قناص" in mode else "general"
                    payload = {
                        "intent_sentence": intent, "city": city, 
                        "time_filter": time_map[time_opt], 
                        "user_id": user,
                        "mode": search_mode
                    }
                    requests.post(f"{API_URL}/start_hunt", json=payload)
                    st.success("تم الإطلاق! تابع صفحة الداتا.")
                except: st.error("خطأ اتصال")

    # === 4. الحملات ===
    elif selected == "الحملات":
        st.subheader("📩 رسائل الواتساب")
        with st.form("c"):
            n = st.text_input("اسم العرض")
            d = st.text_area("النص")
            if st.form_submit_button("حفظ"):
                supabase.table("campaigns").update({"is_active": False}).eq("is_active", True).execute()
                supabase.table("campaigns").insert({"campaign_name": n, "product_description": d, "is_active": True}).execute()
                st.success("تم")

    # === 5. إضافة يدوية ===
    elif selected == "إضافة يدوية":
        st.subheader("📥 إدخال داتا")
        tab1, tab2 = st.tabs(["يدوي", "Excel"])
        with tab1:
            with st.form("m"):
                ph = st.text_input("الرقم")
                nt = st.text_input("الاسم")
                if st.form_submit_button("حفظ"):
                    supabase.table("leads").insert({"phone_number": ph, "notes": nt, "source": "Manual", "user_id": user, "status": "NEW"}).execute()
                    st.success("تم")
        with tab2:
            f = st.file_uploader("ملف Excel", type=['xlsx'])
            if f and st.button("رفع"):
                try:
                    dd = pd.read_excel(f)
                    for i, r in dd.iterrows():
                        supabase.table("leads").insert({"phone_number": str(r['phone']), "source": "Excel", "user_id": user, "status": "NEW"}).execute()
                    st.success("تم")
                except: st.error("تأكد من عمود phone")

    # === 6. الإدارة (Admin) ===
    elif selected == "الإدارة والتوزيع" and role == 'admin':
        st.subheader("👮‍♂️ التحكم المركزي")
        
        tab_a, tab_b = st.tabs(["توزيع الداتا", "المستخدمين"])
        
        with tab_a:
            admin_leads = supabase.table("leads").select("*", count="exact").eq("user_id", "admin").execute().count
            st.metric("مخزون الأدمن", admin_leads)
            
            c1, c2 = st.columns(2)
            users_res = supabase.table("users").select("username").neq("username", "admin").execute().data
            target = c1.selectbox("إرسال إلى", [u['username'] for u in users_res])
            amount = c2.number_input("العدد", 1, 1000, 50)
            
            if st.button("تحويل داتا"):
                leads_to_move = supabase.table("leads").select("id").eq("user_id", "admin").limit(amount).execute().data
                if leads_to_move:
                    for l in leads_to_move:
                        supabase.table("leads").update({"user_id": target}).eq("id", l['id']).execute()
                    st.success(f"تم نقل {len(leads_to_move)} عميل")
                    time.sleep(1)
                    st.rerun()
        
        with tab_b:
            with st.form("nu"):
                u = st.text_input("يوزر")
                p = st.text_input("باس")
                if st.form_submit_button("إضافة عميل"):
                    supabase.table("users").insert({"username": u, "password": p, "role": "client"}).execute()
                    st.success("تم")

if st.session_state['logged_in']: main_app()
else: login_screen()
