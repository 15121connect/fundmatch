"""
app.py — FundMatch landing page.
Run with: streamlit run app.py
"""

import streamlit as st
from pathlib import Path
from typing import Optional

from core.parser import parse, chunk, word_count
from core.embedder import load_model, encode_proposal
from core.matcher import load_funds, build_fund_index, match, summary_stats
from core.themes import extract_themes, theme_fund_breakdown

st.set_page_config(
    page_title="FundMatch",
    page_icon="⭐",                          # fix 1
    layout="centered",
    initial_sidebar_state="collapsed",
)

@st.cache_resource(show_spinner="Loading matching model…")
def get_model():
    try:
        return load_model()
    except Exception as e:
        st.error(f"❌ Model loading failed: {str(e)}.")
        st.stop()

@st.cache_resource(show_spinner="Indexing funds…")
def get_funds_and_index():
    try:
        funds = load_funds("data/funds.json")
        if not funds:
            st.warning("⚠️ No active funds loaded.")
            return [], None
        model = get_model()
        embeddings = build_fund_index(model, funds)
        return funds, embeddings
    except Exception as e:
        st.error(f"❌ Fund indexing failed: {str(e)}")
        st.stop()

SAMPLES = [
    {"label": "Community solar energy project — rural Ontario", "meta": "Clean energy · 2,400 words", "tag": "Energy",   "file": "data/samples/community_solar_ontario.txt"},
    {"label": "Affordable housing retrofit — Hamilton",          "meta": "Housing · 1,800 words",      "tag": "Housing",  "file": "data/samples/affordable_housing_hamilton.txt"},
    {"label": "Zero-emission fleet transition — City of Ottawa", "meta": "Transportation · 3,100 words","tag": "Transit",  "file": "data/samples/zero_emission_fleet_ottawa.txt"},
    {"label": "Indigenous food security program — Northern BC",  "meta": "Social · 2,100 words",       "tag": "Food",     "file": "data/samples/indigenous_food_security_bc.txt"},
]

