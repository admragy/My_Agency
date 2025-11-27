# ==================================================
# الصفحة 1: الداتا والنتائج (The Treasure) - نسخة الحذف
# ==================================================
if menu == "📊 الداتا والنتائج":
    st.header("💎 كنز العملاء (Leads Vault)")
    
    # أدوات التحكم العلوية
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("تحديث الجدول 🔄", use_container_width=True):
            st.rerun()
            
    # منطقة الحذف (Admin Zone)
    with st.expander("🗑️ أدوات الحذف والتنظيف (خطر ⚠️)"):
        c1, c2 = st.columns(2)
        
        # 1. حذف رقم معين
        with c1:
            del_phone = st.text_input("أدخل الرقم المراد حذفه:")
            if st.button("مسح هذا العميل"):
                if del_phone:
                    try:
                        supabase.table("leads").delete().eq("phone_number", del_phone).execute()
                        st.success(f"تم مسح الرقم {del_phone} بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"حدث خطأ: {e}")

        # 2. تصفير الجدول بالكامل
        with c2:
            st.write("هل تريد مسح كل الداتا؟")
            confirm = st.checkbox("نعم، أنا متأكد (لا يمكن التراجع)")
            if st.button("💣 تصفير الخزنة (Delete All)") and confirm:
                try:
                    # معادلة لمسح كل الصفوف (id لا يساوي 0)
                    supabase.table("leads").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                    st.toast("تم تنظيف الخزنة بالكامل!", icon="🧹")
                    st.rerun()
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")

    # عرض الجدول
    response = supabase.table("leads").select("*").order("created_at", desc=True).execute()
    leads = response.data
    
    if leads:
        df = pd.DataFrame(leads)
        
        # الإحصائيات
        m1, m2, m3 = st.columns(3)
        m1.metric("إجمالي الصيد", len(df))
        if 'quality' in df.columns:
            excellent = len(df[df['quality'].str.contains('Excellent', na=False)])
            m2.metric("🔥 عملاء لقطة", excellent)
        
        st.markdown("---")
        
        # عرض البيانات
        cols_to_show = ['quality', 'phone_number', 'email', 'source', 'notes', 'created_at']
        available_cols = [c for c in cols_to_show if c in df.columns]
        
        st.dataframe(
            df[available_cols],
            column_config={
                "quality": st.column_config.TextColumn("جودة العميل", width="medium"),
                "phone_number": "الموبايل",
                "email": "الإيميل",
                "created_at": st.column_config.DatetimeColumn("التوقيت", format="D MMM, HH:mm")
            },
            use_container_width=True
        )
    else:
        st.info("📭 الخزنة نظيفة تماماً.")
