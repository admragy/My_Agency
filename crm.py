import streamlit as st
import pandas as pd
import requests
from supabase import create_client

# --- 1. إعداد الصفحة والتصميم ---
st.set_page_config(
    page_title="Agency Geniuses",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. الاتصال بالسحابة (Secrets) ---
try:
    # قراءة المفاتيح من إعدادات Streamlit Cloud
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    API_URL = st.secrets["API_URL"]
    
    # إنشاء اتصال مباشر بالداتابيس
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("⚠️ خطأ في الاتصال: تأكد من وضع المفاتيح في Secrets.")
    st.stop()

# --- 3. العنوان الرئيسي ---
st.title("🦅 غرفة عمليات الوكالة الذكية")
st.markdown("---")

# --- 4. القائمة الجانبية ---
menu = st.sidebar.radio(
    "القائمة الرئيسية", 
    ["📊 الداتا والنتائج", "🕵️‍♂️ الصياد الذكي", "➕ إضافة عميل يدوي", "🚀 إدارة الحملات", "⚙️ إعدادات المناطق"]
)

# ==================================================
# الصفحة 1: الداتا والنتائج (The Treasure)
# ==================================================
if menu == "📊 الداتا والنتائج":
    st.header("💎 كنز العملاء (Leads Vault)")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("تحديث الجدول 🔄", use_container_width=True):
            st.rerun()
            
    # جلب الداتا (الأحدث أولاً)
    response = supabase.table("leads").select("*").order("created_at", desc=True).execute()
    leads = response.data
    
    if leads:
        df = pd.DataFrame(leads)
        
        # إحصائيات سريعة (Metrics)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي الصيد", len(df))
        
        # حساب التصنيفات لو العمود موجود
        if 'quality' in df.columns:
            excellent = len(df[df['quality'].str.contains('Excellent', na=False)])
            very_good = len(df[df['quality'].str.contains('Very', na=False)])
            m2.metric("🔥 عملاء لقطة", excellent)
            m3.metric("⭐ جيد جداً", very_good)
        
        emails_only = len(df[df['status'] == 'EMAIL_ONLY'])
        m4.metric("📧 إيميلات", emails_only)
        
        st.markdown("---")
        
        # تنظيف الجدول للعرض (اختيار أعمدة معينة)
        # نتأكد إن الأعمدة موجودة عشان ميحصلش خطأ
        cols_to_show = ['quality', 'phone_number', 'email', 'source', 'notes', 'created_at']
        available_cols = [c for c in cols_to_show if c in df.columns]
        
        st.dataframe(
            df[available_cols],
            column_config={
                "quality": st.column_config.TextColumn("جودة العميل", width="medium"),
                "phone_number": st.column_config.TextColumn("الموبايل", width="medium"),
                "email": "البريد الإلكتروني",
                "source": "المصدر",
                "notes": "ملاحظات / الرابط",
                "created_at": st.column_config.DatetimeColumn("توقيت الصيد", format="D MMM, HH:mm")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("📭 الخزنة فارغة.. اذهب للصياد واملأها!")

# ==================================================
# الصفحة 2: الصياد الذكي (Smart Hunter)
# ==================================================
elif menu == "🕵️‍♂️ الصياد الذكي":
    st.header("🎣 إطلاق الصياد (Hunter V12)")
    st.info("اكتب جملة تشرح هدفك، والذكاء الاصطناعي سيحدد أفضل استراتيجية بحث.")
    
    with st.form("hunt_form"):
        c1, c2 = st.columns([3, 1])
        with c1:
            intent = st.text_input("ماذا تريد؟ (مثال: أنا دكتور أسنان وعايز حالات زراعة / ببيع عقارات في التجمع)")
        with c2:
            city = st.text_input("المدينة المستهدفة", "القاهرة")
            
        submitted = st.form_submit_button("🚀 اطلق الصياد الآن")
        
        if submitted and intent:
            with st.spinner("جاري الاتصال بالمخ وتشغيل المحركات..."):
                try:
                    # إرسال الطلب لـ Render
                    payload = {"intent_sentence": intent, "city": city}
                    res = requests.post(f"{API_URL}/start_hunt", json=payload)
                    
                    if res.status_code == 200:
                        st.success(f"✅ تم الإطلاق بنجاح! الصياد يعمل الآن في الخلفية.")
                        st.caption("يمكنك متابعة النتائج في صفحة 'الداتا' بعد دقيقة.")
                    else:
                        st.error(f"حدث خطأ في الاتصال بالسيرفر: {res.status_code}")
                except Exception as e:
                    st.error(f"فشل الاتصال: {e}")

# ==================================================
# الصفحة 3: إضافة عميل يدوي (Manual Add)
# ==================================================
elif menu == "➕ إضافة عميل يدوي":
    st.header("📝 تسجيل عميل جديد")
    
    with st.form("manual_entry"):
        phone = st.text_input("رقم الهاتف (01xxxxxxxxx)")
        email = st.text_input("الإيميل (اختياري)")
        notes = st.text_area("ملاحظات عن العميل")
        
        save_btn = st.form_submit_button("حفظ في الداتابيس")
        
        if save_btn and (phone or email):
            data = {
                "phone_number": phone if phone else f"manual_{email}",
                "email": email,
                "source": "Manual Entry",
                "status": "NEW",
                "quality": "Manual ✅",
                "notes": notes
            }
            try:
                supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
                st.success("تم الحفظ بنجاح! العميل جاهز للمراسلة.")
            except Exception as e:
                st.error(f"خطأ أثناء الحفظ: {e}")

# ==================================================
# الصفحة 4: إدارة الحملات (Campaigns)
# ==================================================
elif menu == "🚀 إدارة الحملات":
    st.header("📦 تجهيز العرض والمنتج")
    st.write("هنا بتحدد الـ AI هيقول إيه للعملاء، والصورة اللي هتتبعتلهم.")
    
    # عرض الحملة الحالية
    current_camp = supabase.table("campaigns").select("*").eq("is_active", True).execute().data
    if current_camp:
        st.info(f"✅ الحملة النشطة حالياً: **{current_camp[0]['campaign_name']}**")
    
    with st.form("campaign_form"):
        name = st.text_input("اسم الحملة الجديد")
        desc = st.text_area("وصف المنتج / السكريبت (الـ AI هيذاكر الكلام ده)")
        media = st.text_input("رابط الصورة أو الفيديو (Direct Link)")
        
        submit_camp = st.form_submit_button("تنشيط الحملة الجديدة")
        
        if submit_camp:
            # 1. إيقاف القديم
            supabase.table("campaigns").update({"is_active": False}).eq("is_active", True).execute()
            # 2. تفعيل الجديد
            supabase.table("campaigns").insert({
                "campaign_name": name,
                "product_description": desc,
                "media_url": media,
                "is_active": True
            }).execute()
            st.success("تم تفعيل الحملة! الـ AI جاهز للبيع.")
            st.rerun()

# ==================================================
# الصفحة 5: الإعدادات (Settings)
# ==================================================
elif menu == "⚙️ إعدادات المناطق":
    st.header("📍 الفلترة الجغرافية")
    
    # جلب الإعدادات الحالية
    settings = supabase.table("project_settings").select("*").limit(1).execute().data
    current_zones = settings[0]['allowed_cities'] if settings else "القاهرة"
    current_msg = settings[0]['reject_message'] if settings else "نعتذر، الخدمة غير متاحة."
    
    with st.form("geo_settings"):
        zones = st.text_area("المناطق المسموحة (افصل بفاصلة)", value=current_zones)
        rej_msg = st.text_input("رسالة الرفض (للمناطق الأخرى)", value=current_msg)
        
        save_geo = st.form_submit_button("حفظ الإعدادات")
        
        if save_geo:
            if settings:
                supabase.table("project_settings").update({"allowed_cities": zones, "reject_message": rej_msg}).eq("id", settings[0]['id']).execute()
            else:
                supabase.table("project_settings").insert({"allowed_cities": zones, "reject_message": rej_msg}).execute()
            st.success("تم تحديث مناطق العمل.")

