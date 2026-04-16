import streamlit as st
import pandas as pd
import numpy as np
from itertools import combinations
import io
import math
import base64
import os

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="AltaPicks Tennis",
    page_icon="⛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# BRAND COLORS
# ============================================================
NAVY = "#1B3A6B"
DARK_BG = "#0D1117"
CARD_BG = "#161B22"
BORDER = "#21262D"
ACCENT = "#3B82F6"
ACCENT_DARK = "#1E40AF"
ACCENT_GLOW = "#60A5FA"
TEXT = "#E2E8F0"
TEXT_MUTED = "#8B949E"
TEXT_DIM = "#484F58"
SUCCESS = "#3B82F6"
DANGER = "#EF4444"
HIGHLIGHT_CELL = "#1E3A5F"

# ============================================================
# DK SCORING
# ============================================================
SCORING = {
    "match_played": 30, "game_won": 2.5, "game_lost": -2,
    "set_won": 6, "set_lost": -3, "match_won": 6,
    "ace": 0.4, "df": -1, "break": 0.75,
    "clean_set": 4, "straight_sets": 6, "no_df": 2.5, "ace_10plus": 2,
}

# ============================================================
# CSS
# ============================================================
def load_logo_b64():
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

LOGO_B64 = load_logo_b64()

st.markdown(f"""
<style>
    /* ── Base ───────────────────────────────── */
    .stApp {{ background-color: {DARK_BG}; }}
    section[data-testid="stSidebar"] {{ background-color: {CARD_BG}; border-right: 1px solid {BORDER}; }}
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {{ color: {TEXT}; }}

    /* ── Tabs ──────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0px;
        background: {CARD_BG};
        border-radius: 8px;
        padding: 4px;
        border: 1px solid {BORDER};
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 24px;
        border-radius: 6px;
        color: {TEXT_MUTED};
        font-weight: 500;
        font-size: 14px;
    }}
    .stTabs [aria-selected="true"] {{
        background: {NAVY} !important;
        color: white !important;
        font-weight: 600;
    }}

    /* ── Cards ─────────────────────────────── */
    .ap-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }}
    .ap-card-header {{
        font-size: 15px;
        font-weight: 600;
        color: {TEXT};
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .ap-card-accent {{
        border-left: 3px solid {ACCENT};
    }}

    /* ── Match Header ─────────────────────── */
    .match-bar {{
        background: linear-gradient(135deg, {NAVY} 0%, #234980 100%);
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 6px;
        font-weight: 600;
        font-size: 14px;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .match-bar .win-pct {{
        background: rgba(255,255,255,0.15);
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 13px;
    }}

    /* ── Lineup Cards ─────────────────────── */
    .lineup-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 8px;
        font-size: 13px;
    }}
    .lineup-card .lu-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        padding-bottom: 6px;
        border-bottom: 1px solid {BORDER};
        font-weight: 600;
        color: {TEXT};
    }}
    .lineup-card .lu-proj {{
        color: {ACCENT_GLOW};
        font-size: 14px;
    }}
    .lineup-card .lu-row {{
        display: flex;
        justify-content: space-between;
        padding: 3px 0;
        color: {TEXT_MUTED};
        font-size: 12px;
    }}
    .lineup-card .lu-row .lu-name {{
        color: {TEXT};
        font-weight: 500;
        flex: 1;
    }}
    .lineup-card .lu-row .lu-opp {{
        color: {TEXT_DIM};
        flex: 1;
        text-align: left;
    }}
    .lineup-card .lu-row .lu-sal {{
        width: 55px;
        text-align: right;
    }}
    .lineup-card .lu-row .lu-pts {{
        width: 45px;
        text-align: right;
        color: {ACCENT_GLOW};
    }}
    .lineup-card .lu-footer {{
        display: flex;
        justify-content: space-between;
        margin-top: 6px;
        padding-top: 6px;
        border-top: 1px solid {BORDER};
        font-weight: 600;
        font-size: 12px;
        color: {TEXT};
    }}

    /* ── Projection Table ─────────────────── */
    .proj-highlight {{
        background: {HIGHLIGHT_CELL};
        color: {ACCENT_GLOW};
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        display: inline-block;
        min-width: 50px;
        text-align: center;
    }}

    /* ── Metric Overrides ─────────────────── */
    div[data-testid="stMetric"] {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 14px 16px;
    }}
    div[data-testid="stMetric"] label {{ color: {TEXT_MUTED} !important; font-size: 12px !important; }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{ color: {ACCENT_GLOW} !important; }}

    /* ── Buttons ───────────────────────────── */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {NAVY} 0%, {ACCENT_DARK} 100%) !important;
        border: none !important;
        font-weight: 600 !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, {ACCENT_DARK} 0%, {ACCENT} 100%) !important;
    }}
    .stDownloadButton > button {{
        background: {CARD_BG} !important;
        border: 1px solid {ACCENT} !important;
        color: {ACCENT_GLOW} !important;
        font-weight: 500 !important;
    }}
    .stDownloadButton > button:hover {{
        background: {NAVY} !important;
        color: white !important;
    }}

    /* ── Inputs ────────────────────────────── */
    .stNumberInput > div > div > input {{
        background: {DARK_BG} !important;
        border: 1px solid {BORDER} !important;
        color: {TEXT} !important;
        font-size: 13px !important;
    }}
    .stSelectbox > div > div {{ background: {DARK_BG} !important; }}

    /* ── Expander ──────────────────────────── */
    .streamlit-expanderHeader {{
        background: {CARD_BG} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }}

    /* ── Dataframe ─────────────────────────── */
    .stDataFrame {{ border-radius: 8px; overflow: hidden; }}

    /* ── Logo ──────────────────────────────── */
    .sidebar-logo {{
        text-align: center;
        padding: 16px 0 8px 0;
    }}
    .sidebar-logo img {{
        width: 120px;
        opacity: 0.95;
    }}
    .sidebar-brand {{
        text-align: center;
        font-size: 11px;
        color: {TEXT_DIM};
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-top: 4px;
        margin-bottom: 16px;
    }}

    /* ── Section Headers ──────────────────── */
    .section-header {{
        font-size: 20px;
        font-weight: 700;
        color: {TEXT};
        margin-bottom: 4px;
    }}
    .section-sub {{
        font-size: 13px;
        color: {TEXT_MUTED};
        margin-bottom: 16px;
    }}

    /* ── Hide Streamlit branding ───────────── */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPERS
# ============================================================
def american_to_prob(odds):
    if odds is None or odds == 0: return 0.5
    if odds > 0: return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)

def remove_vig_pair(p1, p2):
    total = p1 + p2
    if total == 0: return 0.5, 0.5
    return p1 / total, p2 / total

def poisson_ev_from_milestone(odds, milestone):
    p = american_to_prob(odds)
    if p <= 0 or p >= 1: return milestone
    lam = milestone
    for _ in range(50):
        cdf = sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(milestone))
        target = 1 - p
        if abs(cdf - target) < 0.001: break
        dcdf = sum(math.exp(-lam) * (i * lam**(i-1) / math.factorial(i) - lam**i / math.factorial(i))
                    for i in range(milestone))
        if abs(dcdf) < 1e-10: break
        lam -= (cdf - target) / dcdf
        lam = max(0.1, min(lam, 30))
    return lam

def parse_dk_csv(uploaded_file):
    content = uploaded_file.read().decode('utf-8')
    lines = content.strip().split('\n')
    players = []
    for line in lines:
        parts = line.split(',')
        if len(parts) >= 16:
            try:
                name = parts[9].strip()
                player_id = parts[10].strip()
                salary = int(parts[12].strip())
                game_info = parts[13].strip()
                avg_ppg = float(parts[15].strip()) if parts[15].strip() else 0
                if name and player_id.isdigit() and salary > 0:
                    match_str = game_info.split(' ')[0] if game_info else ''
                    players.append({
                        'name': name, 'id': int(player_id), 'salary': salary,
                        'game_info': game_info, 'match_str': match_str, 'avg_ppg': avg_ppg,
                    })
            except (ValueError, IndexError):
                continue
    return players

def detect_matches(players):
    match_map = {}
    for p in players:
        key = p['match_str']
        if key not in match_map: match_map[key] = []
        match_map[key].append(p['name'])
    matches = []
    for key, names in match_map.items():
        if len(names) == 2:
            matches.append({'key': key, 'player_a': names[0], 'player_b': names[1]})
    return matches

def build_projection(odds, scoring=SCORING):
    wp = odds.get('win_prob', 0.5)
    games_won = odds.get('games_won', 10)
    games_lost = odds.get('games_lost', 10)
    p_straight_win = odds.get('p_straight_win', wp * 0.6)
    p_straight_loss = odds.get('p_straight_loss', (1 - wp) * 0.6)
    p_win_3 = wp - p_straight_win
    p_lose_3 = (1 - wp) - p_straight_loss
    p_3set = 1 - p_straight_win - p_straight_loss
    e_sets_played = 2 * (1 - p_3set) + 3 * p_3set
    e_sets_won = 2 * p_straight_win + 2 * p_win_3 + 1 * p_lose_3
    e_sets_lost = e_sets_played - e_sets_won
    aces = odds.get('aces', 3)
    p_10plus_aces = odds.get('p_10plus_aces', 0)
    dfs = odds.get('dfs', 3)
    p_no_df = odds.get('p_no_df', math.exp(-dfs))
    breaks = odds.get('breaks', wp * 3 + (1 - wp) * 1.5)
    clean_rate = odds.get('clean_set_rate', 0.05 + 0.15 * wp)
    e_clean_sets = e_sets_won * clean_rate
    adj = odds.get('adjustment', 0)
    score = (
        scoring["match_played"] + scoring["match_won"] * wp
        + scoring["set_won"] * e_sets_won + scoring["set_lost"] * e_sets_lost
        + scoring["game_won"] * games_won + scoring["game_lost"] * games_lost
        + scoring["ace"] * aces + scoring["df"] * dfs + scoring["break"] * breaks
        + scoring["straight_sets"] * p_straight_win + scoring["clean_set"] * e_clean_sets
        + scoring["no_df"] * p_no_df + scoring["ace_10plus"] * p_10plus_aces + adj
    )
    return {
        'score': round(score, 2), 'wp': round(wp, 3),
        'games_won': round(games_won, 2), 'games_lost': round(games_lost, 2),
        'sets_won': round(e_sets_won, 3), 'sets_lost': round(e_sets_lost, 3),
        'sets_played': round(e_sets_played, 3),
        'aces': round(aces, 2), 'dfs': round(dfs, 2), 'breaks': round(breaks, 2),
        'p_straight': round(p_straight_win, 3), 'p_3set': round(p_3set, 3),
        'p_no_df': round(p_no_df, 4), 'p_10plus_aces': round(p_10plus_aces, 3),
        'clean_sets': round(e_clean_sets, 3),
    }

def run_optimizer(players_data, n_lineups=45, salary_cap=50000, lineup_size=6):
    idx_map = {p['name']: i for i, p in enumerate(players_data)}
    seen = set(); matches = []
    for p in players_data:
        if p['name'] in seen: continue
        opp = p['opponent']
        if opp in idx_map:
            matches.append((p['name'], opp)); seen.add(p['name']); seen.add(opp)
    match_options = []
    for a, b in matches:
        pa, pb = players_data[idx_map[a]], players_data[idx_map[b]]
        match_options.append([(idx_map[a], pa['salary'], pa['projection']),
                              (idx_map[b], pb['salary'], pb['projection'])])
    all_lineups = []
    for mc in combinations(range(len(match_options)), lineup_size):
        for bits in range(2**lineup_size):
            ts=0; tp=0.0; pidxs=[]
            for i, mi in enumerate(mc):
                side = (bits >> i) & 1
                pid, sal, proj = match_options[mi][side]
                ts += sal; tp += proj; pidxs.append(pid)
            if ts <= salary_cap:
                all_lineups.append((round(tp,2), ts, tuple(pidxs)))
    all_lineups.sort(key=lambda x: -x[0])

    max_caps, min_caps = {}, {}
    for p in players_data:
        if p.get('max_exposure') is not None:
            max_caps[p['name']] = max(1, int(round(n_lineups * p['max_exposure'] / 100)))
        if p.get('min_exposure') is not None and p['min_exposure'] > 0:
            min_caps[p['name']] = max(1, int(round(n_lineups * p['min_exposure'] / 100)))
    default_cap = int(n_lineups * 0.60)
    match_caps_dict = {}
    for a, b in matches:
        pa, pb = players_data[idx_map[a]], players_data[idx_map[b]]
        mc = pa.get('match_max_exposure')
        if mc is not None:
            match_caps_dict[frozenset({a, b})] = max(1, int(round(n_lineups * mc / 100)))

    selected = []; selected_keys = set()
    player_counts = [0] * len(players_data)
    match_counts = {mc: 0 for mc in match_caps_dict}

    def can_add(pidxs):
        for pid in pidxs:
            nm = players_data[pid]['name']
            if player_counts[pid] + 1 > max_caps.get(nm, default_cap): return False
        for mc_key, mc_cap in match_caps_dict.items():
            hit = sum(1 for pid in pidxs if players_data[pid]['name'] in mc_key)
            if match_counts[mc_key] + hit > mc_cap: return False
        return True

    def add_lu(proj, sal, pidxs):
        selected.append((proj, sal, pidxs)); selected_keys.add(pidxs)
        for pid in pidxs: player_counts[pid] += 1
        for mc_key in match_caps_dict:
            match_counts[mc_key] += sum(1 for pid in pidxs if players_data[pid]['name'] in mc_key)

    # Phase 1a: Scarcity
    scarcity = sorted(min_caps.items(), key=lambda x: x[1])
    for name, _ in scarcity:
        ti = idx_map[name]
        while player_counts[ti] < min_caps[name] and len(selected) < n_lineups:
            placed = False
            for proj, sal, pidxs in all_lineups:
                if pidxs in selected_keys or ti not in pidxs: continue
                if can_add(pidxs): add_lu(proj, sal, pidxs); placed = True; break
            if not placed: break

    # Phase 1b: Round-robin
    for _ in range(500):
        if len(selected) >= n_lineups: break
        deficits = [(n, min_caps[n] - player_counts[idx_map[n]]) for n in min_caps if player_counts[idx_map[n]] < min_caps[n]]
        if not deficits: break
        deficits.sort(key=lambda x: (-x[1], player_counts[idx_map[x[0]]]))
        tn = deficits[0][0]; ti = idx_map[tn]; picked = False
        for proj, sal, pidxs in all_lineups:
            if pidxs in selected_keys or ti not in pidxs: continue
            if can_add(pidxs): add_lu(proj, sal, pidxs); picked = True; break
        if not picked: min_caps[tn] = player_counts[ti]

    # Phase 2: Greedy
    for proj, sal, pidxs in all_lineups:
        if len(selected) >= n_lineups: break
        if pidxs in selected_keys or not can_add(pidxs): continue
        add_lu(proj, sal, pidxs)

    # Post-pass swaps
    def min_ok(rm, ad, exc):
        for o, om in min_caps.items():
            if o == exc: continue
            oid = idx_map[o]
            ch = (-1 if oid in rm else 0) + (1 if oid in ad else 0)
            nc = player_counts[oid] + ch
            if player_counts[oid] >= om and nc < om: return False
            if player_counts[oid] < om and ch < 0: return False
        return True

    def swap_ok(rm, ad):
        nc = list(player_counts)
        for pid in rm: nc[pid] -= 1
        for pid in ad: nc[pid] += 1
        for pid in range(len(players_data)):
            if nc[pid] > max_caps.get(players_data[pid]['name'], default_cap): return False
        nmc = dict(match_counts)
        for mk in match_caps_dict:
            for pid in rm:
                if players_data[pid]['name'] in mk: nmc[mk] -= 1
            for pid in ad:
                if players_data[pid]['name'] in mk: nmc[mk] += 1
            if nmc[mk] > match_caps_dict[mk]: return False
        return True

    for _ in range(200):
        defs = [(n, min_caps[n] - player_counts[idx_map[n]]) for n in min_caps if player_counts[idx_map[n]] < min_caps[n]]
        if not defs: break
        defs.sort(key=lambda x: -x[1]); nm = defs[0][0]; ti = idx_map[nm]; done = False
        for cp, cs, cpx in all_lineups:
            if cpx in selected_keys or ti not in cpx: continue
            selected.sort(key=lambda x: x[0])
            for i, (sp, ss, spx) in enumerate(selected):
                if ti in spx: continue
                if not min_ok(spx, cpx, nm) or not swap_ok(spx, cpx): continue
                selected_keys.discard(spx)
                for pid in spx: player_counts[pid] -= 1
                for mk in match_caps_dict:
                    match_counts[mk] -= sum(1 for pid in spx if players_data[pid]['name'] in mk)
                selected[i] = (cp, cs, cpx); selected_keys.add(cpx)
                for pid in cpx: player_counts[pid] += 1
                for mk in match_caps_dict:
                    match_counts[mk] += sum(1 for pid in cpx if players_data[pid]['name'] in mk)
                done = True; break
            if done: break
        if not done: min_caps[nm] = player_counts[idx_map[nm]]

    selected.sort(key=lambda x: -x[0])
    return selected, player_counts, all_lineups

# ============================================================
# SESSION STATE
# ============================================================
for key in ['players', 'matches', 'odds_data', 'projections', 'exposure_settings']:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ['players', 'matches'] else {}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    if LOGO_B64:
        st.markdown(f'<div class="sidebar-logo"><img src="data:image/png;base64,{LOGO_B64}"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-brand">Tennis Optimizer</div>', unsafe_allow_html=True)
    else:
        st.markdown("# ⛰️ AltaPicks")
        st.caption("Tennis Optimizer")

    st.markdown("---")
    uploaded_file = st.file_uploader("DraftKings Salary CSV", type=['csv'], label_visibility="collapsed")
    if uploaded_file:
        players = parse_dk_csv(uploaded_file)
        if players:
            st.session_state.players = players
            st.session_state.matches = detect_matches(players)
            st.success(f"{len(players)} players · {len(st.session_state.matches)} matches")

    st.markdown("---")
    st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Build Settings</div>', unsafe_allow_html=True)
    n_lineups = st.number_input("Lineups", min_value=1, max_value=150, value=45)
    salary_cap = st.number_input("Salary Cap", min_value=10000, max_value=100000, value=50000, step=1000)
    lineup_size = st.number_input("Roster Size", min_value=2, max_value=8, value=6)

    st.markdown("---")
    st.markdown(f"""<div style="background:{NAVY};padding:10px 12px;border-radius:8px;font-size:11px;color:{TEXT_MUTED};line-height:1.6;">
    <span style="color:white;font-weight:600;">DK Scoring</span><br>
    Match +30 · Win +6 · Set W/L +6/-3<br>
    Game W/L +2.5/-2 · Ace +0.4 · DF -1<br>
    Break +0.75 · Straights +6<br>
    Clean Set +4 · No DF +2.5 · 10+ Aces +2
    </div>""", unsafe_allow_html=True)

# ============================================================
# MAIN
# ============================================================
if not st.session_state.players:
    st.markdown(f"""
    <div style="text-align:center;padding:80px 20px;">
        {'<img src="data:image/png;base64,' + LOGO_B64 + '" width="180" style="margin-bottom:24px;opacity:0.8;">' if LOGO_B64 else ''}
        <h1 style="color:{TEXT};font-size:32px;margin-bottom:8px;">AltaPicks Tennis Optimizer</h1>
        <p style="color:{TEXT_MUTED};font-size:16px;max-width:500px;margin:0 auto 32px;">
            Upload your DraftKings salary CSV to start building lineups.
        </p>
        <div style="display:flex;gap:20px;justify-content:center;flex-wrap:wrap;max-width:700px;margin:0 auto;">
            <div class="ap-card" style="flex:1;min-width:140px;text-align:center;">
                <div style="font-size:24px;margin-bottom:4px;">📊</div>
                <div style="color:{TEXT};font-weight:600;font-size:13px;">Input Odds</div>
                <div style="color:{TEXT_DIM};font-size:11px;margin-top:2px;">Bet365, DK Sportsbook</div>
            </div>
            <div class="ap-card" style="flex:1;min-width:140px;text-align:center;">
                <div style="font-size:24px;margin-bottom:4px;">⚡</div>
                <div style="color:{TEXT};font-weight:600;font-size:13px;">Projections</div>
                <div style="color:{TEXT_DIM};font-size:11px;margin-top:2px;">Full DK scoring model</div>
            </div>
            <div class="ap-card" style="flex:1;min-width:140px;text-align:center;">
                <div style="font-size:24px;margin-bottom:4px;">🎯</div>
                <div style="color:{TEXT};font-weight:600;font-size:13px;">Optimize</div>
                <div style="color:{TEXT_DIM};font-size:11px;margin-top:2px;">Exposure-capped lineups</div>
            </div>
            <div class="ap-card" style="flex:1;min-width:140px;text-align:center;">
                <div style="font-size:24px;margin-bottom:4px;">📥</div>
                <div style="color:{TEXT};font-weight:600;font-size:13px;">Export</div>
                <div style="color:{TEXT_DIM};font-size:11px;margin-top:2px;">DK-ready upload CSV</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["  Odds Input  ", "  Projections  ", "  Lineup Builder  ", "  Export  "])

