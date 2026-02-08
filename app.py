from datetime import date

import streamlit as st

from utils import (
    DEFAULT_CATEGORIES,
    DEFAULT_PAYMENTS,
    DEFAULT_USERS,
    append_expense_row,
    fetch_recent,
    worksheet_to_df,
    get_sheet_context,
)

st.set_page_config(page_title="家庭記帳", page_icon="🧾", layout="centered")

st.title("家庭記帳")
st.caption("可多人使用，資料寫入 Google 試算表")

st.subheader("功能切換")
if "section" not in st.session_state:
    st.session_state["section"] = "記帳"
if "auth_ok" not in st.session_state:
    st.session_state["auth_ok"] = False


def _set_section(name: str):
    st.session_state["section"] = name


col1, col2, col3 = st.columns(3)
with col1:
    st.button("記帳", use_container_width=True, on_click=_set_section, args=("記帳",))
with col2:
    st.button("統計記帳結果", use_container_width=True, on_click=_set_section, args=("統計",))
with col3:
    st.button("股票資料", use_container_width=True, on_click=_set_section, args=("股票",))

spreadsheet, worksheet = get_sheet_context()

section = st.session_state["section"]
protected_sections = {"統計", "股票"}
password_required = section in protected_sections
password = st.secrets.get("app_password", "")

if password_required and not st.session_state["auth_ok"]:
    st.subheader("需要密碼")
    st.write("此功能需輸入密碼才能查看。")
    input_pwd = st.text_input("密碼", type="password")
    if st.button("解鎖"):
        if input_pwd and input_pwd == password:
            st.session_state["auth_ok"] = True
            st.success("已解鎖")
        else:
            st.error("密碼錯誤")
    st.stop()

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

    st.subheader("股票買賣紀錄")
    try:
        stock_ws = spreadsheet.worksheet("stock")
    except Exception:
        stock_ws = spreadsheet.add_worksheet(title="stock", rows=2000, cols=12)
        stock_ws.append_row(["代碼", "股數", "持有人", "金額", "時間", "買or賣", "備註"])

    with st.form("stock_trade_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.text_input("股票代碼", placeholder="例如：2330")
            shares = st.number_input("股數", min_value=0.0, step=1.0, format="%.0f")
        with col2:
            trade_type = st.selectbox("買or賣", ["買", "賣"])
            amount = st.number_input("金額", min_value=0.0, step=1.0, format="%.0f")
        with col3:
            trade_time = st.date_input("時間", value=date.today())
            holder = selected_user

        trade_note = st.text_input("備註", key="trade_note")
        trade_submit = st.form_submit_button("新增買賣紀錄")

    if trade_submit:
        if not symbol.strip():
            st.error("請輸入股票代碼")
        else:
            trade_row = [
                symbol.strip(),
                shares,
                holder.strip(),
                amount,
                trade_time.strftime("%Y-%m-%d"),
                trade_type,
                trade_note.strip(),
            ]
            stock_ws.append_row(trade_row, value_input_option="USER_ENTERED")
            st.success("已新增買賣紀錄")

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
    try:
        stock_ws = spreadsheet.worksheet("list")
    except Exception:
        stock_ws = None

    if stock_ws is None:
        st.info("找不到 list 分頁，請在 Google 試算表建立名為 list 的工作表。")
    else:
        stock_df = worksheet_to_df(stock_ws)
        if stock_df.empty:
            st.info("list 分頁目前沒有資料。")
        else:
            st.dataframe(stock_df, use_container_width=True)
