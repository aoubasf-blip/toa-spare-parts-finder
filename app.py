from pathlib import Path
import pandas as pd
import streamlit as st


# =============================
# CONFIG
# =============================

COMBINE_FILE = "Spare parts list for TOA- Combine_DATA.xlsx"
CN_FILE = "TOA main spare parts recommendation DATA.xlsx"


# =============================
# LOAD & MERGE DATA
# =============================

@st.cache_data
def load_data():
    base = Path(__file__).parent
    combine_path = base / COMBINE_FILE
    cn_path = base / CN_FILE

    xls = pd.ExcelFile(combine_path, engine="openpyxl")
    all_parts = []

    for sheet in xls.sheet_names:
        df = pd.read_excel(combine_path, sheet_name=sheet, engine="openpyxl")

        if df.empty:
            continue

        df = df.dropna(how="all")
        df = df.loc[:, ~df.columns.isna()]
        df = df.loc[:, ~df.columns.duplicated()]

        df.insert(0, "Category", sheet)

        rename_map = {
            "Spare part code": "Spare Part Code",
            "Spare part code ": "Spare Part Code",
            "Spare Part code": "Spare Part Code",
            "Spare part Code": "Spare Part Code",
            "Description": "Description (EN)",
            "Description（Thai）": "Description (TH)",
            "Description(Thai)": "Description (TH)",
            "Description （Thai）": "Description (TH)",
            "Description（Chinese）": "Description (CN)",
            "Description(Chinese)": "Description (CN)",
            "Description （Chinese）": "Description (CN)",
            "Picture（Product）": "Product Image",
            "Picture( Product )": "Product Image",
            "Picture （Product）": "Product Image",
            "Picture\n（Spare part）": "Spare Image",
            "Picture( Spare part )": "Spare Image",
            "Picture （Spare part）": "Spare Image",
            "Waranty": "Warranty Type",
            "Warranty": "Warranty Type",
            "Unit Price\n(CNY)": "Unit Price (CNY)",
            "Unit Price (CNY)": "Unit Price (CNY)",
            "Spare parts quantity": "Spare Parts Qty",
        }
        df.rename(
            columns={k: v for k, v in rename_map.items() if k in df.columns},
            inplace=True,
        )

        if "Model" in df.columns:
            df["Model"] = df["Model"].ffill()
        if "Product Name" in df.columns:
            df["Product Name"] = df["Product Name"].ffill()

        all_parts.append(df)

    if not all_parts:
        raise ValueError("ไม่พบข้อมูลในไฟล์ Combine_DATA.xlsx เลย")

    parts = pd.concat(all_parts, ignore_index=True)
    parts = parts.loc[:, ~parts.columns.duplicated()]

    if "Spare Part Code" not in parts.columns:
        raise KeyError(
            "ไม่พบคอลัมน์ 'Spare Part Code' ในไฟล์ Combine_DATA.xlsx\n"
            "กรุณาเปิดไฟล์แล้วเช็คว่าชื่อคอลัมน์เขียนว่า 'Spare Part Code' หรือเปล่า"
        )

    parts["Spare Part Code"] = parts["Spare Part Code"].astype(str).str.strip()
    if "Model" not in parts.columns:
        parts["Model"] = ""
    if "Product Name" not in parts.columns:
        parts["Product Name"] = ""

    cn = pd.read_excel(cn_path, sheet_name="Sheet1", engine="openpyxl")

    cn.rename(
        columns={
            "Product name": "CN Product Name",
            "Spare part number": "Spare Part Code",
            "Spare part name": "CN Spare Part Name",
            "Recommended Quantity": "CN Recommended Qty",
        },
        inplace=True,
    )

    cn = cn.loc[:, ~cn.columns.duplicated()]

    keep_cols = []
    for col in [
        "Model",
        "Spare Part Code",
        "CN Product Name",
        "CN Spare Part Name",
        "CN Recommended Qty",
        "Remark",
    ]:
        if col in cn.columns:
            keep_cols.append(col)

    cn = cn[keep_cols]

    if "Spare Part Code" in cn.columns:
        cn["Spare Part Code"] = cn["Spare Part Code"].astype(str).str.strip()
    if "Model" not in cn.columns:
        cn["Model"] = ""

    merged = parts.merge(
        cn,
        on=["Model", "Spare Part Code"],
        how="left",
        suffixes=("", "_CN"),
    )

    return merged