# ============================================================
# TAB 1: ODDS INPUT
# ============================================================
with tab1:
    st.markdown('<div class="section-header">Match Odds</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Enter sportsbook odds for each match · American format (-150, +275)</div>', unsafe_allow_html=True)

    for mi, match in enumerate(st.session_state.matches):
        pa_name, pb_name = match['player_a'], match['player_b']
        match_key = f"{pa_name}_vs_{pb_name}"
        if match_key not in st.session_state.odds_data:
            st.session_state.odds_data[match_key] = {}

        with st.expander(f"🎾  {pa_name}  vs  {pb_name}", expanded=(mi < 2)):
            # Money Line
            c1, c2, c3, c4 = st.columns([2,1,2,1])
            with c1: st.markdown(f"**{pa_name}**")
            with c2: ml_a = st.number_input("ML", key=f"ml_a_{mi}", value=-200, step=5, label_visibility="collapsed")
            with c3: st.markdown(f"**{pb_name}**")
            with c4: ml_b = st.number_input("ML", key=f"ml_b_{mi}", value=160, step=5, label_visibility="collapsed")

            raw_a, raw_b = american_to_prob(ml_a), american_to_prob(ml_b)
            wp_a, wp_b = remove_vig_pair(raw_a, raw_b)

            st.markdown(f"""<div class="match-bar">
                <span>{pa_name}</span>
                <span class="win-pct">{wp_a:.0%} – {wp_b:.0%}</span>
                <span>{pb_name}</span>
            </div>""", unsafe_allow_html=True)

            # Set Betting + Total Games
            st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;margin:8px 0 4px;">SET BETTING</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            with c1: sb_a_20 = st.number_input(f"{pa_name} 2-0", key=f"sb_a20_{mi}", value=-120, step=5)
            with c2: sb_a_21 = st.number_input(f"{pa_name} 2-1", key=f"sb_a21_{mi}", value=240, step=5)
            with c3: sb_b_20 = st.number_input(f"{pb_name} 2-0", key=f"sb_b20_{mi}", value=600, step=5)
            with c4: sb_b_21 = st.number_input(f"{pb_name} 2-1", key=f"sb_b21_{mi}", value=550, step=5)

            rp = [american_to_prob(x) for x in [sb_a_20, sb_a_21, sb_b_20, sb_b_21]]
            tr = sum(rp)
            p_a20, p_a21, p_b20, p_b21 = [p/tr for p in rp] if tr > 0 else [.4,.2,.1,.1]

            # Games Won
            st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;margin:8px 0 4px;">PLAYER GAMES WON</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            with c1: gw_a_line = st.number_input(f"{pa_name} line", key=f"gw_a_{mi}", value=12.5, step=0.5)
            with c2: gw_a_over = st.number_input(f"Over odds", key=f"gw_ao_{mi}", value=-150, step=5)
            with c3: gw_b_line = st.number_input(f"{pb_name} line", key=f"gw_b_{mi}", value=10.5, step=0.5)
            with c4: gw_b_over = st.number_input(f"Over odds", key=f"gw_bo_{mi}", value=-120, step=5)

            gw_a = gw_a_line + (0.5 if american_to_prob(gw_a_over) > 0.55 else -0.3 if american_to_prob(gw_a_over) < 0.45 else 0)
            gw_b = gw_b_line + (0.5 if american_to_prob(gw_b_over) > 0.55 else -0.3 if american_to_prob(gw_b_over) < 0.45 else 0)

            # Breaks
            st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;margin:8px 0 4px;">BREAKS OF SERVE</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            with c1: brk_a_line = st.number_input(f"{pa_name} line", key=f"brk_a_{mi}", value=2.5, step=0.5)
            with c2: brk_a_over = st.number_input(f"Over", key=f"brk_ao_{mi}", value=-200, step=5)
            with c3: brk_b_line = st.number_input(f"{pb_name} line", key=f"brk_b_{mi}", value=1.5, step=0.5)
            with c4: brk_b_over = st.number_input(f"Over", key=f"brk_bo_{mi}", value=-120, step=5)

            brk_a = brk_a_line + (0.5 if american_to_prob(brk_a_over) > 0.6 else 0)
            brk_b = brk_b_line + (0.2 if american_to_prob(brk_b_over) > 0.55 else 0)

            # Aces & DFs
            st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;margin:8px 0 4px;">ACES & DOUBLE FAULTS</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            with c1: ace_a5 = st.number_input(f"{pa_name} 5+ Aces", key=f"ace_a5_{mi}", value=-200, step=5)
            with c2: ace_a10 = st.number_input(f"{pa_name} 10+ Aces", key=f"ace_a10_{mi}", value=400, step=5)
            with c3: ace_b5 = st.number_input(f"{pb_name} 5+ Aces", key=f"ace_b5_{mi}", value=-225, step=5)
            with c4: ace_b10 = st.number_input(f"{pb_name} 10+ Aces", key=f"ace_b10_{mi}", value=333, step=5)

            c1, c2, c3, c4 = st.columns(4)
            with c1: df_a2 = st.number_input(f"{pa_name} 2+ DFs", key=f"df_a2_{mi}", value=-275, step=5)
            with c2: df_a3 = st.number_input(f"{pa_name} 3+ DFs", key=f"df_a3_{mi}", value=100, step=5)
            with c3: df_b2 = st.number_input(f"{pb_name} 2+ DFs", key=f"df_b2_{mi}", value=100, step=5)
            with c4: df_b3 = st.number_input(f"{pb_name} 3+ DFs", key=f"df_b3_{mi}", value=300, step=5)

            ace_a_ev = poisson_ev_from_milestone(ace_a5, 5)
            ace_b_ev = poisson_ev_from_milestone(ace_b5, 5)
            df_a_ev = poisson_ev_from_milestone(df_a3, 3)
            df_b_ev = poisson_ev_from_milestone(df_b3, 3)
            p_nodf_a = max(0, 1 - american_to_prob(df_a2)) if american_to_prob(df_a2) < 0.95 else math.exp(-df_a_ev)
            p_nodf_b = max(0, 1 - american_to_prob(df_b2)) if american_to_prob(df_b2) < 0.95 else math.exp(-df_b_ev)

            # Adjustment
            st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;margin:8px 0 4px;">YOUR READ (±)</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: adj_a = st.number_input(f"{pa_name}", key=f"adj_a_{mi}", value=0.0, step=0.5, label_visibility="collapsed")
            with c2: adj_b = st.number_input(f"{pb_name}", key=f"adj_b_{mi}", value=0.0, step=0.5, label_visibility="collapsed")

            st.session_state.odds_data[match_key] = {
                'player_a': {
                    'name': pa_name, 'win_prob': wp_a,
                    'p_straight_win': p_a20, 'p_straight_loss': p_b20,
                    'games_won': gw_a, 'games_lost': gw_b,
                    'aces': ace_a_ev, 'dfs': df_a_ev, 'breaks': brk_a,
                    'p_10plus_aces': american_to_prob(ace_a10), 'p_no_df': p_nodf_a,
                    'adjustment': adj_a,
                },
                'player_b': {
                    'name': pb_name, 'win_prob': wp_b,
                    'p_straight_win': p_b20, 'p_straight_loss': p_a20,
                    'games_won': gw_b, 'games_lost': gw_a,
                    'aces': ace_b_ev, 'dfs': df_b_ev, 'breaks': brk_b,
                    'p_10plus_aces': american_to_prob(ace_b10), 'p_no_df': p_nodf_b,
                    'adjustment': adj_b,
                },
            }

