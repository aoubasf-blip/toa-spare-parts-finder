from pathlib import Path
import pandas as pd

# ชื่อไฟล์ต้นฉบับ (ตัวใหญ่)
SOURCE_FILE = "Spare parts list for TOA- Combine.xlsx"
# ชื่อไฟล์ใหม่ (ตัวผอม ใช้สำหรับ deploy)
TARGET_FILE = "Spare parts list for TOA- Combine_DATA.xlsx"


def shrink_excel():
    base = Path(__file__).parent
    src = base / SOURCE_FILE
    dst = base / TARGET_FILE

    if not src.exists():
        print(f"ไม่พบไฟล์ต้นฉบับ: {src}")
        return

    print(f"อ่านไฟล์ต้นฉบับ: {src}")
    xls = pd.ExcelFile(src, engine="openpyxl")

    # เก็บ sheet ที่แปลงแล้ว
    sheet_dfs = {}

    for sheet in xls.sheet_names:
        print(f"  >> แปลงชีต: {sheet}")
        # อ่านแบบไม่มี header เพื่อควบคุมเอง
        raw = pd.read_excel(src, sheet_name=sheet, header=None, engine="openpyxl")

        if raw.empty or len(raw) < 3:
            print("     - ข้าม (ข้อมูลน้อยเกิน)")
            continue

        # แถวที่ 2 (index = 1) เป็นหัวคอลัมน์จริง
        header_row = raw.iloc[1]
        df = raw.iloc[2:].copy()
        df.columns = header_row

        # ลบคอลัมน์ header เป็น NaN และ header ซ้ำ
        df = df.loc[:, ~df.columns.isna()]
        df = df.loc[:, ~df.columns.duplicated()]

        # map ชื่อคอลัมน์ให้ตรงกับ app.py
        rename_map = {
            "Spare part code": "Spare Part Code",
            "Description": "Description (EN)",
            "Description（Thai）": "Description (TH)",
            "Description（Chinese）": "Description (CN)",
            "Picture（Product）": "Product Image",
            "Picture\n（Spare part）": "Spare Image",
            "Waranty": "Warranty Type",
            "Unit Price\n(CNY)": "Unit Price (CNY)",
            "Spare parts quantity": "Spare Parts Qty",
        }
        df.rename(
            columns={k: v for k, v in rename_map.items() if k in df.columns},
            inplace=True,
        )

        # ตัดคอลัมน์รูป/คอลัมน์ที่ใหญ่แต่ไม่ใช้ทิ้ง (ลดขนาดไฟล์)
        drop_cols = []
        for col in df.columns:
            col_str = str(col)
            if "picture" in col_str.lower() or "รูป" in col_str:
                drop_cols.append(col)
        if drop_cols:
            print(f"     - ลบคอลัมน์รูป: {drop_cols}")
            df = df.drop(columns=drop_cols)

        # เติม Model / Product Name จากบรรทัดบนลงมา (เหมือนใน app.py)
        if "Model" in df.columns:
            df["Model"] = df["Model"].ffill()
        if "Product Name" in df.columns:
            df["Product Name"] = df["Product Name"].ffill()

        # ลบแถวที่ว่างทั้งแถว
        df = df.dropna(how="all")

        sheet_dfs[sheet] = df

    if not sheet_dfs:
        print("ไม่พบชีตที่ใช้ได้เลย")
        return

    print(f"\nบันทึกไฟล์ใหม่: {dst}")
    with pd.ExcelWriter(dst, engine="openpyxl") as writer:
        for sheet_name, df in sheet_dfs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print("เสร็จแล้ว ✅  ได้ไฟล์ Excel ตัวผอมสำหรับ deploy")


if __name__ == "__main__":
    shrink_excel()
