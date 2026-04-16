import streamlit as st
import pandas as pd
import numpy as np
from itertools import combinations
import io
import math

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="DK Tennis Optimizer",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# DK Scoring - Best of 3
SCORING = {
    "match_played": 30,
    "game_won": 2.5,
    "game_lost": -2,
    "set_won": 6,
    "set_lost": -3,
    "match_won": 6,
    "ace": 0.4,
    "df": -1,
    "break": 0.75,
    "clean_set": 4,
    "straight_sets": 6,
    "no_df": 2.5,
    "ace_10plus": 2,
}

# ============================================================
# STYLING
# ============================================================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #1a1f2e;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 12px;
    }
    .match-header {
        background: linear-gradient(135deg, #1a472a 0%, #2d5a3f 100%);
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-weight: 600;
        font-size: 16px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 20px;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPERS
# ============================================================
def american_to_prob(odds):
    """Convert American odds to implied probability (vig-included)."""
    if odds is None or odds == 0:
        return 0.5
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def remove_vig_pair(p1, p2):
    """Remove vig from a pair of implied probabilities."""
    total = p1 + p2
    if total == 0:
        return 0.5, 0.5
    return p1 / total, p2 / total

def poisson_ev_from_milestone(odds, milestone):
    """Estimate expected value from a milestone (X+) odds using Poisson.
    P(X >= k) = 1 - CDF(k-1). Solve for lambda."""
    p = american_to_prob(odds)
    if p <= 0 or p >= 1:
        return milestone
    # For P(X >= k) = p, find lambda
    # Use Newton's method on Poisson CDF
    lam = milestone  # start guess
    for _ in range(50):
        # P(X < k) = sum(e^-lam * lam^i / i! for i in range(k))
        cdf = sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(milestone))
        target = 1 - p  # CDF(k-1) = 1 - P(X >= k)
        if abs(cdf - target) < 0.001:
            break
        # Derivative of CDF w.r.t. lambda
        dcdf = sum(math.exp(-lam) * (i * lam**(i-1) / math.factorial(i) - lam**i / math.factorial(i))
                    for i in range(milestone))
        if abs(dcdf) < 1e-10:
            break
        lam -= (cdf - target) / dcdf
        lam = max(0.1, min(lam, 30))
    return lam

def parse_dk_csv(uploaded_file):
    """Parse DraftKings salary CSV and extract player data."""
    content = uploaded_file.read().decode('utf-8')
    lines = content.strip().split('\n')

    players = []
    for line in lines:
        parts = line.split(',')
        # Look for rows with player data: Position, Name+ID, Name, ID, RosterPos, Salary, GameInfo, Team, AvgPPG
        if len(parts) >= 16:
            try:
                name = parts[9].strip()
                player_id = parts[10].strip()
                salary = int(parts[12].strip())
                game_info = parts[13].strip()
                avg_ppg = float(parts[15].strip()) if parts[15].strip() else 0
                if name and player_id.isdigit() and salary > 0:
                    # Parse opponent from game_info: "Player1@Player2 date time"
                    match_str = game_info.split(' ')[0] if game_info else ''
                    players.append({
                        'name': name,
                        'id': int(player_id),
                        'salary': salary,
                        'game_info': game_info,
                        'match_str': match_str,
                        'avg_ppg': avg_ppg,
                    })
            except (ValueError, IndexError):
                continue
    return players

def detect_matches(players):
    """Auto-detect matches from game_info strings."""
    match_map = {}
    for p in players:
        key = p['match_str']
        if key not in match_map:
            match_map[key] = []
        match_map[key].append(p['name'])

    matches = []
    for key, names in match_map.items():
        if len(names) == 2:
            matches.append({
                'key': key,
                'player_a': names[0],
                'player_b': names[1],
                'game_info': key,
            })
    return matches

def build_projection(odds, scoring=SCORING):
    """Build DK projection from sportsbook odds for one player."""
    # Win probability
    wp = odds.get('win_prob', 0.5)

    # Games
    games_won = odds.get('games_won', 10)
    games_lost = odds.get('games_lost', 10)

    # Sets
    p_straight_win = odds.get('p_straight_win', wp * 0.6)
    p_straight_loss = odds.get('p_straight_loss', (1 - wp) * 0.6)
    p_3set = 1 - p_straight_win - p_straight_loss

    e_sets_played = 2 * (1 - p_3set) + 3 * p_3set
    e_sets_won = 2 * p_straight_win + 1 * (wp - p_straight_win) + 1 * p_straight_loss + 0 * ((1-wp) - p_straight_loss)
    # Simpler: E[SW] = 2*P(win 2-0) + 1*P(win 2-1) + 1*P(lose 1-2) + 0*P(lose 0-2)
    p_win_3 = wp - p_straight_win  # P(win 2-1)
    p_lose_3 = (1 - wp) - p_straight_loss  # P(lose 1-2)
    e_sets_won = 2 * p_straight_win + 2 * p_win_3 + 1 * p_lose_3 + 0 * p_straight_loss
    e_sets_lost = e_sets_played - e_sets_won

    # Aces
    aces = odds.get('aces', 3)
    p_10plus_aces = odds.get('p_10plus_aces', 0)

    # DFs
    dfs = odds.get('dfs', 3)
    p_no_df = odds.get('p_no_df', math.exp(-dfs))

    # Breaks
    breaks = odds.get('breaks', wp * 3 + (1 - wp) * 1.5)

    # Clean set probability (per set won)
    clean_rate = odds.get('clean_set_rate', 0.05 + 0.15 * wp)
    e_clean_sets = e_sets_won * clean_rate

    # User projection adjustment
    adj = odds.get('adjustment', 0)

    # Calculate score
    score = (
        scoring["match_played"]
        + scoring["match_won"] * wp
        + scoring["set_won"] * e_sets_won
        + scoring["set_lost"] * e_sets_lost
        + scoring["game_won"] * games_won
        + scoring["game_lost"] * games_lost
        + scoring["ace"] * aces
        + scoring["df"] * dfs
        + scoring["break"] * breaks
        + scoring["straight_sets"] * p_straight_win
        + scoring["clean_set"] * e_clean_sets
        + scoring["no_df"] * p_no_df
        + scoring["ace_10plus"] * p_10plus_aces
        + adj
    )

    return {
        'score': round(score, 2),
        'wp': round(wp, 3),
        'games_won': round(games_won, 2),
        'games_lost': round(games_lost, 2),
        'sets_won': round(e_sets_won, 3),
        'sets_lost': round(e_sets_lost, 3),
        'sets_played': round(e_sets_played, 3),
        'aces': round(aces, 2),
        'dfs': round(dfs, 2),
        'breaks': round(breaks, 2),
        'p_straight': round(p_straight_win, 3),
        'p_3set': round(p_3set, 3),
        'p_no_df': round(p_no_df, 4),
        'p_10plus_aces': round(p_10plus_aces, 3),
        'clean_sets': round(e_clean_sets, 3),
    }

def run_optimizer(players_data, n_lineups=45, salary_cap=50000, lineup_size=6):
    """Run lineup optimizer with exposure caps."""
    # Build match structure
    idx_map = {p['name']: i for i, p in enumerate(players_data)}
    seen = set()
    matches = []
    for p in players_data:
        if p['name'] in seen:
            continue
        opp = p['opponent']
        if opp in idx_map:
            matches.append((p['name'], opp))
            seen.add(p['name'])
            seen.add(opp)

    match_options = []
    for a, b in matches:
        pa = players_data[idx_map[a]]
        pb = players_data[idx_map[b]]
        match_options.append([
            (idx_map[a], pa['salary'], pa['projection']),
            (idx_map[b], pb['salary'], pb['projection']),
        ])

    n_matches = len(match_options)

    # Generate all valid lineups
    all_lineups = []
    for mc in combinations(range(n_matches), lineup_size):
        for bits in range(2**lineup_size):
            ts = 0; tp = 0.0; pidxs = []
            for i, mi in enumerate(mc):
                side = (bits >> i) & 1
                pid, sal, proj = match_options[mi][side]
                ts += sal; tp += proj; pidxs.append(pid)
            if ts <= salary_cap:
                all_lineups.append((round(tp, 2), ts, tuple(pidxs)))

    all_lineups.sort(key=lambda x: -x[0])

    # Exposure caps
    max_caps = {}
    min_caps = {}
    for p in players_data:
        if p.get('max_exposure') is not None:
            max_caps[p['name']] = max(1, int(round(n_lineups * p['max_exposure'] / 100)))
        if p.get('min_exposure') is not None and p['min_exposure'] > 0:
            min_caps[p['name']] = max(1, int(round(n_lineups * p['min_exposure'] / 100)))

    default_cap = int(n_lineups * 0.60)  # 60% default max

    # Match caps
    match_caps_dict = {}
    for a, b in matches:
        pa = players_data[idx_map[a]]
        pb = players_data[idx_map[b]]
        mc = pa.get('match_max_exposure')
        if mc is not None:
            match_caps_dict[frozenset({a, b})] = max(1, int(round(n_lineups * mc / 100)))

    # Selection state
    selected = []
    selected_keys = set()
    player_counts = [0] * len(players_data)
    match_counts = {mc: 0 for mc in match_caps_dict}

    def can_add(pidxs):
        for pid in pidxs:
            nm = players_data[pid]['name']
            cap = max_caps.get(nm, default_cap)
            if player_counts[pid] + 1 > cap:
                return False
        for mc_key, mc_cap in match_caps_dict.items():
            hit = sum(1 for pid in pidxs if players_data[pid]['name'] in mc_key)
            if match_counts[mc_key] + hit > mc_cap:
                return False
        return True

    def add_lineup(proj, sal, pidxs):
        selected.append((proj, sal, pidxs))
        selected_keys.add(pidxs)
        for pid in pidxs:
            player_counts[pid] += 1
        for mc_key in match_caps_dict:
            match_counts[mc_key] += sum(1 for pid in pidxs if players_data[pid]['name'] in mc_key)

    # Phase 1a: Scarcity pre-allocation (mins sorted ascending)
    scarcity = sorted(min_caps.items(), key=lambda x: x[1])
    for name, _ in scarcity:
        target_idx = idx_map[name]
        while player_counts[target_idx] < min_caps[name] and len(selected) < n_lineups:
            placed = False
            for proj, sal, pidxs in all_lineups:
                if pidxs in selected_keys: continue
                if target_idx not in pidxs: continue
                if not can_add(pidxs): continue
                add_lineup(proj, sal, pidxs)
                placed = True
                break
            if not placed:
                break

    # Phase 1b: Round-robin for remaining min targets
    for iteration in range(500):
        if len(selected) >= n_lineups:
            break
        deficits = [(n, min_caps[n] - player_counts[idx_map[n]])
                     for n in min_caps if player_counts[idx_map[n]] < min_caps[n]]
        if not deficits:
            break
        deficits.sort(key=lambda x: (-x[1], player_counts[idx_map[x[0]]]))
        target_name = deficits[0][0]
        target_idx = idx_map[target_name]
        picked = False
        for proj, sal, pidxs in all_lineups:
            if pidxs in selected_keys: continue
            if target_idx not in pidxs: continue
            if not can_add(pidxs): continue
            add_lineup(proj, sal, pidxs)
            picked = True
            break
        if not picked:
            min_caps[target_name] = player_counts[target_idx]

    # Phase 2: Greedy fill
    for proj, sal, pidxs in all_lineups:
        if len(selected) >= n_lineups:
            break
        if pidxs in selected_keys:
            continue
        if not can_add(pidxs):
            continue
        add_lineup(proj, sal, pidxs)

    # Post-pass swap
    def min_still_met(remove_pidxs, add_pidxs, exclude):
        for other, other_min in min_caps.items():
            if other == exclude: continue
            oid = idx_map[other]
            change = (-1 if oid in remove_pidxs else 0) + (1 if oid in add_pidxs else 0)
            new_count = player_counts[oid] + change
            if player_counts[oid] >= other_min:
                if new_count < other_min: return False
            else:
                if change < 0: return False
        return True

    def feasible_after_swap(remove_pidxs, add_pidxs):
        new_counts = list(player_counts)
        for pid in remove_pidxs: new_counts[pid] -= 1
        for pid in add_pidxs: new_counts[pid] += 1
        for pid in range(len(players_data)):
            cap = max_caps.get(players_data[pid]['name'], default_cap)
            if new_counts[pid] > cap: return False
        new_mc = dict(match_counts)
        for mc_key in match_caps_dict:
            for pid in remove_pidxs:
                if players_data[pid]['name'] in mc_key: new_mc[mc_key] -= 1
            for pid in add_pidxs:
                if players_data[pid]['name'] in mc_key: new_mc[mc_key] += 1
            if new_mc[mc_key] > match_caps_dict[mc_key]: return False
        return True

    for iteration in range(200):
        deficits = [(n, min_caps[n] - player_counts[idx_map[n]])
                     for n in min_caps if player_counts[idx_map[n]] < min_caps[n]]
        if not deficits: break
        deficits.sort(key=lambda x: -x[1])
        name, deficit = deficits[0]
        target_idx = idx_map[name]
        did_swap = False
        for c_proj, c_sal, c_pidxs in all_lineups:
            if c_pidxs in selected_keys: continue
            if target_idx not in c_pidxs: continue
            selected.sort(key=lambda x: x[0])
            for i, (s_proj, s_sal, s_pidxs) in enumerate(selected):
                if target_idx in s_pidxs: continue
                if not min_still_met(s_pidxs, c_pidxs, name): continue
                if not feasible_after_swap(s_pidxs, c_pidxs): continue
                selected_keys.discard(s_pidxs)
                for pid in s_pidxs: player_counts[pid] -= 1
                for mc_key in match_caps_dict:
                    match_counts[mc_key] -= sum(1 for pid in s_pidxs if players_data[pid]['name'] in mc_key)
                selected[i] = (c_proj, c_sal, c_pidxs)
                selected_keys.add(c_pidxs)
                for pid in c_pidxs: player_counts[pid] += 1
                for mc_key in match_caps_dict:
                    match_counts[mc_key] += sum(1 for pid in c_pidxs if players_data[pid]['name'] in mc_key)
                did_swap = True
                break
            if did_swap: break
        if not did_swap:
            min_caps[name] = player_counts[idx_map[name]]

    selected.sort(key=lambda x: -x[0])
    return selected, player_counts, all_lineups

# ============================================================
# SESSION STATE INIT
# ============================================================
if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'odds_data' not in st.session_state:
    st.session_state.odds_data = {}
if 'projections' not in st.session_state:
    st.session_state.projections = {}
if 'exposure_settings' not in st.session_state:
    st.session_state.exposure_settings = {}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("# 🎾 DK Tennis")
    st.markdown("### Optimizer")
    st.markdown("---")

    uploaded_file = st.file_uploader("Upload DK Salary CSV", type=['csv'])

    if uploaded_file:
        players = parse_dk_csv(uploaded_file)
        if players:
            st.session_state.players = players
            st.session_state.matches = detect_matches(players)
            st.success(f"Loaded {len(players)} players, {len(st.session_state.matches)} matches")
        else:
            st.error("Could not parse CSV. Check format.")

    st.markdown("---")
    st.markdown("**Lineup Settings**")
    n_lineups = st.number_input("Number of lineups", min_value=1, max_value=150, value=45)
    salary_cap = st.number_input("Salary cap", min_value=10000, max_value=100000, value=50000, step=1000)
    lineup_size = st.number_input("Roster size", min_value=2, max_value=8, value=6)

    st.markdown("---")
    st.markdown("##### DK Scoring (Best of 3)")
    st.caption("Match Played +30 | Game Won +2.5 | Game Lost -2 | Set Won +6 | Set Lost -3 | Match Won +6 | Ace +0.4 | DF -1 | Break +0.75 | Straight Sets +6 | Clean Set +4 | No DF +2.5 | 10+ Aces +2")

# ============================================================
# MAIN TABS
# ============================================================
if not st.session_state.players:
    st.markdown("# 🎾 DK Tennis DFS Optimizer")
    st.markdown("### Upload your DraftKings salary CSV to get started")
    st.markdown("""
    **Workflow:**
    1. **Upload** your DK salary CSV in the sidebar
    2. **Input odds** from bet365 / sportsbooks for each match
    3. **Review projections** and adjust with your match reads
    4. **Set exposure caps** and generate optimized lineups
    5. **Download** the DK-ready upload CSV
    """)
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Odds Input", "📈 Projections", "⚙️ Lineup Builder", "📥 Export"])

# ============================================================
# TAB 1: ODDS INPUT
# ============================================================
with tab1:
    st.markdown("## Match Odds Input")
    st.caption("Enter sportsbook odds for each match. American odds format (e.g. -150, +275).")

    for mi, match in enumerate(st.session_state.matches):
        pa_name = match['player_a']
        pb_name = match['player_b']
        match_key = f"{pa_name}_vs_{pb_name}"

        if match_key not in st.session_state.odds_data:
            st.session_state.odds_data[match_key] = {}

        with st.expander(f"🎾 {pa_name} vs {pb_name}", expanded=(mi < 3)):
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown(f"**{pa_name}**")
                ml_a = st.number_input(f"Money Line", key=f"ml_a_{mi}", value=-200, step=5)
            with col_b:
                st.markdown(f"**{pb_name}**")
                ml_b = st.number_input(f"Money Line", key=f"ml_b_{mi}", value=160, step=5)

            # Derive win probabilities
            raw_a = american_to_prob(ml_a)
            raw_b = american_to_prob(ml_b)
            wp_a, wp_b = remove_vig_pair(raw_a, raw_b)

            st.caption(f"Implied win %: {pa_name} **{wp_a:.1%}** | {pb_name} **{wp_b:.1%}**")

            st.markdown("---")
            st.markdown("**Set Betting**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sb_a_20 = st.number_input(f"{pa_name} 2-0", key=f"sb_a20_{mi}", value=-120, step=5)
            with col2:
                sb_a_21 = st.number_input(f"{pa_name} 2-1", key=f"sb_a21_{mi}", value=240, step=5)
            with col3:
                sb_b_20 = st.number_input(f"{pb_name} 2-0", key=f"sb_b20_{mi}", value=600, step=5)
            with col4:
                sb_b_21 = st.number_input(f"{pb_name} 2-1", key=f"sb_b21_{mi}", value=550, step=5)

            # Normalize set betting
            raw_probs = [american_to_prob(x) for x in [sb_a_20, sb_a_21, sb_b_20, sb_b_21]]
            total_raw = sum(raw_probs)
            if total_raw > 0:
                p_a20, p_a21, p_b20, p_b21 = [p / total_raw for p in raw_probs]
            else:
                p_a20, p_a21, p_b20, p_b21 = 0.4, 0.2, 0.1, 0.1

            st.caption(f"Set probs: {pa_name} 2-0 **{p_a20:.1%}** | 2-1 **{p_a21:.1%}** | {pb_name} 2-0 **{p_b20:.1%}** | 2-1 **{p_b21:.1%}**")

            st.markdown("---")
            st.markdown("**Player Games Won**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                gw_a_line = st.number_input(f"{pa_name} line", key=f"gw_a_{mi}", value=12.5, step=0.5)
            with col2:
                gw_a_over = st.number_input(f"Over odds", key=f"gw_ao_{mi}", value=-150, step=5)
            with col3:
                gw_b_line = st.number_input(f"{pb_name} line", key=f"gw_b_{mi}", value=10.5, step=0.5)
            with col4:
                gw_b_over = st.number_input(f"Over odds", key=f"gw_bo_{mi}", value=-120, step=5)

            # Adjust games won by over/under lean
            gw_a_adj = gw_a_line + (0.5 if american_to_prob(gw_a_over) > 0.55 else -0.3 if american_to_prob(gw_a_over) < 0.45 else 0)
            gw_b_adj = gw_b_line + (0.5 if american_to_prob(gw_b_over) > 0.55 else -0.3 if american_to_prob(gw_b_over) < 0.45 else 0)

            st.markdown("---")
            st.markdown("**Breaks of Serve**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                brk_a_line = st.number_input(f"{pa_name} line", key=f"brk_a_{mi}", value=2.5, step=0.5)
            with col2:
                brk_a_over = st.number_input(f"Over odds", key=f"brk_ao_{mi}", value=-200, step=5)
            with col3:
                brk_b_line = st.number_input(f"{pb_name} line", key=f"brk_b_{mi}", value=1.5, step=0.5)
            with col4:
                brk_b_over = st.number_input(f"Over odds", key=f"brk_bo_{mi}", value=-120, step=5)

            brk_a_adj = brk_a_line + (0.5 if american_to_prob(brk_a_over) > 0.6 else 0)
            brk_b_adj = brk_b_line + (0.2 if american_to_prob(brk_b_over) > 0.55 else 0)

            st.markdown("---")
            st.markdown("**Aces & Double Faults**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                ace_a_5plus = st.number_input(f"{pa_name} 5+ Aces", key=f"ace_a5_{mi}", value=-200, step=5,
                                               help="Odds for 5+ aces")
            with col2:
                ace_a_10plus = st.number_input(f"{pa_name} 10+ Aces", key=f"ace_a10_{mi}", value=400, step=5)
            with col3:
                ace_b_5plus = st.number_input(f"{pb_name} 5+ Aces", key=f"ace_b5_{mi}", value=-225, step=5)
            with col4:
                ace_b_10plus = st.number_input(f"{pb_name} 10+ Aces", key=f"ace_b10_{mi}", value=333, step=5)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                df_a_2plus = st.number_input(f"{pa_name} 2+ DFs", key=f"df_a2_{mi}", value=-275, step=5)
            with col2:
                df_a_3plus = st.number_input(f"{pa_name} 3+ DFs", key=f"df_a3_{mi}", value=100, step=5)
            with col3:
                df_b_2plus = st.number_input(f"{pb_name} 2+ DFs", key=f"df_b2_{mi}", value=100, step=5)
            with col4:
                df_b_3plus = st.number_input(f"{pb_name} 3+ DFs", key=f"df_b3_{mi}", value=300, step=5)

            ace_a_ev = poisson_ev_from_milestone(ace_a_5plus, 5)
            ace_b_ev = poisson_ev_from_milestone(ace_b_5plus, 5)
            df_a_ev = poisson_ev_from_milestone(df_a_3plus, 3)
            df_b_ev = poisson_ev_from_milestone(df_b_3plus, 3)

            p_10ace_a = american_to_prob(ace_a_10plus)
            p_10ace_b = american_to_prob(ace_b_10plus)
            p_no_df_a = 1 - american_to_prob(df_a_2plus) if american_to_prob(df_a_2plus) < 0.95 else math.exp(-df_a_ev)
            p_no_df_b = 1 - american_to_prob(df_b_2plus) if american_to_prob(df_b_2plus) < 0.95 else math.exp(-df_b_ev)

            st.caption(f"Estimated E[Aces]: {pa_name} **{ace_a_ev:.1f}** | {pb_name} **{ace_b_ev:.1f}** | "
                       f"E[DFs]: {pa_name} **{df_a_ev:.1f}** | {pb_name} **{df_b_ev:.1f}**")

            st.markdown("---")
            st.markdown("**Your Match Read (projection adjustment)**")
            col1, col2 = st.columns(2)
            with col1:
                adj_a = st.number_input(f"{pa_name} +/- pts", key=f"adj_a_{mi}", value=0.0, step=0.5,
                                         help="e.g. +3 if you think they win in straights, -3 if 3-set match")
            with col2:
                adj_b = st.number_input(f"{pb_name} +/- pts", key=f"adj_b_{mi}", value=0.0, step=0.5)

            # Store all odds
            st.session_state.odds_data[match_key] = {
                'player_a': {
                    'name': pa_name, 'win_prob': wp_a,
                    'p_straight_win': p_a20, 'p_straight_loss': p_b20,
                    'games_won': gw_a_adj, 'games_lost': gw_b_adj,
                    'aces': ace_a_ev, 'dfs': df_a_ev,
                    'breaks': brk_a_adj,
                    'p_10plus_aces': p_10ace_a, 'p_no_df': p_no_df_a,
                    'adjustment': adj_a,
                },
                'player_b': {
                    'name': pb_name, 'win_prob': wp_b,
                    'p_straight_win': p_b20, 'p_straight_loss': p_a20,
                    'games_won': gw_b_adj, 'games_lost': gw_a_adj,
                    'aces': ace_b_ev, 'dfs': df_b_ev,
                    'breaks': brk_b_adj,
                    'p_10plus_aces': p_10ace_b, 'p_no_df': p_no_df_b,
                    'adjustment': adj_b,
                },
            }

# ============================================================
# TAB 2: PROJECTIONS
# ============================================================
with tab2:
    st.markdown("## Projections")

    if not st.session_state.odds_data:
        st.info("Enter odds in the Odds Input tab first.")
        st.stop()

    # Build projections
    proj_rows = []
    for match_key, odds in st.session_state.odds_data.items():
        if 'player_a' not in odds:
            continue
        for side in ['player_a', 'player_b']:
            o = odds[side]
            name = o['name']
            proj = build_projection(o)

            # Find salary
            salary = 0
            for p in st.session_state.players:
                if p['name'] == name:
                    salary = p['salary']
                    break

            value = proj['score'] / (salary / 1000) if salary > 0 else 0

            proj_rows.append({
                'Player': name,
                'Salary': salary,
                'Win%': f"{proj['wp']:.0%}",
                'Proj': proj['score'],
                'Value': round(value, 3),
                'GW': proj['games_won'],
                'GL': proj['games_lost'],
                'SW': proj['sets_won'],
                'SL': proj['sets_lost'],
                'Aces': proj['aces'],
                'DFs': proj['dfs'],
                'Brks': proj['breaks'],
                'P(2-0)': f"{proj['p_straight']:.0%}",
                'P(NoDf)': f"{proj['p_no_df']:.1%}",
                'P(10A)': f"{proj['p_10plus_aces']:.0%}",
            })

            st.session_state.projections[name] = {
                'projection': proj['score'],
                'value': round(value, 3),
                **proj,
            }

    if proj_rows:
        df = pd.DataFrame(proj_rows)
        df = df.sort_values('Value', ascending=False).reset_index(drop=True)
        df.index += 1
        df.index.name = 'Rank'

        st.dataframe(
            df,
            use_container_width=True,
            height=min(700, 35 * len(df) + 38),
        )

        st.markdown("---")
        st.markdown("### Quick Stats")
        col1, col2, col3 = st.columns(3)
        with col1:
            top_player = df.iloc[0]
            st.metric("Top Value", f"{top_player['Player']}", f"{top_player['Value']} pts/$1K")
        with col2:
            top_proj = df.sort_values('Proj', ascending=False).iloc[0]
            st.metric("Highest Projection", f"{top_proj['Player']}", f"{top_proj['Proj']} pts")
        with col3:
            st.metric("Players Projected", len(df))

# ============================================================
# TAB 3: LINEUP BUILDER
# ============================================================
with tab3:
    st.markdown("## Lineup Builder")

    if not st.session_state.projections:
        st.info("Build projections first in the Projections tab.")
        st.stop()

    st.markdown("### Exposure Settings")
    st.caption("Set min/max exposure %. Leave blank for defaults (max 60%, min 0%).")

    # Build exposure settings table
    player_data_for_opt = []
    player_sal_map = {p['name']: p for p in st.session_state.players}

    # Find opponents
    opp_map = {}
    for match in st.session_state.matches:
        opp_map[match['player_a']] = match['player_b']
        opp_map[match['player_b']] = match['player_a']

    # Sort players by value
    sorted_players = sorted(
        [(name, data) for name, data in st.session_state.projections.items()],
        key=lambda x: -x[1]['value']
    )

    cols_header = st.columns([3, 1, 1, 1, 1, 1])
    cols_header[0].markdown("**Player**")
    cols_header[1].markdown("**Salary**")
    cols_header[2].markdown("**Proj**")
    cols_header[3].markdown("**Value**")
    cols_header[4].markdown("**Min %**")
    cols_header[5].markdown("**Max %**")

    for pi, (name, proj_data) in enumerate(sorted_players):
        p_info = player_sal_map.get(name, {})
        salary = p_info.get('salary', 0)
        dk_id = p_info.get('id', 0)

        cols = st.columns([3, 1, 1, 1, 1, 1])
        cols[0].markdown(f"{name}")
        cols[1].markdown(f"${salary:,}")
        cols[2].markdown(f"{proj_data['score']:.1f}")
        cols[3].markdown(f"{proj_data['value']:.2f}")

        min_exp = cols[4].number_input("min", key=f"min_{pi}", value=0, min_value=0, max_value=100,
                                        step=5, label_visibility="collapsed")
        max_exp = cols[5].number_input("max", key=f"max_{pi}", value=60, min_value=0, max_value=100,
                                        step=5, label_visibility="collapsed")

        player_data_for_opt.append({
            'name': name,
            'salary': salary,
            'id': dk_id,
            'projection': proj_data['score'],
            'value': proj_data['value'],
            'opponent': opp_map.get(name, ''),
            'min_exposure': min_exp,
            'max_exposure': max_exp,
        })

    st.markdown("---")
    st.markdown("### Match-Level Caps")
    st.caption("Set maximum total exposure across both players in a match.")

    for mi, match in enumerate(st.session_state.matches):
        col1, col2 = st.columns([3, 1])
        col1.markdown(f"{match['player_a']} vs {match['player_b']}")
        mc = col2.number_input("Max %", key=f"match_cap_{mi}", value=60, min_value=0, max_value=100,
                                step=5, label_visibility="collapsed")
        # Store on both players
        for pd in player_data_for_opt:
            if pd['name'] in [match['player_a'], match['player_b']]:
                pd['match_max_exposure'] = mc

    st.markdown("---")

    if st.button("🚀 Generate Lineups", type="primary", use_container_width=True):
        with st.spinner(f"Optimizing {n_lineups} lineups..."):
            selected, player_counts, all_lineups = run_optimizer(
                player_data_for_opt,
                n_lineups=n_lineups,
                salary_cap=salary_cap,
                lineup_size=lineup_size,
            )

        st.session_state.selected_lineups = selected
        st.session_state.player_counts = player_counts
        st.session_state.player_data_for_opt = player_data_for_opt
        st.session_state.total_valid = len(all_lineups)

        st.success(f"Generated {len(selected)} lineups from {len(all_lineups):,} valid combinations!")

    # Display results
    if 'selected_lineups' in st.session_state:
        selected = st.session_state.selected_lineups
        player_counts = st.session_state.player_counts
        player_data = st.session_state.player_data_for_opt

        st.markdown("### Exposure Report")
        exp_rows = []
        for i, pd in enumerate(player_data):
            cnt = player_counts[i]
            exp_rows.append({
                'Player': pd['name'],
                'Salary': pd['salary'],
                'Proj': pd['projection'],
                'Value': pd['value'],
                'Count': cnt,
                'Exposure': f"{cnt / len(selected) * 100:.1f}%",
            })
        exp_df = pd.DataFrame(exp_rows).sort_values('Value', ascending=False).reset_index(drop=True)
        st.dataframe(exp_df, use_container_width=True, height=min(700, 35 * len(exp_df) + 38))

        st.markdown("### Lineup Preview")
        for rank, (proj, sal, pidxs) in enumerate(selected[:10], 1):
            names = [player_data[i]['name'] for i in pidxs]
            sals = [player_data[i]['salary'] for i in pidxs]
            sorted_names = [n for _, n in sorted(zip(sals, names), reverse=True)]
            st.caption(f"#{rank} | Proj: {proj:.2f} | Sal: ${sal:,} | {' / '.join(sorted_names)}")

        if len(selected) > 10:
            st.caption(f"... and {len(selected) - 10} more lineups")

# ============================================================
# TAB 4: EXPORT
# ============================================================
with tab4:
    st.markdown("## Export Lineups")

    if 'selected_lineups' not in st.session_state:
        st.info("Generate lineups in the Lineup Builder tab first.")
        st.stop()

    selected = st.session_state.selected_lineups
    player_data = st.session_state.player_data_for_opt

    # DK Upload CSV
    st.markdown("### DraftKings Upload CSV")
    st.caption("Drop this directly into DraftKings bulk lineup import.")

    upload_rows = []
    for proj, sal, pidxs in selected:
        name_sal = sorted([(player_data[i]['name'], player_data[i]['salary'], player_data[i]['id'])
                            for i in pidxs], key=lambda x: -x[1])
        upload_rows.append([str(ns[2]) for ns in name_sal])

    upload_csv = "P,P,P,P,P,P\n"
    upload_csv += "\n".join([",".join(row) for row in upload_rows])

    st.download_button(
        label="📥 Download DK Upload CSV",
        data=upload_csv,
        file_name="dk_tennis_upload.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

    # Readable Lineups CSV
    st.markdown("### Readable Lineups CSV")
    readable_rows = []
    for rank, (proj, sal, pidxs) in enumerate(selected, 1):
        name_sal = sorted([(player_data[i]['name'], player_data[i]['salary'])
                            for i in pidxs], key=lambda x: -x[1])
        row = {'Rank': rank, 'Proj': proj, 'Salary': sal}
        for j, (n, s) in enumerate(name_sal):
            row[f'P{j+1}'] = n
        readable_rows.append(row)

    readable_df = pd.DataFrame(readable_rows)
    readable_csv = readable_df.to_csv(index=False)

    st.download_button(
        label="📥 Download Readable Lineups CSV",
        data=readable_csv,
        file_name="dk_tennis_lineups.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Exposure CSV
    st.markdown("### Exposure Report CSV")
    player_counts = st.session_state.player_counts
    exp_rows = []
    for i, pd_item in enumerate(player_data):
        cnt = player_counts[i]
        exp_rows.append({
            'Player': pd_item['name'],
            'Salary': pd_item['salary'],
            'Projection': pd_item['projection'],
            'Value': pd_item['value'],
            'Count': cnt,
            'Exposure_Pct': round(cnt / len(selected) * 100, 1),
        })
    exp_df = pd.DataFrame(exp_rows).sort_values('Value', ascending=False)
    exp_csv = exp_df.to_csv(index=False)

    st.download_button(
        label="📥 Download Exposure Report CSV",
        data=exp_csv,
        file_name="dk_tennis_exposure.csv",
        mime="text/csv",
        use_container_width=True,
    )