# =============================
# HELPER: MODEL OPTIONS WITH GROUPING
# =============================

def build_model_options(df: pd.DataFrame, keyword: str = "", category: str | None = None):
    """สร้าง list dropdown: (label, model) filter ด้วย category + keyword"""
    mdf = df.copy()

    if category and category != "ทั้งหมด" and "Category" in mdf.columns:
        mdf = mdf[mdf["Category"] == category]

    if keyword:
        kw = keyword.lower()
        mask = pd.Series(False, index=mdf.index)
        for col in ["Model", "Product Name", "CN Product Name"]:
            if col in mdf.columns:
                mask = mask | mdf[col].astype(str).str.lower().str.contains(kw)
        mdf = mdf[mask]

    if "Model" not in mdf.columns:
        return []

    subset_cols = [c for c in ["Model", "Product Name", "Category"] if c in mdf.columns]
    models_df = (
        mdf[subset_cols]
        .astype(str)
        .replace("nan", "")
        .drop_duplicates()
    )

    options: list[tuple[str, str]] = []
    for _, r in models_df.iterrows():
        model = r.get("Model", "").strip()
        if not model:
            continue
        pname = r.get("Product Name", "").strip()
        cat = r.get("Category", "").strip()

        parts = []
        if cat:
            parts.append(cat)
        parts.append(model)
        if pname:
            parts.append(pname)
        label = " | ".join(parts)
        options.append((label, model))

    options.sort(key=lambda x: x[0].lower())
    return options


# =============================
# UI / APP
# =============================