# ============================================================
# TAB 2: PROJECTIONS
# ============================================================
with tab2:
    st.markdown('<div class="section-header">Player Projections</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Sorted by value (pts/$1K) · All DK bonuses included</div>', unsafe_allow_html=True)

    if not st.session_state.odds_data:
        st.info("Enter odds in the Odds Input tab first.")
        st.stop()

    proj_rows = []
    for mk, odds in st.session_state.odds_data.items():
        if 'player_a' not in odds: continue
        for side in ['player_a', 'player_b']:
            o = odds[side]; name = o['name']
            proj = build_projection(o)
            sal = next((p['salary'] for p in st.session_state.players if p['name'] == name), 0)
            val = proj['score'] / (sal / 1000) if sal > 0 else 0
            proj_rows.append({
                'Player': name, 'Salary': f"${sal:,}", 'Win%': f"{proj['wp']:.0%}",
                'Proj': proj['score'], 'Value': round(val, 2),
                'GW': proj['games_won'], 'GL': proj['games_lost'],
                'SW': round(proj['sets_won'], 1), 'SL': round(proj['sets_lost'], 1),
                'Aces': round(proj['aces'], 1), 'DFs': round(proj['dfs'], 1),
                'Brks': round(proj['breaks'], 1), 'P(2-0)': f"{proj['p_straight']:.0%}",
            })
            st.session_state.projections[name] = {'projection': proj['score'], 'value': round(val, 3), **proj}

    if proj_rows:
        df = pd.DataFrame(proj_rows).sort_values('Value', ascending=False).reset_index(drop=True)
        df.index += 1; df.index.name = '#'

        c1, c2, c3, c4 = st.columns(4)
        top = df.iloc[0]
        c1.metric("Top Value", top['Player'], f"{top['Value']} pts/$1K")
        best_proj = df.sort_values('Proj', ascending=False).iloc[0]
        c2.metric("Highest Proj", best_proj['Player'], f"{best_proj['Proj']} pts")
        c3.metric("Players", len(df))
        c4.metric("Matches", len(st.session_state.matches))

        st.markdown("")
        st.dataframe(df, use_container_width=True, height=min(800, 35*len(df)+38))

