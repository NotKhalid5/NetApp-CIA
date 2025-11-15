# frontend/app.py
# C.I.A. – Content Intelligence Analyzer | NetApp Hackathon Edition
# Streamlit Frontend — Clean Corporate UI + AI File Intelligence Dashboard (stable pagination + unique widget keys)

import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import hashlib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.file_classifier import classify_files_batch


# --- PAGE CONFIG ---
st.set_page_config(page_title="C.I.A. - Content Intelligence Analyzer", layout="wide")

# --- SESSION STATE ---
if "results" not in st.session_state:
    st.session_state.results = []
if "page_number" not in st.session_state:
    st.session_state.page_number = {}


# --- CUSTOM CSS ---
st.markdown("""
<style>
body {
    background-color: #0b0e17;
    color: #e3e6ed;
    font-family: 'Inter', sans-serif;
}
.sidebar .sidebar-content {
    background: linear-gradient(180deg, #171a24 0%, #0d0f17 100%);
    padding: 24px;
}
h1, h2, h3, h4 {
    color: #b9aaff !important;
    font-weight: 700;
}
.metric-card {
    background-color: #181c29;
    padding: 22px;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0px 0px 12px rgba(185,170,255,0.08);
}
.metric-value {
    font-size: 34px;
    color: #b9aaff;
    font-weight: 700;
}
.metric-label {
    font-size: 14px;
    color: #b0b3c1;
}
.stButton > button {
    background: linear-gradient(90deg, #4d3fff, #7d6aff);
    color: white;
    border-radius: 6px;
    border: none;
    font-weight: 600;
    box-shadow: 0 2px 6px rgba(125,106,255,0.4);
}
.stButton > button:hover {
    background: linear-gradient(90deg, #695aff, #8e7aff);
}
.sidebar-title {
    font-size: 18px;
    color: #b9aaff;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 20px;
}
.sidebar-section {
    color: #d1d5e0;
    font-size: 15px;
    margin-top: 18px;
}
hr {
    border: 0;
    border-top: 1px solid #2a2f40;
    margin: 18px 0;
}
.status-light {
    height: 10px;
    width: 10px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 8px;
    background-color: #4ade80;
    box-shadow: 0 0 6px rgba(74, 222, 128, 0.5);
}
.pagination {
    text-align: center;
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)


# --- SIDEBAR ---
st.sidebar.markdown('<div class="sidebar-title">C.I.A. Interface</div>', unsafe_allow_html=True)
page = st.sidebar.radio("", ["Dashboard", "File Analysis", "Quarantine"])

st.sidebar.markdown('<hr>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-section">System Status</div>', unsafe_allow_html=True)
st.sidebar.markdown("""
<small>
<span class="status-light"></span> Confidentiality: Stable<br>
<span class="status-light"></span> Integrity: Verified<br>
<span class="status-light"></span> Availability: Operational
</small>
""", unsafe_allow_html=True)
st.sidebar.markdown("<hr>", unsafe_allow_html=True)
st.sidebar.caption("NCAT Hackathon 2025 | Four Horse Men")


# --- FILE HANDLER ---
def handle_uploads(uploaded_files):
    os.makedirs("uploads", exist_ok=True)
    paths = []
    for f in uploaded_files:
        path = os.path.join("uploads", f.name)
        with open(path, "wb") as out:
            out.write(f.getbuffer())
        paths.append(path)

    st.info("Analyzing files with Magika AI... please wait ⏳")
    new_results = classify_files_batch(paths)
    st.session_state.results.extend(new_results)
    return new_results


# --- PAGINATION HELPER ---
def paginate_data(data, namespace: str, items_per_page=10):
    """Paginate datasets with unique keys for each context."""
    if namespace not in st.session_state.page_number:
        st.session_state.page_number[namespace] = 0

    total_pages = max(1, (len(data) + items_per_page - 1) // items_per_page)
    current_page = st.session_state.page_number[namespace]
    start_idx = current_page * items_per_page
    end_idx = start_idx + items_per_page
    paginated_data = data[start_idx:end_idx]

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"<div class='pagination'>Page {current_page + 1} of {total_pages}</div>",
            unsafe_allow_html=True
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("⬅ Previous", key=f"{namespace}_prev_{current_page}"):
                if st.session_state.page_number[namespace] > 0:
                    st.session_state.page_number[namespace] -= 1
                    st.rerun()
        with col_b:
            if st.button("Next ➡", key=f"{namespace}_next_{current_page}"):
                if st.session_state.page_number[namespace] < total_pages - 1:
                    st.session_state.page_number[namespace] += 1
                    st.rerun()
    return paginated_data


# --- DASHBOARD ---
if page == "Dashboard":
    st.markdown("<h1 style='text-align:center;'>C.I.A - Content Intelligence Analyzer</h1>", unsafe_allow_html=True)

    total = len(st.session_state.results)
    flagged = sum(1 for r in st.session_state.results if r.get("flagged"))
    safe = total - flagged

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="metric-card"><div class="metric-value">{total}</div><div class="metric-label">Total Files Scanned</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><div class="metric-value">{flagged}</div><div class="metric-label">Threats Quarantined</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><div class="metric-value">{safe}</div><div class="metric-label">Safe Files</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="metric-card"><div class="metric-value">{(flagged / total * 100 if total else 0):.1f}%</div><div class="metric-label">Threat Percentage</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Live File Feed")

    if total > 0:
        df = pd.DataFrame(st.session_state.results)
        df["AI Confidence"] = df["confidence"]
        df["Status"] = df["flagged"].map(lambda x: "Leak Risk" if x else "Safe")
        df = df.rename(columns={
            "file_name": "File Name",
            "language": "Language",
            "ai_category": "AI Category",
            "uploaded": "Timestamp"
        })
        paginated_df = paginate_data(df, "dashboard")
        st.dataframe(
            paginated_df[["File Name", "AI Category", "Language", "Status", "AI Confidence", "Timestamp"]],
            use_container_width=True
        )
    else:
        st.info("No data yet. Upload files in File Analysis to populate the dashboard.")


# --- FILE ANALYSIS ---
elif page == "File Analysis":
    st.markdown("<h1 style='text-align:center;'>File Analysis</h1>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload files for analysis", accept_multiple_files=True)

    if uploaded_files:
        new_results = handle_uploads(uploaded_files)
        st.success(f"{len(new_results)} files analyzed successfully.")

    flagged_files = [r for r in st.session_state.results if r.get("flagged")]
    safe_files = [r for r in st.session_state.results if not r.get("flagged")]

    if len(st.session_state.results) == 0:
        st.info("No files analyzed yet. Upload files to begin.")
    else:
        st.markdown("---")
        st.subheader("Flagged Files (Potential Data Leaks)")

        if not flagged_files:
            st.success("No leaks detected.")
        else:
            for r in paginate_data(flagged_files, "flagged"):
                unique_key = hashlib.md5(f"{r.get('file_name','')}_{r.get('uploaded','')}_flagged".encode()).hexdigest()
                with st.expander(f"{r.get('file_name', 'Unknown')} — Potential Leak"):
                    st.write(f"**AI Category:** {r.get('ai_category', 'Unknown')}")
                    st.write(f"**MIME Type:** {r.get('mime_type', 'Unknown')}")
                    st.write(f"**Encoding:** {r.get('encoding', 'N/A')}")
                    st.write(f"**Language:** {r.get('language', 'Unknown')}")
                    st.write(f"**Confidence:** {r.get('confidence', 'N/A')}")
                    st.write(f"**Detected PII Patterns:** {r.get('flag_reasons', [])}")
                    st.text_area(
                        f"Preview - {r.get('file_name', 'Unknown')}",
                        r.get("preview", "No preview available."),
                        height=180,
                        key=f"text_{unique_key}"
                    )

        st.markdown("---")
        st.subheader("Safe Files")

        for r in paginate_data(safe_files, "safe"):
            unique_key = hashlib.md5(f"{r.get('file_name','')}_{r.get('uploaded','')}_safe".encode()).hexdigest()
            with st.expander(f"{r.get('file_name', 'Unknown')} — Safe File"):
                st.write(f"**AI Category:** {r.get('ai_category', 'Unknown')}")
                st.write(f"**MIME Type:** {r.get('mime_type', 'Unknown')}")
                st.write(f"**Encoding:** {r.get('encoding', 'N/A')}")
                st.write(f"**Language:** {r.get('language', 'Unknown')}")
                st.write(f"**Confidence:** {r.get('confidence', 'N/A')}")
                st.text_area(
                    f"Preview - {r.get('file_name', 'Unknown')}",
                    r.get("preview", "No preview available."),
                    height=150,
                    key=f"text_{unique_key}"
                )


# --- QUARANTINE ---
elif page == "Quarantine":
    st.markdown("<h1 style='text-align:center;'>Quarantine</h1>", unsafe_allow_html=True)
    flagged_files = [r for r in st.session_state.results if r.get("flagged")]
    if not flagged_files:
        st.success("No files currently quarantined.")
    else:
        for r in paginate_data(flagged_files, "quarantine"):
            unique_key = hashlib.md5(f"{r.get('file_name','')}_{r.get('uploaded','')}_quarantine".encode()).hexdigest()
            with st.expander(f"{r.get('file_name', 'Unknown')} — Quarantined"):
                st.write(f"**Uploaded:** {r.get('uploaded', 'Unknown')}")
                st.write(f"**Language:** {r.get('language', 'Unknown')}")
                st.write(f"**AI Category:** {r.get('ai_category', 'Unknown')}")
                st.write(f"**Flag Reasons:** {', '.join(r.get('flag_reasons', [])) or 'unknown'}")
                st.text_area(
                    f"Preview - {r.get('file_name', 'Unknown')}",
                    r.get("preview", "No preview available."),
                    height=180,
                    key=f"text_{unique_key}"
                )
