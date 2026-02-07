import json
import os
from datetime import date

import pandas as pd
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_SHEET_NAME = "Family_Expenses"
DEFAULT_SHEET_ID = "1RwxVkaWAJfkhqiwwdRTwEXhdyj8aky-wrZOO0JQNXHQ"
DEFAULT_CATEGORIES = ["餐飲", "交通", "生活", "娛樂", "醫療", "教育", "其他"]
DEFAULT_PAYMENTS = ["現金", "信用卡", "轉帳", "行動支付", "其他"]
DEFAULT_USERS = ["Rick", "Karen", "Max", "Mic"]


def load_credentials():
    # 優先使用本地檔案
    if os.path.exists("credentials.json"):
        try:
            return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        except Exception:
            with open("credentials.json", "r", encoding="utf-8-sig") as fh:
                info = json.load(fh)
            return Credentials.from_service_account_info(info, scopes=SCOPES)

    # 檔案不存在，改讀 Streamlit Secrets
    try:
        if "gcp_service_account" in st.secrets:
            # AttrDict -> dict，避免型別相容問題
            info = dict(st.secrets["gcp_service_account"])
            if info.get("private_key") and info.get("client_email"):
                return Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception as exc:
        st.error(f"解析 Secrets 時發生錯誤: {exc}")

    st.error("找不到 credentials.json，或未正確設定 Streamlit secrets 的 gcp_service_account。")
    st.stop()


def get_client():
    creds = load_credentials()
    return gspread.authorize(creds)


def open_or_create_sheet(client, sheet_name: str):
    try:
        spreadsheet = client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        st.error(
            "找不到該試算表。請先在你的 Google Drive 建立試算表，並分享給服務帳戶的 email。"
        )
        st.stop()
    try:
        worksheet = spreadsheet.worksheet("data")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="data", rows=2000, cols=10)
        worksheet.append_row(["日期", "金額", "分類", "付款方式", "備註", "使用人", "建立時間"])
    return spreadsheet, worksheet


def append_expense_row(worksheet, row):
    worksheet.append_row(row, value_input_option="USER_ENTERED")


def fetch_recent(worksheet, limit=50):
    values = worksheet.get_all_values()
    if len(values) <= 1:
        return pd.DataFrame(columns=values[0] if values else [])
    header = values[0]
    data = values[1:]
    df = pd.DataFrame(data, columns=header)
    if "金額" in df.columns:
        df["金額"] = pd.to_numeric(df["金額"], errors="coerce")
    return df.tail(limit)


st.set_page_config(page_title="家庭記帳", page_icon="🧾", layout="centered")

st.title("家庭記帳")
st.caption("可多人使用，資料寫入 Google 試算表")

st.markdown(
    """
    <style>
    div[data-testid="stRadio"] > div {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
    }
    div[data-testid="stRadio"] label {
        border: 1px solid #e4e7ec;
        border-radius: 14px;
        padding: 10px 12px;
        background: #f8fafc;
        margin: 0 !important;
        font-weight: 600;
        text-align: center;
    }
    div[data-testid="stRadio"] label:hover {
        border-color: #94a3b8;
        background: #f1f5f9;
    }
    div[data-testid="stRadio"] input:checked + div {
        border: 2px solid #2563eb;
        background: #eff6ff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("設定")
    sheet_name = st.text_input("Google 試算表名稱", value=DEFAULT_SHEET_NAME)
    sheet_id = DEFAULT_SHEET_ID
    st.write("使用預設試算表 ID")
    st.write("請先在 Google Drive 建立試算表，並分享給服務帳戶 email")

client = get_client()
if sheet_id.strip():
    try:
        spreadsheet = client.open_by_key(sheet_id.strip())
        try:
            worksheet = spreadsheet.worksheet("data")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="data", rows=2000, cols=10)
            worksheet.append_row(["日期", "金額", "分類", "付款方式", "備註", "使用人", "建立時間"])
    except Exception:
        st.error("無法使用該試算表 ID，請確認已分享給服務帳戶。")
        st.stop()
else:
    spreadsheet, worksheet = open_or_create_sheet(client, sheet_name)

with st.form("expense_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        user = st.radio("使用人", DEFAULT_USERS, horizontal=True)
        expense_date = st.date_input("日期", value=date.today())
        amount = st.number_input("金額", min_value=0.0, step=1.0, format="%.0f")
    with col2:
        payment = st.selectbox("付款方式", DEFAULT_PAYMENTS)
        category = st.selectbox("分類", DEFAULT_CATEGORIES)
        note = st.text_input("備註")

    submitted = st.form_submit_button("新增紀錄")

if submitted:
    if not user.strip():
        st.error("請輸入使用人")
    else:
        row = [
            expense_date.strftime("%Y-%m-%d"),
            amount,
            category,
            payment,
            note.strip(),
            user.strip(),
            date.today().strftime("%Y-%m-%d"),
        ]
        append_expense_row(worksheet, row)
        st.success("已新增到 Google 試算表")

st.subheader("最近紀錄")
recent_df = fetch_recent(worksheet, limit=30)
if recent_df.empty:
    st.info("目前還沒有資料")
else:
    st.dataframe(recent_df, use_container_width=True)

st.subheader("統計")
if not recent_df.empty and "金額" in recent_df.columns:
    summary_user = recent_df.groupby("使用人")["金額"].sum().reset_index()
    summary_category = recent_df.groupby("分類")["金額"].sum().reset_index()
    st.write("按使用人")
    st.dataframe(summary_user, use_container_width=True)
    st.write("按分類")
    st.dataframe(summary_category, use_container_width=True)
