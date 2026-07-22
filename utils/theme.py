"""ENA 가치+ 글로벌 테마 — 다크 네온 · Glassmorphism UI."""

COLORS = {
    "bg": "#070b14",
    "bg_alt": "#0d1424",
    "card": "rgba(255, 255, 255, 0.05)",
    "card_border": "rgba(255, 255, 255, 0.10)",
    "text": "#f8fafc",
    "text_muted": "#94a3b8",
    "magenta": "#ff2d95",
    "cyan": "#00d4ff",
    "purple": "#7c4dff",
    "blue": "#4facfe",
    "indigo": "#667eea",
    "accent_red": "#ff5370",
    "accent_blue": "#64b5f6",
}

GLOBAL_CSS = f"""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

:root {{
    --ena-bg: {COLORS["bg"]};
    --ena-bg-alt: {COLORS["bg_alt"]};
    --ena-card: {COLORS["card"]};
    --ena-card-border: {COLORS["card_border"]};
    --ena-text: {COLORS["text"]};
    --ena-text-muted: {COLORS["text_muted"]};
    --ena-magenta: {COLORS["magenta"]};
    --ena-cyan: {COLORS["cyan"]};
    --ena-purple: {COLORS["purple"]};
    --ena-radius: 18px;
    --ena-glow: 0 0 24px rgba(255, 45, 149, 0.18);
}}

html, body, .stApp {{
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
}}

.stApp {{
    background:
        radial-gradient(circle at 15% 20%, rgba(255, 45, 149, 0.12) 0%, transparent 28%),
        radial-gradient(circle at 85% 10%, rgba(0, 212, 255, 0.10) 0%, transparent 24%),
        radial-gradient(circle at 70% 80%, rgba(124, 77, 255, 0.10) 0%, transparent 30%),
        linear-gradient(180deg, #070b14 0%, #0d1424 100%);
    color: var(--ena-text);
}}

/* Material Icons: Pretendard 강제 시 keyboard_arrow_down 등이 텍스트로 겹쳐 보임 */
[data-testid="stIconMaterial"],
span[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
.material-icons {{
    font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
    font-style: normal !important;
    font-weight: normal !important;
    letter-spacing: normal !important;
    line-height: 1 !important;
}}

.main .block-container {{
    padding-top: 1rem;
    max-width: 1100px;
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, rgba(13,20,36,0.98) 0%, rgba(7,11,20,0.98) 100%);
    border-right: 1px solid rgba(255,255,255,0.08);
}}
[data-testid="stSidebar"] * {{
    color: #e2e8f0 !important;
}}
[data-testid="stSidebar"] .ena-sidebar-section {{
    color: {COLORS["text_muted"]} !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    margin: 0.85rem 0.15rem 0.45rem !important;
    padding-bottom: 0.35rem !important;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
}}
[data-testid="stSidebar"] .stButton {{
    margin-bottom: 0.35rem;
}}
[data-testid="stSidebar"] .stButton > button {{
    border-radius: 10px !important;
    padding: 0.72rem 0.95rem !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, rgba(255,45,149,0.45) 0%, rgba(124,77,255,0.35) 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,45,149,0.35) !important;
    border-left: 3px solid {COLORS["magenta"]} !important;
    box-shadow: 0 0 18px rgba(255, 45, 149, 0.22) !important;
}}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {{
    background: linear-gradient(135deg, rgba(0,212,255,0.12) 0%, rgba(124,77,255,0.10) 100%) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(0,212,255,0.22) !important;
    border-left: 3px solid {COLORS["cyan"]} !important;
    box-shadow: 0 0 12px rgba(0, 212, 255, 0.08) !important;
}}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {{
    background: linear-gradient(135deg, rgba(0,212,255,0.20) 0%, rgba(124,77,255,0.16) 100%) !important;
    border-color: rgba(0,212,255,0.35) !important;
    border-left-color: {COLORS["cyan"]} !important;
    color: #ffffff !important;
    box-shadow: 0 0 16px rgba(0, 212, 255, 0.16) !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.10);
}}
[data-testid="stSidebar"] .stCaption {{
    color: {COLORS["text_muted"]} !important;
    font-size: 0.72rem !important;
}}

h1, h2, h3, h4, p, label {{
    font-family: 'Pretendard', sans-serif !important;
}}
h1, h2, h3, h4 {{
    color: var(--ena-text) !important;
    font-weight: 700 !important;
}}

[data-testid="stMetric"] {{
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 1rem;
    border: 1px solid rgba(255,255,255,0.10);
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
    backdrop-filter: blur(12px);
}}
[data-testid="stMetric"] label {{
    color: var(--ena-text-muted) !important;
    font-size: 0.85rem !important;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: var(--ena-cyan) !important;
    font-weight: 700 !important;
}}

.stButton > button {{
    border-radius: 999px !important;
    font-weight: 600 !important;
    font-family: 'Pretendard', sans-serif !important;
    transition: all 0.2s ease !important;
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {COLORS["magenta"]} 0%, {COLORS["purple"]} 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 0 20px rgba(255, 45, 149, 0.35) !important;
}}
.stButton > button:not([kind="primary"]) {{
    background: rgba(255,255,255,0.04) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
}}

div[data-testid="stExpander"] {{
    background: rgba(255,255,255,0.04);
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.10);
    backdrop-filter: blur(10px);
}}

.stSelectbox > div > div,
.stMultiSelect > div > div,
.stTextInput > div > div > input,
.stFileUploader,
.stRadio {{
    background: rgba(255,255,255,0.04) !important;
    border-color: rgba(255,255,255,0.10) !important;
    color: #e2e8f0 !important;
}}
.stSelectbox [data-testid="stIconMaterial"],
.stMultiSelect [data-testid="stIconMaterial"],
.stFileUploader [data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
}}


[data-testid="stDataFrame"] {{
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    overflow: hidden;
}}

.stCaption, .stMarkdown small {{
    color: var(--ena-text-muted) !important;
}}
</style>
"""

CHART_LAYOUT = dict(
    font=dict(family="Pretendard, sans-serif", color="#e2e8f0"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=[COLORS["cyan"], COLORS["magenta"], COLORS["purple"], COLORS["blue"]],
    margin=dict(l=20, r=20, t=60, b=20),
)
