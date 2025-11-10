import streamlit as st

def header(title, subtitle=None):
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)

def status_card(label, value, color="blue"):
    st.markdown(
        f"""
        <div style="
            padding:10px;
            border-radius:8px;
            background:#f7f7f9;
            border-left:6px solid {color};
            margin-bottom:8px;">
            <strong>{label}</strong><br>{value}
        </div>
        """,
        unsafe_allow_html=True,
    )
