# 🎾 DK Tennis DFS Optimizer

A Streamlit app for building optimized DraftKings Tennis DFS lineups using sportsbook odds.

## What It Does

1. **Upload** your DraftKings salary CSV — auto-detects all matches and players
2. **Input sportsbook odds** (bet365, DraftKings Sportsbook, etc.) for each match:
   - Money lines → win probabilities
   - Set betting (2-0, 2-1 exact scores) → straight-set probabilities
   - Player games won lines → game projections
   - Breaks of serve → break point projections
   - Ace milestones (5+, 10+) → ace projections + 10+ Ace Bonus
   - Double fault milestones (2+, 3+) → DF projections + No-DF Bonus
3. **Review projections** with full DK scoring breakdown (all bonuses included)
4. **Set exposure caps** per player (min/max %) and per match
5. **Add your match reads** as +/- point adjustments (e.g., "wins in straights" = +3)
6. **Generate optimized lineups** with a 3-phase optimizer:
   - Phase 1a: Pre-allocate scarce minimum-exposure players
   - Phase 1b: Round-robin fill remaining minimums
   - Phase 2: Greedy fill to target count
   - Post-pass: Swap to resolve any remaining min-exposure deficits
7. **Download** DK-ready upload CSV, readable lineup CSV, and exposure report

## DK Scoring (Best of 3 Sets)

| Stat | Points |
|---|---|
| Match Played | +30 |
| Game Won / Lost | +2.5 / -2 |
| Set Won / Lost | +6 / -3 |
| Match Won | +6 |
| Ace | +0.4 |
| Double Fault | -1 |
| Break | +0.75 |
| Straight Sets Bonus | +6 |
| Clean Set Bonus | +4 |
| No Double Fault Bonus | +2.5 |
| 10+ Ace Bonus | +2 |

## Deploy to Streamlit Cloud (Free)

### Step 1: Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it `dk-tennis-optimizer` (or whatever you want)
3. Set it to **Private** (so only people with the link can access)
4. Upload these files:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repository, branch (`main`), and file (`app.py`)
5. Click **Deploy**
6. Wait ~2 minutes for it to build
7. You'll get a URL like `https://your-app-name.streamlit.app`

### Step 3: Share with Friends

Just send them the URL. They open it in any browser — no downloads, no installs.

If the repo is private, your friends won't be able to see the code, but the deployed app is still accessible via the direct URL.

## Run Locally (Optional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`

## Workflow Tips

- **Enter odds before projections**: The model uses sportsbook odds to derive every stat. Missing odds = fallback guesses.
- **Use bet365 set betting odds**: These are the single most impactful input. The 2-0 and 2-1 exact score odds drive straight-set bonus, sets won/lost, and clean set probability.
- **Ace milestones matter**: The 10+ Ace Bonus (+2 pts) is a real differentiator for big servers. Use the 5+ and 10+ milestone odds from bet365.
- **Match reads are additive**: Your +/- adjustment is added directly to the final projection after all scoring is calculated. Use ~+3 for "wins in straights" and ~-3 for "wins but goes 3 sets."
- **Exposure caps are percentages**: 25% on a 45-lineup build = 11 lineups. The optimizer enforces both min and max caps with a post-pass swap to clean up edge cases.