# ============================================================
# TAB 3: LINEUP BUILDER
# ============================================================
with tab3:
    st.markdown('<div class="section-header">Lineup Builder</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Set exposure constraints and generate optimized lineups</div>', unsafe_allow_html=True)

    if not st.session_state.projections:
        st.info("Build projections first.")
        st.stop()

    player_sal_map = {p['name']: p for p in st.session_state.players}
    opp_map = {}
    for m in st.session_state.matches:
        opp_map[m['player_a']] = m['player_b']
        opp_map[m['player_b']] = m['player_a']

    sorted_p = sorted(st.session_state.projections.items(), key=lambda x: -x[1]['value'])
    player_data_for_opt = []

    st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;letter-spacing:1px;margin-bottom:8px;">PLAYER EXPOSURE</div>', unsafe_allow_html=True)

    for pi, (name, pd) in enumerate(sorted_p):
        p_info = player_sal_map.get(name, {})
        cols = st.columns([3, 1, 1, 1, 1, 1])
        cols[0].markdown(f"<span style='font-size:13px;font-weight:500;'>{name}</span> <span style='color:{TEXT_DIM};font-size:11px;'>vs {opp_map.get(name,'')}</span>", unsafe_allow_html=True)
        cols[1].caption(f"${p_info.get('salary',0):,}")
        cols[2].caption(f"{pd['score']:.1f}")
        cols[3].caption(f"{pd['value']:.2f}")
        min_e = cols[4].number_input("min", key=f"min_{pi}", value=0, min_value=0, max_value=100, step=5, label_visibility="collapsed")
        max_e = cols[5].number_input("max", key=f"max_{pi}", value=60, min_value=0, max_value=100, step=5, label_visibility="collapsed")

        player_data_for_opt.append({
            'name': name, 'salary': p_info.get('salary',0), 'id': p_info.get('id',0),
            'projection': pd['score'], 'value': pd['value'],
            'opponent': opp_map.get(name,''), 'min_exposure': min_e, 'max_exposure': max_e,
        })

    st.markdown("---")
    st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;letter-spacing:1px;margin-bottom:8px;">MATCH CAPS</div>', unsafe_allow_html=True)
    for mi, m in enumerate(st.session_state.matches):
        c1, c2 = st.columns([4, 1])
        c1.caption(f"{m['player_a']} vs {m['player_b']}")
        mc = c2.number_input("max", key=f"mc_{mi}", value=60, min_value=0, max_value=100, step=5, label_visibility="collapsed")
        for pd in player_data_for_opt:
            if pd['name'] in [m['player_a'], m['player_b']]:
                pd['match_max_exposure'] = mc

    st.markdown("---")
    if st.button("⚡ Build Lineups", type="primary", use_container_width=True):
        with st.spinner(f"Optimizing {n_lineups} lineups..."):
            sel, pcounts, all_lu = run_optimizer(player_data_for_opt, n_lineups, salary_cap, lineup_size)
        st.session_state.sel = sel
        st.session_state.pcounts = pcounts
        st.session_state.opt_data = player_data_for_opt
        st.session_state.total_valid = len(all_lu)
        st.success(f"Built {len(sel)} lineups from {len(all_lu):,} valid combinations")

    if 'sel' in st.session_state:
        sel = st.session_state.sel; pcounts = st.session_state.pcounts; pd_opt = st.session_state.opt_data

        st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;letter-spacing:1px;margin:16px 0 8px;">EXPOSURE REPORT</div>', unsafe_allow_html=True)
        exp_data = []
        for i, p in enumerate(pd_opt):
            exp_data.append({'Player': p['name'], 'Salary': f"${p['salary']:,}", 'Proj': p['projection'],
                             'Value': p['value'], 'Count': pcounts[i],
                             'Exposure': f"{pcounts[i]/len(sel)*100:.1f}%"})
        st.dataframe(pd.DataFrame(exp_data).sort_values('Value', ascending=False).reset_index(drop=True),
                     use_container_width=True, height=min(600, 35*len(exp_data)+38))

        # Lineup cards
        st.markdown(f'<div style="color:{TEXT_MUTED};font-size:12px;font-weight:600;letter-spacing:1px;margin:16px 0 8px;">LINEUPS</div>', unsafe_allow_html=True)
        for rank, (proj, sal, pidxs) in enumerate(sel[:20], 1):
            players_in = sorted([(pd_opt[i]['name'], pd_opt[i]['salary'], pd_opt[i]['projection'], pd_opt[i]['opponent']) for i in pidxs], key=lambda x: -x[1])
            rows_html = ""
            for nm, s, pr, op in players_in:
                rows_html += f"""<div class="lu-row">
                    <span class="lu-name">{nm}</span>
                    <span class="lu-opp">vs {op}</span>
                    <span class="lu-sal">${s:,}</span>
                    <span class="lu-pts">{pr:.1f}</span>
                </div>"""
            st.markdown(f"""<div class="lineup-card">
                <div class="lu-header"><span>Lineup #{rank}</span><span class="lu-proj">{proj:.2f} pts</span></div>
                {rows_html}
                <div class="lu-footer"><span>${sal:,}</span><span>{proj:.2f}</span></div>
            </div>""", unsafe_allow_html=True)
        if len(sel) > 20:
            st.caption(f"+ {len(sel)-20} more lineups (see Export tab)")

