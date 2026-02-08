import json
import os

import gspread
import pandas as pd
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
    if os.path.exists("credentials.json"):
        try:
            return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        except Exception:
            with open("credentials.json", "r", encoding="utf-8-sig") as fh:
                info = json.load(fh)
            return Credentials.from_service_account_info(info, scopes=SCOPES)

    try:
        if "gcp_service_account" in st.secrets:
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
    worksheet = ensure_worksheet(spreadsheet, "data")
    return spreadsheet, worksheet


def ensure_worksheet(spreadsheet, title: str):
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=2000, cols=10)
        worksheet.append_row(["日期", "金額", "分類", "付款方式", "備註", "使用人", "建立時間"])
        return worksheet


def get_sheet_context():
    client = get_client()
    sheet_id = DEFAULT_SHEET_ID
    if sheet_id.strip():
        try:
            spreadsheet = client.open_by_key(sheet_id.strip())
            worksheet = ensure_worksheet(spreadsheet, "data")
            return spreadsheet, worksheet
        except Exception:
            st.error("無法使用該試算表 ID，請確認已分享給服務帳戶。")
            st.stop()
    return open_or_create_sheet(client, DEFAULT_SHEET_NAME)


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


def worksheet_to_df(worksheet):
    values = worksheet.get_all_values()
    if not values:
        return pd.DataFrame()
    header = values[0]
    data = values[1:]
    return pd.DataFrame(data, columns=header)
