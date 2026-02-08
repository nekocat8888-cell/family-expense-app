from datetime import date

import streamlit as st

from utils import (
    DEFAULT_CATEGORIES,
    DEFAULT_PAYMENTS,
    DEFAULT_USERS,
    append_expense_row,
    fetch_recent,
    get_sheet_context,
)

st.set_page_config(page_title="家庭記帳", page_icon="🧾", layout="centered")

st.title("家庭記帳")
st.caption("可多人使用，資料寫入 Google 試算表")

st.subheader("功能切換")
if "section" not in st.session_state:
    st.session_state["section"] = "記帳"

def _set_section(name: str):
    st.session_state["section"] = name

col1, col2, col3 = st.columns(3)
with col1:
    st.button("記帳", use_container_width=True, on_click=_set_section, args=("記帳",))
with col2:
    st.button("統計記帳結果", use_container_width=True, on_click=_set_section, args=("統計",))
with col3:
    st.button("股票資料", use_container_width=True, on_click=_set_section, args=("股票",))

_, worksheet = get_sheet_context()

section = st.session_state["section"]

if section == "記帳":
    st.subheader("使用人")
    selected_user = st.radio("使用人", DEFAULT_USERS, horizontal=True, key="selected_user")

    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            expense_date = st.date_input("日期", value=date.today())
            amount = st.number_input("金額", min_value=0.0, step=1.0, format="%.0f")
        with col2:
            payment = st.selectbox("付款方式", DEFAULT_PAYMENTS)
            category = st.selectbox("分類", DEFAULT_CATEGORIES)
            note = st.text_input("備註")

        submitted = st.form_submit_button("新增紀錄")

    if submitted:
        row = [
            expense_date.strftime("%Y-%m-%d"),
            amount,
            category,
            payment,
            note.strip(),
            selected_user.strip(),
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

elif section == "統計":
    st.subheader("使用人")
    selected_user = st.radio("使用人", DEFAULT_USERS, horizontal=True, key="selected_user")

    st.subheader("統計")
    if "show_stats" not in st.session_state:
        st.session_state["show_stats"] = False
    if st.button("開始統計"):
        st.session_state["show_stats"] = True

    recent_df = fetch_recent(worksheet, limit=200)
    if st.session_state["show_stats"] and not recent_df.empty and "金額" in recent_df.columns:
        filtered = recent_df
        if "使用人" in recent_df.columns:
            filtered = recent_df[recent_df["使用人"] == selected_user]
        st.write(f"使用人：{selected_user}")
        if filtered.empty:
            st.info("此使用人目前沒有資料")
        else:
            summary_category = filtered.groupby("分類")["金額"].sum().reset_index()
            st.write("按分類")
            st.dataframe(summary_category, use_container_width=True)

else:
    st.subheader("股票資料")
    st.info("股票資料功能尚未啟用。如需接上現有股票程式，告訴我要顯示哪些內容。")
