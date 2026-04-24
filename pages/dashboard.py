"""
pages/dashboard.py — FundMatch results dashboard.

Two-panel master-detail layout that displays matched funding
opportunities scored against a user's draft proposal. Features:
  • Eligibility verification via NLP keyword matching
  • Dynamic sorting (strength / deadline)
  • Theme extraction with strength-breakdown micro-charts
  • Custom HTML component with sessionStorage-based click handling
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from markupsafe import escape
from core.eligibility import verify_eligibility
from core.explanations import generate_match_reasons

st.set_page_config(
    page_title="FundMatch — Results",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------
if "results" not in st.session_state:
    st.warning("No results found. Please start from the home page.")
    if st.button("← Back to home"):
        st.switch_page("app.py")
    st.stop()

results       = st.session_state["results"]
stats         = st.session_state["stats"]
themes        = st.session_state["themes"]
proposal_text = st.session_state.get("proposal_text", "")

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
def default(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

default("show_all_results", False)
default("sort_by", "strength")
default("selected_fund_idx_visible", 0)

# ---------------------------------------------------------------------------
# Separate results by strength
# ---------------------------------------------------------------------------
strong_results   = [r for r in results if r["strength"] == "strong"]
moderate_results = [r for r in results if r["strength"] == "moderate"]
weak_results     = [r for r in results if r["strength"] == "weak"]

visible_results = strong_results + moderate_results
if st.session_state.show_all_results:
    visible_results = results

if st.session_state.sort_by == "deadline":
    visible_results = sorted(
        visible_results,
        key=lambda r: (r["days_remaining"] is None, r.get("days_remaining", 9999))
    )

n   = len(visible_results)
sel = min(st.session_state.selected_fund_idx_visible, n - 1) if n > 0 else 0
st.session_state.selected_fund_idx_visible = sel

# ---------------------------------------------------------------------------
# Colour maps & icons
# ---------------------------------------------------------------------------
STRENGTH_COLOURS = {"strong": "#639922", "moderate": "#BA7517", "weak": "#888780"}

ICON_BOLT = (
    '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle;">'
    '<path d="M9.5 1.5L4 9h4l-1.5 5.5L13 7H9l.5-5.5z" '
    'stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" '
    'stroke-linecap="round" fill="none"/></svg>'
)

ICON_TIMER = (
    '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle;">'
    '<circle cx="8" cy="9" r="5" stroke="currentColor" stroke-width="1.2" fill="none"/>'
    '<path d="M8 6.5V9l2 1.5" stroke="currentColor" stroke-width="1.2" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M6.5 2.5h3" stroke="currentColor" stroke-width="1.2" '
    'stroke-linecap="round"/></svg>'
)

# ---------------------------------------------------------------------------
# CSS (page-level only — component has its own styles)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1.5rem; max-width: 1200px; }

  .metric-tile { background:#f9fafb; border-radius:8px; padding:12px 16px; }
  .metric-label { font-size:11px; color:#6b7280; margin-bottom:4px; }
  .metric-value { font-size:22px; font-weight:500; }
  .metric-value.green { color:#3B6D11; }
  .metric-value.amber { color:#854F0B; }

  .section-heading { font-size:13px; font-weight:600; color:#111827; margin-bottom:10px; }

  .badge { display:inline-block; padding:2px 9px; border-radius:10px;
           font-size:11px; font-weight:500; white-space:nowrap; }
  .badge-urgent { background:#FCEBEB; color:#A32D2D; }
  .badge-soon   { background:#FAEEDA; color:#633806; }
  .badge-later  { background:#f3f4f6; color:#6b7280; border:0.5px solid #e5e7eb; }
  .badge-open   { background:#f3f4f6; color:#9ca3af; border:0.5px solid #e5e7eb;
                  font-style:italic; }

  .detail-card { background:white; border:0.5px solid #e5e7eb;
                 border-radius:12px; padding:18px; }
  .detail-title { font-size:15px; font-weight:500; margin-bottom:6px; }
  .detail-section-label {
    font-size:10px; font-weight:500; color:#9ca3af;
    text-transform:uppercase; letter-spacing:0.05em; margin:14px 0 5px;
  }

  .theme-pill {
    display:inline-flex; align-items:center; gap:8px;
    background:#f9fafb; border:0.5px solid #e5e7eb; border-radius:20px;
    padding:5px 10px 5px 8px; margin:3px;
  }
  .theme-count { font-size:11px; color:#6b7280; }

  .tag { display:inline-block; padding:2px 8px; border-radius:10px;
         font-size:10px; font-weight:500; margin:2px; }
  .tag-blue   { background:#E6F1FB; color:#185FA5; }
  .tag-teal   { background:#E1F5EE; color:#0F6E56; }
  .tag-purple { background:#EEEDFE; color:#3C3489; }

  button[data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    border: 0.5px solid #e5e7eb !important;
    border-radius: 6px !important;
    color: #6b7280 !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    padding: 5px 12px !important;
    box-shadow: none !important;
  }
  button[data-testid="stBaseButton-secondary"]:hover {
    color: #111827 !important; border-color:#d1d5db !important;
    background:#f9fafb !important;
  }         
  /* ── Hide relay buttons (offscreen but clickable by JS) ── */
  button[data-testid="stBaseButton-primary"] {
    position: fixed !important;
    left: -9999px !important;
    top: -9999px !important;
  }

  .fund-col-hdr { font-size: 11px; color: #6b7280; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Back button
# ---------------------------------------------------------------------------
if st.button("← New search", type="secondary"):
    st.switch_page("app.py")

# ---------------------------------------------------------------------------
# Proposal title
# ---------------------------------------------------------------------------
_words = proposal_text.strip().split()
if len(_words) <= 7:
    _proposal_title = " ".join(_words)
else:
    _proposal_title = " ".join(_words[:5]) + "…"

st.markdown(
    f'<div class="section-heading" style="margin-bottom:0.5rem;">'
    f'{escape(_proposal_title)}</div>',
    unsafe_allow_html=True,
)
st.write("")

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
st.markdown('<div class="section-heading">Summary</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns([1, 1, 2.5, 1.2])
with c1:
    st.markdown(
        f'<div class="metric-tile"><div class="metric-label">Strong matches</div>'
        f'<div class="metric-value green">{stats["strong_count"]}</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="metric-tile"><div class="metric-label">Total related funds</div>'
        f'<div class="metric-value">{stats["total_count"]}</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    tp = stats.get("type_split", {})
    g  = tp.get("grant", 0)
    rb = tp.get("rebate", 0)
    ln = tp.get("loan", 0)
    st.markdown(f"""<div class="metric-tile">
      <div class="metric-label">Fund type split</div>
      <div style="display:flex;height:10px;border-radius:5px;overflow:hidden;gap:2px;
           margin:8px 0 5px;">
        <div style="width:{g}%;background:#378ADD;border-radius:3px;"></div>
        <div style="width:{rb}%;background:#1D9E75;border-radius:3px;"></div>
        <div style="width:{ln}%;background:#7F77DD;border-radius:3px;"></div>
      </div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;">
        <span style="font-size:11px;color:#6b7280;display:flex;align-items:center;gap:4px;">
          <span style="width:8px;height:8px;background:#378ADD;border-radius:2px;
                display:inline-block;"></span>Grants {g}%</span>
        <span style="font-size:11px;color:#6b7280;display:flex;align-items:center;gap:4px;">
          <span style="width:8px;height:8px;background:#1D9E75;border-radius:2px;
                display:inline-block;"></span>Rebates {rb}%</span>
        <span style="font-size:11px;color:#6b7280;display:flex;align-items:center;gap:4px;">
          <span style="width:8px;height:8px;background:#7F77DD;border-radius:2px;
                display:inline-block;"></span>Loans {ln}%</span>
      </div></div>""", unsafe_allow_html=True)
with c4:
    st.markdown(
        f'<div class="metric-tile" style="background:#FAEEDA;">'
        f'<div class="metric-label" style="color:#633806;">Closing soon</div>'
        f'<div class="metric-value amber">{stats["closing_soon"]}</div>'
        f'<div style="font-size:11px;color:#854F0B;margin-top:2px;">funds in next 30 days</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.write("")

# ---------------------------------------------------------------------------
# Theme pills
# ---------------------------------------------------------------------------
if themes:
    st.markdown(
        "<div style='font-size:11px;font-weight:500;color:#9ca3af;letter-spacing:0.06em;"
        "text-transform:uppercase;margin-bottom:8px;'>"
        "Top themes in your draft vs. Funds matched</div>",
        unsafe_allow_html=True,
    )
    pills = ""
    for t in themes:
        bd    = t.get("breakdown", {})
        total = bd.get("total", 0)
        s     = bd.get("strong", 0)
        m     = bd.get("moderate", 0)
        sp    = round(s / total * 100) if total else 0
        mp    = round(m / total * 100) if total else 0
        wp    = 100 - sp - mp
        pills += (
            f'<span class="theme-pill">'
            f'<span style="font-size:13px;">{t["icon"]}</span>'
            f'<span style="font-size:12px;font-weight:500;">{escape(t["label"])}</span>'
            f'<span style="display:flex;height:6px;gap:1px;border-radius:3px;'
            f'overflow:hidden;width:48px;">'
            f'<span style="width:{sp}%;background:#639922;"></span>'
            f'<span style="width:{mp}%;background:#BA7517;"></span>'
            f'<span style="width:{wp}%;background:#B4B2A9;"></span></span>'
            f'<span class="theme-count">{total}</span></span>'
        )
    pills += (
        '<span style="display:inline-flex;align-items:center;gap:10px;margin-left:8px;'
        'vertical-align:middle;">'
        '<span style="font-size:10px;color:#9ca3af;display:flex;align-items:center;gap:4px;">'
        '<span style="width:8px;height:8px;background:#639922;border-radius:2px;'
        'display:inline-block;"></span>Strong</span>'
        '<span style="font-size:10px;color:#9ca3af;display:flex;align-items:center;gap:4px;">'
        '<span style="width:8px;height:8px;background:#BA7517;border-radius:2px;'
        'display:inline-block;"></span>Moderate</span>'
        '<span style="font-size:10px;color:#9ca3af;display:flex;align-items:center;gap:4px;">'
        '<span style="width:8px;height:8px;background:#B4B2A9;border-radius:2px;'
        'display:inline-block;"></span>Weak</span></span>'
    )
    st.markdown(pills, unsafe_allow_html=True)

st.markdown('<div style="height:2.4rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Two-panel layout
# ---------------------------------------------------------------------------
left, right = st.columns([1.05, 0.95], gap="medium")

# ===========================================================================
# LEFT — fund list as components.html
# ===========================================================================
with left:
    str_active = st.session_state.sort_by == "strength"
    dl_active  = st.session_state.sort_by == "deadline"
    str_cls    = "active" if str_active else "inactive"
    dl_cls     = "active" if dl_active  else "inactive"

    rows_html = ""
    for i, fund in enumerate(visible_results):
        colour   = STRENGTH_COLOURS[fund["strength"]]
        score    = fund.get("score_out_of_10", round(fund["score"] * 10))
        badge    = fund["deadline_badge"]
        dlabel   = fund["deadline_label"]
        is_sel   = (i == sel)
        row_cls  = "fund-row selected" if is_sel else "fund-row"
        name_col = "#3B6D11" if is_sel else "#111827"

        rows_html += f"""
        <div class="{row_cls}" onclick="selectFund({i})">
          <div style="min-width:0;padding-right:10px;">
            <div class="fund-name" style="color:{name_col};">
              {escape(fund['name'])}</div>
            <div class="fund-meta">
              {escape(fund['provider'])} · {escape(fund['type'].capitalize())}</div>
          </div>
          <div style="display:flex;align-items:center;gap:6px;padding-right:8px;">
            <div style="flex:1;height:4px;background:#e5e7eb;border-radius:2px;
                 overflow:hidden;min-width:30px;max-width:72px;">
              <div style="width:{score*10}%;height:100%;background:{colour};
                   border-radius:2px;"></div>
            </div>
            <span style="font-size:11px;font-weight:500;color:{colour};
                  min-width:18px;text-align:right;">{score}</span>
          </div>
          <div><span class="badge badge-{badge}">{escape(dlabel)}</span></div>
        </div>"""

    show_more_html = ""
    if weak_results and not st.session_state.show_all_results:
        show_more_html = f"""
        <div style="text-align:center;padding:12px;">
          <span onclick="doAction('show_more')" style="font-size:12px;color:#6b7280;
                cursor:pointer;border:0.5px solid #e5e7eb;border-radius:6px;
                padding:5px 12px;display:inline-block;transition:background 0.1s;">
            Show {len(weak_results)} more →</span>
        </div>"""

    component_height = max(n * 52 + 80, 200)
    if show_more_html:
        component_height += 50

    # The component writes to a hidden textarea in the PARENT frame,
    # which Streamlit can read as a text_input value
    component_html = f"""
    <html>
    <head>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
              "Helvetica Neue", Arial, sans-serif; background: transparent; }}

      .header {{
        display:flex; align-items:center; justify-content:space-between;
        margin-bottom:6px;
      }}
      .section-heading {{ font-size:13px; font-weight:600; color:#111827; }}
      .sort-wrap {{ display:flex; gap:6px; }}
      .sort-toggle {{
        display:inline-flex; align-items:center; justify-content:center;
        width:26px; height:26px; border-radius:6px; cursor:pointer;
        color:#6b7280; transition: background 0.1s;
      }}
      .sort-toggle.active {{ background:#f3f4f6; border:1px solid #9ca3af; }}
      .sort-toggle.inactive {{ background:#f9fafb; border:0.5px solid #e5e7eb; }}
      .sort-toggle:hover {{ background:#f3f4f6; }}

      .col-hdr {{
        display:grid; grid-template-columns:2fr 1.55fr 0.85fr;
        padding:4px 12px 6px; border-bottom:1px solid #e5e7eb;
      }}
      .col-hdr span {{ font-size:11px; color:#6b7280; font-weight:500; }}

      .fund-row {{
        display:grid; grid-template-columns:2fr 1.55fr 0.85fr;
        align-items:center; padding:10px 12px;
        border-bottom:0.5px solid #f3f4f6;
        cursor:pointer; border-left:3px solid transparent;
        transition: background 0.1s;
      }}
      .fund-row:hover {{ background:#f9fafb; }}
      .fund-row.selected {{
        background: #EAF3DE55; border-left:3px solid #3B6D11;
      }}
      .fund-name {{
        font-size:12px; font-weight:500; color:#111827;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
      }}
      .fund-meta {{ font-size:10px; color:#9ca3af; margin-top:2px; }}

      .badge {{
        display:inline-block; padding:2px 9px; border-radius:10px;
        font-size:11px; font-weight:500; white-space:nowrap;
      }}
      .badge-urgent {{ background:#FCEBEB; color:#A32D2D; }}
      .badge-soon   {{ background:#FAEEDA; color:#633806; }}
      .badge-later  {{ background:#f3f4f6; color:#6b7280; border:0.5px solid #e5e7eb; }}
      .badge-open   {{ background:#f3f4f6; color:#9ca3af; border:0.5px solid #e5e7eb;
                      font-style:italic; }}
    </style>
    </head>
    <body>
      <div class="header">
        <div class="section-heading">Details</div>
        <div class="sort-wrap">
          <div class="sort-toggle {str_cls}" onclick="doAction('sort_strength')">
            {ICON_BOLT}
          </div>
          <div class="sort-toggle {dl_cls}" onclick="doAction('sort_deadline')">
            {ICON_TIMER}
          </div>
        </div>
      </div>

      <div class="col-hdr">
        <span>Fund</span><span>Score</span><span>Deadline</span>
      </div>

      {rows_html}
      {show_more_html}

      <script>
        function findButtons() {{
          try {{
            return window.parent.document.querySelectorAll(
              'button[data-testid="stBaseButton-primary"]');
          }} catch(e) {{ return []; }}
        }}

        function clickButtonByKey(text) {{
          var buttons = findButtons();
          for (var i = 0; i < buttons.length; i++) {{
            if (buttons[i].innerText.trim() === text) {{
              buttons[i].click();
              return;
            }}
          }}
        }}

        function selectFund(idx) {{
          clickButtonByKey('sel' + idx);
        }}

        function doAction(action) {{
          if (action === 'sort_strength') clickButtonByKey('sort_strength');
          else if (action === 'sort_deadline') clickButtonByKey('sort_deadline');
          else if (action === 'show_more') clickButtonByKey('show_more');
        }}
      </script>
    </body>
    </html>"""

    components.html(component_html, height=component_height, scrolling=True)
    # Hidden buttons — one per fund, plus sort and show-more
    st.markdown('<div style="height:0;overflow:hidden;">', unsafe_allow_html=True)
    for i in range(n):
        if st.button(f"sel{i}", key=f"sel_{i}", type="primary"):
            st.session_state.selected_fund_idx_visible = i
            st.rerun()
    if st.button("sort_strength", key="act_sort_str", type="primary"):
        st.session_state.sort_by = "strength"
        st.rerun()
    if st.button("sort_deadline", key="act_sort_dl", type="primary"):
        st.session_state.sort_by = "deadline"
        st.rerun()
    if st.button("show_more", key="act_show_more", type="primary"):
        st.session_state.show_all_results = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ===========================================================================
# RIGHT — fund detail
# ===========================================================================
with right:
    fund = visible_results[sel] if n > 0 else None

    if fund is None:
        st.warning("No funds to display.")
    else:
        colour          = STRENGTH_COLOURS[fund["strength"]]
        score_out_of_10 = fund.get("score_out_of_10", round(fund["score"] * 10))
        badge           = fund["deadline_badge"]
        pill_label      = fund["deadline_label"]
        strength        = fund["strength"]

        tag_map  = {"grant": "tag-blue", "loan": "tag-purple", "rebate": "tag-teal"}
        type_tag = (f'<span class="tag {tag_map.get(fund["type"], "tag-blue")}">'
                    f'{escape(fund["type"].capitalize())}</span>')
        focus_tags = " ".join(
            f'<span class="tag tag-teal">{escape(fa)}</span>'
            for fa in fund.get("focus_areas", [])[:3]
        )

        lo, hi = fund.get("award_min"), fund.get("award_max")
        if lo and hi:
            range_str = f"${lo:,} – ${hi:,}"
        elif hi:
            range_str = f"Up to ${hi:,}"
        else:
            range_str = "Varies"

        deadline_raw = fund.get("deadline")
        if deadline_raw:
            try:
                dl = datetime.strptime(deadline_raw, "%Y-%m-%d")
                deadline_full = dl.strftime("%-d %b %Y")
            except ValueError:
                deadline_full = deadline_raw
            deadline_html = (
                f'<span style="font-size:12px;font-weight:500;color:#111827;'
                f'margin-right:8px;">{escape(deadline_full)}</span>'
                f'<span class="badge badge-{badge}">{escape(pill_label)}</span>'
            )
        else:
            deadline_html = '<span class="badge badge-open">Rolling</span>'

        eligibility_list = fund.get("eligibility", [])
        elig_html = ""
        if eligibility_list and proposal_text:
            for check in verify_eligibility(proposal_text, eligibility_list):
                icon = check["status"]
                crit = check["criterion"]
                if icon == "✓":
                    bg, fg = "#E1F5EE", "#0F6E56"
                elif icon == "✗":
                    bg, fg = "#FCEBEB", "#A32D2D"
                else:
                    bg, fg, icon = "#FAEEDA", "#854F0B", "?"
                badge_span = (
                    f'<span style="display:inline-flex;align-items:center;'
                    f'justify-content:center;width:15px;height:15px;border-radius:50%;'
                    f'background:{bg};font-size:9px;color:{fg};margin-right:6px;'
                    f'flex-shrink:0;">{icon}</span>'
                )
                elig_html += (
                    f'<div style="display:flex;align-items:center;font-size:11px;'
                    f'color:#4b5563;margin-bottom:5px;">'
                    f'{badge_span}{escape(crit)}</div>'
                )
        else:
            elig_html = "".join(
                f'<div style="font-size:11px;color:#4b5563;margin-bottom:4px;">'
                f'• {escape(e)}</div>'
                for e in eligibility_list
            )

        reasons = generate_match_reasons(
            proposal_text, fund, themes, fund.get("score", 0), strength
        )
        reasons_html = "".join(
            f'<div style="display:flex;align-items:flex-start;gap:7px;font-size:11px;'
            f'color:#4b5563;margin-bottom:5px;">'
            f'<span style="width:5px;height:5px;border-radius:50%;background:#3B6D11;'
            f'flex-shrink:0;margin-top:4px;"></span>'
            f'<span>{escape(r)}</span></div>'
            for r in reasons
        )

        contact_web   = fund.get("contact_web", "")
        contact_email = fund.get("contact_email", "")
        contact_parts = [p for p in [contact_web, contact_email] if p]
        contact_line  = (
            " | ".join(escape(p) for p in contact_parts)
            if contact_parts
            else "No contact info available"
        )

        boost_btn = """
        <div style="position:relative;display:inline-block;margin-top:4px;">
          <button onclick="return false;"
            title="Enhance your proposal with tailored intelligence"
            style="display:inline-flex;align-items:center;gap:7px;padding:8px 16px;
                   background:#f9fafb;border:0.5px solid #d1d5db;border-radius:8px;
                   font-size:12px;font-weight:500;color:#374151;cursor:default;
                   font-family:inherit;transition:background 0.15s;">
            <svg width="13" height="13" viewBox="0 0 14 14" fill="none"
                 xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;">
              <path d="M7 1l1.5 3.5L12 6l-3.5 1.5L7 11l-1.5-3.5L2 6l3.5-1.5L7 1z"
                    fill="#854F0B" stroke="#854F0B" stroke-width="0.3"
                    stroke-linejoin="round"/>
              <path d="M11.5 1.5l0.7 1.3 1.3 0.7-1.3 0.7-0.7 1.3-0.7-1.3-1.3-0.7
                       1.3-0.7z"
                    fill="#854F0B" stroke="#854F0B" stroke-width="0.2"/>
            </svg>
            Boost your odds
          </button>
          <span style="position:absolute;top:-7px;right:-7px;font-size:8px;
                       font-weight:500;background:#FAEEDA;color:#854F0B;
                       padding:1px 5px;border-radius:6px;border:0.5px solid #FBCF8A;
                       white-space:nowrap;">coming soon</span>
        </div>"""

        detail_html = f"""
        <div class="detail-card">
          <div class="detail-title">{escape(fund['name'])}</div>
          <div style="margin-bottom:10px;">{type_tag} {focus_tags}</div>

          <div class="detail-section-label">Score</div>
          <div style="font-size:18px;font-weight:500;color:{colour};margin-bottom:4px;">
            {score_out_of_10}/10 — {escape(strength.capitalize())} match
          </div>

          <div style="height:0.5px;background:#f3f4f6;margin:12px 0;"></div>

          <div class="detail-section-label">Award range</div>
          <div style="display:inline-block;background:#f9fafb;border:0.5px solid #e5e7eb;
               border-radius:8px;padding:4px 10px;font-size:12px;font-weight:500;
               margin-bottom:4px;">
            {range_str}
          </div>

          <div style="height:0.5px;background:#f3f4f6;margin:12px 0;"></div>

          <div class="detail-section-label">Why your draft matches</div>
          {reasons_html}

          <div style="height:0.5px;background:#f3f4f6;margin:12px 0;"></div>

          <div class="detail-section-label">Description</div>
          <div style="font-size:12px;color:#4b5563;line-height:1.6;margin-bottom:10px;">
            {escape(fund['description'])}</div>

          <div style="height:0.5px;background:#f3f4f6;margin:12px 0;"></div>

          <div class="detail-section-label">Eligibility check</div>
          {elig_html}

          <div style="height:0.5px;background:#f3f4f6;margin:12px 0;"></div>

          <div class="detail-section-label">Deadline</div>
          <div style="margin-top:4px;">{deadline_html}</div>

          <div style="height:0.5px;background:#f3f4f6;margin:12px 0;"></div>

          <div class="detail-section-label">Contact</div>
          <div style="font-size:11px;color:#185FA5;word-break:break-all;">
            {contact_line}</div>

          <div style="height:0.5px;background:#f3f4f6;margin:12px 0;"></div>

          {boost_btn}
        </div>"""

        st.markdown(detail_html, unsafe_allow_html=True)