# ============================================================
# TAB 4: EXPORT
# ============================================================
with tab4:
    st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Download lineup files for DraftKings</div>', unsafe_allow_html=True)

    if 'sel' not in st.session_state:
        st.info("Generate lineups in the Builder tab first.")
        st.stop()

    sel = st.session_state.sel; pd_opt = st.session_state.opt_data

    # DK Upload
    upload_csv = "P,P,P,P,P,P\n"
    for proj, sal, pidxs in sel:
        ns = sorted([(pd_opt[i]['name'], pd_opt[i]['salary'], pd_opt[i]['id']) for i in pidxs], key=lambda x: -x[1])
        upload_csv += ",".join(str(n[2]) for n in ns) + "\n"

    st.download_button("📥  DraftKings Upload CSV", upload_csv, "dk_upload.csv", "text/csv",
                        type="primary", use_container_width=True)

    st.markdown("")

    # Readable
    rows = []
    for rank, (proj, sal, pidxs) in enumerate(sel, 1):
        ns = sorted([(pd_opt[i]['name'], pd_opt[i]['salary']) for i in pidxs], key=lambda x: -x[1])
        row = {'#': rank, 'Proj': proj, 'Salary': sal}
        for j, (n, s) in enumerate(ns): row[f'P{j+1}'] = n
        rows.append(row)
    r_csv = pd.DataFrame(rows).to_csv(index=False)
    st.download_button("📥  Readable Lineups CSV", r_csv, "lineups.csv", "text/csv", use_container_width=True)

    st.markdown("")

    # Exposure
    pcounts = st.session_state.pcounts
    e_rows = [{'Player': pd_opt[i]['name'], 'Salary': pd_opt[i]['salary'], 'Proj': pd_opt[i]['projection'],
                'Value': pd_opt[i]['value'], 'Count': pcounts[i], 'Exp%': round(pcounts[i]/len(sel)*100,1)}
               for i in range(len(pd_opt))]
    e_csv = pd.DataFrame(e_rows).sort_values('Value', ascending=False).to_csv(index=False)
    st.download_button("📥  Exposure Report CSV", e_csv, "exposure.csv", "text/csv", use_container_width=True)