st.markdown("""
<style>
  #MainMenu, footer, header { visibility: hidden; }

  /* ── fix 2: true vertical centering ────────────────────────────── */
  section[data-testid="stAppViewContainer"] > .main {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 100vh;
  }
  .block-container {
    max-width: 560px;
    margin-top: auto !important;
    margin-bottom: auto !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }

  /* ── Tabs: full-width, centred labels, green bottom border active ─ */
  div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: white;
    border-bottom: 0.5px solid #e5e7eb;
    gap: 0;
    padding: 0;
    width: 100%;
  }
  div[data-testid="stTabs"] [data-baseweb="tab"] {
    flex: 1 !important;
    justify-content: center !important;
    background: white !important;
    color: #6b7280 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    padding: 11px 8px !important;
    margin-bottom: -1px;
    border-radius: 0 !important;
  }
  div[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    color: #111827 !important;
    background: #f9fafb !important;
  }
  div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    color: #3B6D11 !important;
    border-bottom: 2px solid #3B6D11 !important;
    font-weight: 500 !important;
    background: white !important;
  }
  div[data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }
  div[data-testid="stTabs"] [data-baseweb="tab-border"]    { display: none !important; }
  div[data-testid="stTabs"] [data-testid="stTabContent"]   { padding-top: 1.25rem; }

  /* ── Explore button ─────────────────────────────────────────────── */
  div[data-testid="stButton"] > button:not(:disabled) {
    background: #3B6D11 !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important; font-size: 14px !important;
    font-weight: 500 !important; width: 100%;
  }
  div[data-testid="stButton"] > button:not(:disabled):hover { background: #27500A !important; }
  div[data-testid="stButton"] > button:disabled {
    background: #f3f4f6 !important; color: #9ca3af !important;
    border: none !important; border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important; font-size: 14px !important;
    font-weight: 500 !important; width: 100%; cursor: not-allowed !important;
  }

  /* ── Sample radio list ──────────────────────────────────────────── */
  div[data-testid="stRadio"] > div { gap: 6px; }
  div[data-testid="stRadio"] label {
    font-size: 13px; border: 0.5px solid #e5e7eb; border-radius: 8px;
    padding: 10px 12px; cursor: pointer;
    transition: border-color 0.1s, background 0.1s;
  }
  div[data-testid="stRadio"] label:hover { background: #f9fafb; border-color: #3B6D11; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align:center; margin-bottom:2rem;">
  <div style="display:flex; align-items:center; justify-content:center; gap:10px; margin-bottom:0.6rem;">
    <div style="background:#3B6D11; border-radius:7px; width:36px; height:36px;
                display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;">
      <svg viewBox="0 0 16 16" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 2L10 6.5H14.5L11 9.5L12.5 14L8 11L3.5 14L5 9.5L1.5 6.5H6L8 2Z"
              fill="white" stroke="white" stroke-width="0.5" stroke-linejoin="round"/>
      </svg>
    </div>
    <span style="font-size:2rem; font-weight:700; letter-spacing:-0.025em; line-height:1;">FundMatch</span>
  </div>
  <div style="font-size:0.875rem; color:#6b7280; line-height:1.65; max-width:380px; margin:0 auto;">
    Discover the right grants, loans, and rebates for your project — without the manual research.
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# fix 3: Input tabs — errors scoped per tab, no shared error_msg
# ---------------------------------------------------------------------------
proposal_text: Optional[str] = None

tab_upload, tab_paste, tab_sample = st.tabs(["Upload file", "Paste text", "Try a sample"])

with tab_upload:
    uploaded = st.file_uploader(
        "Drop your proposal here or browse",
        type=["pdf", "docx"], help="PDF or DOCX, maximum 5 MB",
        label_visibility="collapsed",
    )
    if uploaded:
        if uploaded.size > 5 * 1024 * 1024:
            st.error("❌ File exceeds 5 MB. Please upload a smaller document.")
        else:
            with st.spinner("Parsing document…"):
                try:
                    proposal_text = parse(uploaded.read(), uploaded.name)
                    st.caption(f"✓ {uploaded.name} — {word_count(proposal_text):,} words extracted")
                except ImportError as e:
                    st.error(f"❌ Parser error: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Could not parse file: {str(e)}")

with tab_paste:
    pasted = st.text_area(
        "Paste your proposal text", placeholder="Paste your proposal text here…",
        height=180, label_visibility="collapsed",
    )
    if pasted:
        if len(pasted) < 100:
            st.warning("Please paste at least 100 characters for accurate matching.")
        else:
            proposal_text = pasted
            st.caption(f"{len(pasted):,} characters · {word_count(pasted):,} words")

with tab_sample:
    chosen = st.radio(
        "Select a sample proposal:", options=[s["label"] for s in SAMPLES],
        index=None, label_visibility="collapsed",
    )
    if chosen is not None:
        s = next(x for x in SAMPLES if x["label"] == chosen)
        p = Path(s["file"])
        if p.exists():
            proposal_text = p.read_text()
            st.caption(f"✓ {s['meta']}")
        else:
            st.error(f"Sample file not found: {p}")

st.write("")
if st.button("Explore →", disabled=proposal_text is None, use_container_width=True):
    with st.spinner("Analysing your proposal…"):
        model = get_model()
        funds, fund_embeddings = get_funds_and_index()
        results = match(model, proposal_text, funds, fund_embeddings)
        stats   = summary_stats(results)
        themes  = extract_themes(proposal_text)
        for theme in themes:
            theme["breakdown"] = theme_fund_breakdown(theme["id"], results)
        st.session_state.update({
            "results": results, "stats": stats,
            "themes": themes, "proposal_text": proposal_text,
        })
    st.switch_page("pages/dashboard.py")