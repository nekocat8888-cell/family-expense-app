import streamlit as st

from utils import DEFAULT_USERS, fetch_recent, get_sheet_context

st.set_page_config(page_title="統計記帳結果", page_icon="📊", layout="centered")

st.title("統計記帳結果")
st.caption("依使用人顯示統計")

_, worksheet = get_sheet_context()

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
