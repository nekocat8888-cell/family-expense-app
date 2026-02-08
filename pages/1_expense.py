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

st.set_page_config(page_title="記帳", page_icon="🧾", layout="centered")

st.title("記帳")
st.caption("可多人使用，資料寫入 Google 試算表")

_, worksheet = get_sheet_context()

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
