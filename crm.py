import streamlit as st
import pandas as pd
import requests
from supabase import create_client

# --- 1. إعداد الصفحة ---
st.set_page_config(
    page_title="Mass Hunter V14",
    page_icon="☢️",
    layout="wide"
)

# --- 2. الاتصال بالسحابة ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    API_URL = st.secrets["API_URL"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("⚠️ خطأ في الاتصال: راجع الـ Secrets")
    st.stop()

st.title("☢️ غرفة عمليات - Mass Hunter V14")
st.caption("نظام الصيد النووي متعدد المفاتيح والتحليل الذكي")

# القائمة الجانبية
menu = st.sidebar.radio(
    "القائمة", 
    ["📊 تحليل الداتا (Data)", "🚀 إطلاق الصياد", "➕ إضافة يدوية", "📦 الحملات", "⚙️ الإعدادات"]
)

# ==========================================
# 1. صفحة الداتا (الأهم)
# ==========================================
if menu == "📊 تحليل الداتا (Data)":
    c1, c2 = st.columns([4, 1])
    with c1:
        st.header("💎 الكنز (Leads Vault)")
    with c2:
        if st.button("تحديث 🔄", use_container_width=True):
            st.rerun()

    # جلب الداتا
    leads = supabase.table("leads").select("*").order("created_at", desc=True).execute().data
    
    if leads:
        df = pd.DataFrame(leads)
        
        # --- لوحة العدادات (Metrics) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("الإجمالي", len(df))
        
        # تصنيف الجودة A
        if 'quality' in df.columns:
            a_leads = len(df[df['quality'] == 'A'])
            m2.metric("🔥 عملاء A+ (لقطة)", a_leads)
            
        # تصنيف الاستعجال High
        if 'urgency' in df.columns:
            urgent = len(df[df['urgency'] == 'HIGH'])
            m3.metric("🚨 مستعجلين جداً", urgent)
            
        # تصنيف المنصة
        if 'platform' in df.columns:
            fb = len(df[df['platform'] == 'FACEBOOK'])
            m4.metric("من فيسبوك", fb)
            
        st.markdown("---")
        
        # --- الجدول الذكي ---
        # تجهيز الأعمدة للعرض
        cols = ['quality', 'urgency', 'intent_detected', 'phone_number', 'platform', 'notes', 'created_at']
        # فلترة الأعمدة الموجودة فقط لتجنب الأخطاء
        valid_cols = [c for c in cols if c in df.columns]
        
        st.dataframe(
            df[valid_cols],
            column_config={
                "quality": st.column_config.TextColumn("الجودة", help="A=ممتاز, B=جيد, C=عادي"),
                "urgency": st.column_config.TextColumn("الاستعجال", help="مدى حاجة العميل"),
                "intent_detected": "النية",
                "phone_number": "الموبايل",
                "platform": "المنصة",
                "notes": st.column_config.TextColumn("النص الأصلي / الملاحظات", width="large"),
                "created_at": st.column_config.DatetimeColumn("الوقت", format="D MMM HH:mm")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("الخزنة فارغة.. ابدأ الصيد!")

# ==========================================
# 2. صفحة الصيد (Hunter)
# ==========================================
elif menu == "🚀 إطلاق الصياد":
    st.header("🛰️ مركز التحكم في الصياد")
    st.info("اكتب وصفاً لما تريد، والذكاء الاصطناعي سيولد كلمات البحث المناسبة.")
    
    with st.form("hunt"):
        intent = st.text_area("ماذا تريد؟ (مثال: أنا ببيع كوتشيات جملة في العتبة وعايز تجار)", height=100)
        city = st.text_input("المدينة / المنطقة", "القاهرة")
        
        btn = st.form_submit_button("🚀 إطلاق الصواريخ (Start Hunt)")
        
        if btn and intent:
            try:
                payload = {"intent_sentence": intent, "city": city}
                res = requests.post(f"{API_URL}/start_hunt", json=payload)
                if res.status_code == 200:
                    st.success("✅ تم الإطلاق! الصياد يعمل الآن في الخلفية بذكاء V14.")
                    st.caption("تابع صفحة 'تحليل الداتا' لمشاهدة النتائج لحظياً.")
                else:
                    st.error(f"خطأ في الاتصال: {res.status_code}")
            except Exception as e:
                st.error(f"فشل: {e}")

# ==========================================
# 3. إضافة يدوية
# ==========================================
elif menu == "➕ إضافة يدوية":
    st.header("تسجيل عميل يدوي")
    with st.form("manual"):
        phone = st.text_input("رقم الموبايل")
        note = st.text_input("ملاحظات")
        if st.form_submit_button("حفظ"):
            try:
                supabase.table("leads").upsert({
                    "phone_number": phone, 
                    "source": "Manual", 
                    "status": "NEW",
                    "quality": "Manual",
                    "notes": note
                }, on_conflict="phone_number").execute()
                st.success("تم الحفظ")
            except: st.error("خطأ")

# ==========================================
# 4. الحملات
# ==========================================
elif menu == "📦 الحملات":
    st.header("إعداد الحملة التسويقية")
    current = supabase.table("campaigns").select("*").eq("is_active", True).execute().data
    if current: st.success(f"الحملة النشطة: {current[0]['campaign_name']}")
    
    with st.form("camp"):
        name = st.text_input("اسم الحملة")
        desc = st.text_area("وصف المنتج (لـ AI)")
        img = st.text_input("رابط الصورة")
        if st.form_submit_button("تفعيل"):
            supabase.table("campaigns").update({"is_active": False}).eq("is_active", True).execute()
            supabase.table("campaigns").insert({"campaign_name": name, "product_description": desc, "media_url": img, "is_active": True}).execute()
            st.success("تم التفعيل")
            st.rerun()

# ==========================================
# 5. الإعدادات
# ==========================================
elif menu == "⚙️ الإعدادات":
    st.header("إعدادات المناطق")
    curr = supabase.table("project_settings").select("*").limit(1).execute().data
    val = curr[0]['allowed_cities'] if curr else "القاهرة"
    
    new_val = st.text_input("المناطق المسموحة", value=val)
    if st.button("حفظ"):
        if curr: supabase.table("project_settings").update({"allowed_cities": new_val}).eq("id", curr[0]['id']).execute()
        else: supabase.table("project_settings").insert({"allowed_cities": new_val}).execute()
        st.success("تم الحفظ")