def main():
    st.set_page_config(
        page_title="TOA | JOMOO After Sale Service",
        layout="wide",
    )

    # ---------- GLOBAL CSS ----------
    st.markdown(
        """
        <style>
        :root {
            --toa-navy: #071427;
            --toa-blue: #1B4EA3;
            --toa-gold: #C89A55;
            --toa-bg: #F4F7FB;
        }

        header[data-testid="stHeader"] {display: none;}
        [data-testid="stToolbar"] {display: none;}
        .block-container {padding-top: 0.5rem;}

        .stApp {
            background: var(--toa-bg);
            font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .hero {
            width: 100%;
            padding: 1.4rem 1.8rem;
            border-radius: 18px;
            background: radial-gradient(circle at top left, #213b72 0%, #050B14 60%);
            color: #ffffff;
            margin-bottom: 1.4rem;
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            box-shadow: 0 14px 40px rgba(0,0,0,0.25);
        }
        .hero-title {
            font-size: 1.7rem;
            font-weight: 800;
            letter-spacing: 0.03em;
        }
        .hero-sub {
            opacity: 0.9;
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .search-panel {
            padding: 0.9rem 1.1rem;
            border-radius: 18px;
            background: #0B1220;
            color: #ffffff;
            box-shadow: 0 14px 30px rgba(15,23,42,0.25);
        }
        .search-panel h4 {
            margin-bottom: 0.4rem;
        }

        .card {
            padding: 0.9rem 1.1rem;      /* กระชับลง */
            border-radius: 18px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
            margin-bottom: 1.0rem;       /* ระยะห่างการ์ดต่อการ์ด */
            background-color: #ffffff;
        }

        .field-label {
            font-weight: 600;
            color: #4B5563;
        }

        .card h3, .card h4, .card h5 {
            color: var(--toa-navy);
        }

        .stAlert.success {
            background-color: #E0F2FE;
            border-radius: 999px;
        }
        .stAlert.warning {
            background-color: #FEF3C7;
            border-radius: 999px;
        }

        .subheading {
            font-size: 0.95rem;
            color: #6B7280;
            margin-bottom: 0.15rem;      /* เดิมเยอะกว่านี้ */
        }

        .card hr {
            margin: 0.35rem 0 0.55rem 0;
            border-color: #E5E7EB;
        }

        .stRadio > div[role="radiogroup"] {
            gap: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------- HERO ----------
    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">TOA | JOMOO After Sale Service Teams</div>
            <div class="hero-sub">
                ศูนย์กลางข้อมูลอะไหล่สำหรับทีม After Sale Service ของ TOA / JOMOO
                ค้นหาจากรหัสอะไหล่ หรือค้นจากรุ่นสินค้า (เช่น X70, TS3) เพื่อดูอะไหล่ทั้งหมดของรุ่นนั้น
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # โหลดข้อมูล
    df = load_data()

    base = Path(__file__).parent
    images_dir = base / "images"
    product_dir = images_dir / "product"
    spare_dir = images_dir / "spare"

    # ---------- helper แสดง card ----------
    def render_cards(rows: pd.DataFrame):
        for _, row in rows.iterrows():
            code = str(row.get("Spare Part Code", "") or "").strip()
            model = str(row.get("Model", "") or "").strip()
            pname = str(row.get("Product Name", "") or "").strip()

            prod_src = None
            spare_src = None

            if code:
                for p in [images_dir / f"{code}.png", spare_dir / f"{code}.png"]:
                    if p.exists():
                        spare_src = p.as_posix()
                        break

            if not spare_src:
                for key in ["Spare Image", "Product Image"]:
                    val = row.get(key, "")
                    if isinstance(val, str) and val.strip():
                        spare_src = val.strip()
                        break

            if model:
                raw_model_path = product_dir / f"{model}.png"
                safe_model = "".join(ch if ch.isalnum() else "_" for ch in model)
                safe_model_path = product_dir / f"{safe_model}.png"

                if raw_model_path.exists():
                    prod_src = raw_model_path.as_posix()
                elif safe_model_path.exists():
                    prod_src = safe_model_path.as_posix()

            if not prod_src and pname:
                safe_name = "".join(ch if ch.isalnum() else "_" for ch in pname)
                pname_path = product_dir / f"{safe_name}.png"
                if pname_path.exists():
                    prod_src = pname_path.as_posix()

            if (
                not prod_src
                and isinstance(row.get("Product Image", ""), str)
                and row["Product Image"].strip()
            ):
                prod_src = row["Product Image"].strip()

            st.markdown('<div class="card">', unsafe_allow_html=True)
            col_img, col_info = st.columns([1.5, 2.0])

            with col_img:
                col_prod, col_spare = st.columns(2)

                with col_prod:
                    if prod_src:
                        st.image(
                            prod_src,
                            use_container_width=True,
                            caption="Product image",
                        )
                    else:
                        st.markdown("**🛁 Product image**")
                        st.caption(
                            "ถ้ามีรูปสินค้า ให้เซฟเป็น .png แล้ววางในโฟลเดอร์ "
                            "`images/product/` เช่น `images/product/ModelName.png`"
                        )

                with col_spare:
                    if spare_src:
                        st.image(
                            spare_src,
                            use_container_width=True,
                            caption="Spare part image",
                        )
                    else:
                        st.markdown("**🔧 Spare part image**")
                        st.caption(
                            "ถ้ามีรูปอะไหล่ ให้เซฟเป็นไฟล์ .png ชื่อเดียวกับ Spare Part Code "
                            "แล้ววางในโฟลเดอร์ `images/` หรือ `images/spare/`"
                        )

            with col_info:
                st.markdown(f"### {code}")

                sub_parts = []
                if model:
                    sub_parts.append(f"Model: {model}")
                if pname:
                    sub_parts.append(pname)
                if sub_parts:
                    st.markdown(
                        f"<div class='subheading'>{' · '.join(sub_parts)}</div>",
                        unsafe_allow_html=True,
                    )

                # --- Basic info ---
                st.markdown("**ข้อมูลหลัก (Basic Info)**")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(
                        f"<span class='field-label'>Category:</span> {row.get('Category', '')}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span class='field-label'>Model:</span> {model}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span class='field-label'>Warranty Type:</span> {row.get('Warranty Type', '')}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span class='field-label'>Warranty Period:</span> {row.get('Warranty Period', '')}",
                        unsafe_allow_html=True,
                    )

                with c2:
                    st.markdown(
                        f"<span class='field-label'>Product Name:</span> {pname}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span class='field-label'>Unit Price (CNY):</span> {row.get('Unit Price (CNY)', '')}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span class='field-label'>Spare Parts Qty (from list):</span> {row.get('Spare Parts Qty', '')}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span class='field-label'>Remark:</span> {row.get('Remark', '')}",
                        unsafe_allow_html=True,
                    )

                # เส้นคั่นแบบ margin สั้น
                st.markdown(
                    "<hr style='margin:0.35rem 0 0.55rem 0; border-color:#E5E7EB;'/>",
                    unsafe_allow_html=True,
                )

                # --- Description ---
                st.markdown("**คำอธิบาย / Description**")
                th = row.get("Description (TH)", "")
                en = row.get("Description (EN)", "")
                cn_txt = row.get("Description (CN)", "")
                if isinstance(th, str) and th.strip():
                    st.markdown(
                        f"<span class='field-label'>Thai:</span> {th}",
                        unsafe_allow_html=True,
                    )
                if isinstance(en, str) and en.strip():
                    st.markdown(
                        f"<span class='field-label'>English:</span> {en}",
                        unsafe_allow_html=True,
                    )
                if isinstance(cn_txt, str) and cn_txt.strip():
                    st.markdown(
                        f"<span class='field-label'>Chinese:</span> {cn_txt}",
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    "<hr style='margin:0.35rem 0 0.55rem 0; border-color:#E5E7EB;'/>",
                    unsafe_allow_html=True,
                )

                # --- China Recommendation ---
                st.markdown("**China Recommendation**")
                st.markdown(
                    f"<span class='field-label'>CN Product Name:</span> {row.get('CN Product Name', '')}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<span class='field-label'>CN Spare Part Name:</span> {row.get('CN Spare Part Name', '')}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<span class='field-label'>CN Recommended Qty:</span> {row.get('CN Recommended Qty', '')}",
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

    # ---------- LAYOUT: ซ้าย (search) / ขวา (result) ----------
    search_col, result_col = st.columns([0.9, 2.1])

    result_df: pd.DataFrame | None = None
    status_kind = "info"
    status_text = ""

    # ---------- SEARCH PANEL (LEFT) ----------
    with search_col:
        st.markdown('<div class="search-panel">', unsafe_allow_html=True)
        st.markdown("#### 🔍 Search")

        search_mode = st.radio(
            "Search mode",
            ("ค้นหาจาก Spare Part Code", "ค้นหาจาก Product / Model"),
            label_visibility="visible",
        )

        if search_mode == "ค้นหาจาก Spare Part Code":
            code_input = st.text_input(
                "Spare Part Code", placeholder="เช่น KD236-1179"
            ).strip()
            exact_match = st.checkbox("ค้นหาแบบตรงตัว (Exact match)", value=True)

            if not code_input:
                status_kind = "info"
                status_text = "พิมพ์ **Spare Part Code** ทางซ้ายเพื่อเริ่มค้นหา"
            else:
                if "Spare Part Code" not in df.columns:
                    status_kind = "error"
                    status_text = "ไม่พบคอลัมน์ 'Spare Part Code' ในข้อมูล"
                else:
                    if exact_match:
                        mask = df["Spare Part Code"].str.lower() == code_input.lower()
                    else:
                        mask = df["Spare Part Code"].str.contains(
                            code_input, case=False, na=False
                        )

                    result_df = df[mask]

                    if result_df.empty:
                        status_kind = "warning"
                        status_text = f"ไม่พบอะไหล่ที่มีโค้ด: **{code_input}**"
                        result_df = None
                    else:
                        status_kind = "success"
                        status_text = f"พบ {len(result_df)} รายการสำหรับโค้ด: **{code_input}**"

        else:
            st.markdown("**เลือกวิธีค้นหา Product / Model**")
            product_search_mode = st.radio(
                "ค้นหาด้วย",
                ("เลือกจาก Model dropdown", "พิมพ์คำค้น (Product / Model)"),
                label_visibility="collapsed",
            )

            if product_search_mode == "เลือกจาก Model dropdown":
                # หมวดหมู่
                cat_list = ["ทั้งหมด"]
                if "Category" in df.columns:
                    cat_unique = (
                        df["Category"]
                        .astype(str)
                        .str.strip()
                        .replace("nan", "")
                        .dropna()
                        .unique()
                    )
                    cat_list += sorted(cat_unique)

                category_selected = st.selectbox(
                    "หมวดหมู่สินค้า", options=cat_list
                )

                keyword_filter = st.text_input(
                    "ตัวกรองชื่อสั้นๆ (เช่น x70, ts3)",
                    placeholder="พิมพ์คำบางส่วนในชื่อรุ่น / product",
                ).strip()

                options = build_model_options(
                    df, keyword=keyword_filter, category=category_selected
                )

                if not options:
                    status_kind = "info"
                    status_text = (
                        "ยังไม่พบ Model ที่ตรงกับเงื่อนไขที่เลือก\n"
                        "ลองเปลี่ยนหมวดหมู่ หรือเคลียร์ตัวกรองชื่อสั้นดูก่อน"
                    )
                else:
                    labels = ["— เลือก Model —"] + [opt[0] for opt in options]
                    label_selected = st.selectbox("เลือก Model", options=labels)

                    if label_selected == "— เลือก Model —":
                        status_kind = "info"
                        status_text = "เลือก Model ด้านบนเพื่อดูรายการอะไหล่ทั้งหมดของรุ่นนั้น"
                    else:
                        label_to_model = {lbl: mdl for lbl, mdl in options}
                        model_selected = label_to_model[label_selected]

                        mask = df["Model"].astype(str).str.strip() == model_selected
                        tmp = df[mask].copy()

                        if tmp.empty:
                            status_kind = "warning"
                            status_text = f"ไม่พบอะไหล่สำหรับ Model: **{model_selected}**"
                        else:
                            result_df = tmp
                            status_kind = "success"
                            status_text = (
                                f"พบอะไหล่ {len(result_df)} รายการสำหรับ Model: "
                                f"**{model_selected}**"
                            )
            else:
                product_input = st.text_input(
                    "Product / Model",
                    placeholder="เช่น X70, TS3, ZD9640 หรือคำบางส่วนในชื่อรุ่น",
                ).strip()

                if not product_input:
                    status_kind = "info"
                    status_text = (
                        "พิมพ์ชื่อรุ่น หรือคำในชื่อ Product / Model ด้านบน "
                        "หรือเลือกจาก Model dropdown ก็ได้"
                    )
                else:
                    mask = pd.Series(False, index=df.index)

                    if "Model" in df.columns:
                        mask = mask | df["Model"].astype(str).str.contains(
                            product_input, case=False, na=False
                        )
                    if "Product Name" in df.columns:
                        mask = mask | df["Product Name"].astype(str).str.contains(
                            product_input, case=False, na=False
                        )
                    if "CN Product Name" in df.columns:
                        mask = mask | df["CN Product Name"].astype(str).str.contains(
                            product_input, case=False, na=False
                        )

                    tmp = df[mask].copy()

                    if tmp.empty:
                        status_kind = "warning"
                        status_text = (
                            f"ไม่พบ Product / Model ที่ตรงกับคำว่า: **{product_input}**"
                        )
                    else:
                        result_df = tmp
                        status_kind = "success"
                        status_text = (
                            f"พบอะไหล่ {len(result_df)} รายการสำหรับคำค้น: "
                            f"**{product_input}**"
                        )

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- RESULT PANEL (RIGHT) ----------
    with result_col:
        if status_text:
            if status_kind == "info":
                st.info(status_text)
            elif status_kind == "warning":
                st.warning(status_text)
            elif status_kind == "error":
                st.error(status_text)
            elif status_kind == "success":
                st.success(status_text)

        if result_df is not None and not result_df.empty:
            sort_cols = [c for c in ["Model", "Spare Part Code"] if c in result_df.columns]
            if sort_cols:
                result_df = result_df.sort_values(sort_cols)

            summary_cols = [c for c in [
                "Model",
                "Product Name",
                "Spare Part Code",
                "Description (TH)",
                "Description (EN)",
                "Spare Parts Qty",
            ] if c in result_df.columns]

            if summary_cols:
                st.markdown("**ภาพรวมอะไหล่ของรุ่นนี้ (Summary List)**")
                st.dataframe(
                    result_df[summary_cols].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("---")
            st.markdown("**รายละเอียดแต่ละอะไหล่ (Detail View)**")
            render_cards(result_df)


if __name__ == "__main__":
    main()
