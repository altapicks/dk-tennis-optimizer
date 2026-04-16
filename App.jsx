import { useState, useEffect, useMemo, useCallback } from 'react';
import { processMatch, dkProjection, ppProjection, ppEV, optimize } from './lib/engine';

// ============================================================
// DATA LOADER
// ============================================================
function useSlateData() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetch('/data/slate.json')
      .then(r => { if (!r.ok) throw new Error('No slate data'); return r.json(); })
      .then(setData)
      .catch(e => setError(e.message));
  }, []);
  return { data, error };
}

// ============================================================
// PROJECTION BUILDER
// ============================================================
function buildProjections(data) {
  if (!data) return { dkPlayers: [], ppRows: [] };
  const dkMap = {};
  data.dk_players.forEach(p => { dkMap[p.name] = p; });
  const oppMap = {};
  data.matches.forEach(m => {
    oppMap[m.player_a] = m.player_b;
    oppMap[m.player_b] = m.player_a;
  });
  const matchTimeMap = {};
  data.matches.forEach(m => {
    matchTimeMap[m.player_a] = { time: m.start_time, tournament: m.tournament };
    matchTimeMap[m.player_b] = { time: m.start_time, tournament: m.tournament };
  });

  const dkPlayers = [];
  data.matches.forEach(match => {
    const stats = processMatch(match);
    [['player_a', stats.player_a], ['player_b', stats.player_b]].forEach(([side, s]) => {
      const name = match[side];
      const dk = dkMap[name];
      if (!dk) return;
      const proj = dkProjection(s);
      const val = dk.salary > 0 ? Math.round(proj / (dk.salary / 1000) * 100) / 100 : 0;
      const ppProj = ppProjection(s);
      dkPlayers.push({
        name, salary: dk.salary, id: dk.id, avgPPG: dk.avg_ppg,
        opponent: oppMap[name] || '', tournament: matchTimeMap[name]?.tournament || '',
        startTime: matchTimeMap[name]?.time || '',
        wp: s.wp, proj, val, pStraight: s.pStraightWin, p3set: s.p3set,
        gw: s.gw, gl: s.gl, sw: s.setsWon, sl: s.setsLost,
        aces: s.aces, dfs: s.dfs, breaks: s.breaks,
        p10ace: s.p10ace, pNoDF: s.pNoDF,
        ppProj, stats: s,
      });
    });
  });

  // PP EV rows
  const ppRows = [];
  if (data.pp_lines) {
    data.pp_lines.forEach(line => {
      const player = dkPlayers.find(p => p.name === line.player);
      if (!player) return;
      let projected = 0;
      if (line.stat === 'Fantasy Score') projected = player.ppProj;
      else if (line.stat === 'Games Won') projected = player.gw;
      else if (line.stat === 'Aces') projected = player.aces;
      else if (line.stat === 'Total Games') projected = player.gw + player.gl;
      else if (line.stat === 'Double Faults') projected = player.dfs;
      else if (line.stat === 'Sets Won') projected = player.sw;
      else if (line.stat === 'Breaks') projected = player.breaks;
      else projected = 0;
      const ev = ppEV(projected, line.line);
      ppRows.push({
        player: line.player, stat: line.stat, line: line.line,
        projected: Math.round(projected * 100) / 100, ev,
        opponent: player.opponent, wp: player.wp,
        direction: ev > 0 ? 'MORE' : ev < 0 ? 'LESS' : '-',
      });
    });
  }

  return { dkPlayers, ppRows };
}

// ============================================================
// SORTABLE TABLE HOOK
// ============================================================
function useSort(data, defaultKey = 'val', defaultDir = 'desc') {
  const [sortKey, setSortKey] = useState(defaultKey);
  const [sortDir, setSortDir] = useState(defaultDir);
  const sorted = useMemo(() => {
    const arr = [...data];
    arr.sort((a, b) => {
      let va = a[sortKey], vb = b[sortKey];
      if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb || '').toLowerCase(); }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return arr;
  }, [data, sortKey, sortDir]);
  const toggleSort = useCallback((key) => {
    if (key === sortKey) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  }, [sortKey]);
  return { sorted, sortKey, sortDir, toggleSort };
}

// ============================================================
// HEADER COMPONENT
// ============================================================
function SortHeader({ label, colKey, sortKey, sortDir, onSort }) {
  const active = colKey === sortKey;
  return (
    <th className={active ? 'sorted' : ''} onClick={() => onSort(colKey)}>
      {label}
      {active && <span className="sort-arrow">{sortDir === 'asc' ? '▲' : '▼'}</span>}
    </th>
  );
}

// ============================================================
// FORMAT HELPERS
// ============================================================
const fmt = (n, d = 1) => (typeof n === 'number' ? n.toFixed(d) : '-');
const fmtPct = (n) => (typeof n === 'number' ? (n * 100).toFixed(0) + '%' : '-');
const fmtTime = (iso) => {
  if (!iso) return '-';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  } catch { return iso; }
};
const fmtSal = (n) => '$' + n.toLocaleString();

// ============================================================
// MAIN APP
// ============================================================
export default function App() {
  const { data, error } = useSlateData();
  const [tab, setTab] = useState('dk');
  const { dkPlayers, ppRows } = useMemo(() => buildProjections(data), [data]);

  if (error) return <div className="app"><div className="empty"><h2>No Slate Loaded</h2><p>Push a slate.json to /public/data/ and redeploy.</p></div></div>;
  if (!data) return <div className="app"><div className="empty"><h2>Loading...</h2></div></div>;

  const tabs = [
    { id: 'dk', label: 'DK Projections' },
    { id: 'pp', label: 'PP Projections' },
    { id: 'build', label: 'Lineup Builder' },
    { id: 'export', label: 'Export' },
  ];

  return (
    <div className="app">
      <div className="topbar">
        <div className="topbar-brand">
          <img src="/logo.png" alt="DD" />
          <span>DeuceData</span>
        </div>
        <div className="topbar-date">{data.date} · {data.matches.length} matches</div>
      </div>
      <div className="tab-bar">
        {tabs.map(t => (
          <button key={t.id} className={`tab ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="content">
        {tab === 'dk' && <DKTab players={dkPlayers} matchCount={data.matches.length} />}
        {tab === 'pp' && <PPTab rows={ppRows} />}
        {tab === 'build' && <BuilderTab players={dkPlayers} />}
        {tab === 'export' && <ExportTab players={dkPlayers} />}
      </div>
    </div>
  );
}

// ============================================================
// DK PROJECTIONS TAB
// ============================================================
function DKTab({ players, matchCount }) {
  const { sorted, sortKey, sortDir, toggleSort } = useSort(players, 'val', 'desc');

  // Compute top-3 value and top-3 straight-set
  const top3val = useMemo(() => [...players].sort((a, b) => b.val - a.val).slice(0, 3).map(p => p.name), [players]);
  const top3ss = useMemo(() => [...players].sort((a, b) => b.pStraight - a.pStraight).slice(0, 3).map(p => p.name), [players]);

  // Find earliest start time
  const startTimes = players.filter(p => p.startTime).map(p => fmtTime(p.startTime));
  const firstStart = startTimes.length > 0 ? startTimes[0] : '-';

  const SH = (props) => <SortHeader {...props} sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />;

  return (
    <>
      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Top Value</div>
          <div className="metric-value">{top3val.map((n, i) => <div key={i} style={{fontSize: i === 0 ? '18px' : '13px', color: i === 0 ? undefined : 'var(--text-muted)', fontWeight: i === 0 ? 700 : 500}}>{i + 1}. {n}</div>)}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Top Straight-Set Odds</div>
          <div className="metric-value">{top3ss.map((n, i) => {
            const p = players.find(x => x.name === n);
            return <div key={i} style={{fontSize: i === 0 ? '18px' : '13px', color: i === 0 ? undefined : 'var(--text-muted)', fontWeight: i === 0 ? 700 : 500}}>{n} <span style={{fontSize:'12px',color:'var(--text-dim)'}}>{fmtPct(p?.pStraight)}</span></div>;
          })}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Matches</div>
          <div className="metric-value">{matchCount}</div>
        </div>
        <div className="metric">
          <div className="metric-label">First Start</div>
          <div className="metric-value">{firstStart}</div>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <SH label="Player" colKey="name" />
              <SH label="Opp" colKey="opponent" />
              <SH label="Salary" colKey="salary" />
              <SH label="Win%" colKey="wp" />
              <SH label="Proj" colKey="proj" />
              <SH label="Value" colKey="val" />
              <SH label="P(2-0)" colKey="pStraight" />
              <SH label="GW" colKey="gw" />
              <SH label="GL" colKey="gl" />
              <SH label="SW" colKey="sw" />
              <SH label="Aces" colKey="aces" />
              <SH label="DFs" colKey="dfs" />
              <SH label="Brks" colKey="breaks" />
              <SH label="Time" colKey="startTime" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((p, i) => {
              const isTop3Val = top3val.includes(p.name);
              const isTop3SS = top3ss.includes(p.name);
              return (
                <tr key={p.name}>
                  <td className="muted">{i + 1}</td>
                  <td className="name">{p.name}</td>
                  <td className="muted">{p.opponent}</td>
                  <td className="num">{fmtSal(p.salary)}</td>
                  <td className="num">{fmtPct(p.wp)}</td>
                  <td className="num"><span className={isTop3Val ? 'cell-top3' : 'cell-proj'}>{fmt(p.proj, 2)}</span></td>
                  <td className="num"><span className={isTop3Val ? 'cell-top3' : ''}>{fmt(p.val, 2)}</span></td>
                  <td className="num"><span className={isTop3SS ? 'cell-top3' : ''}>{fmtPct(p.pStraight)}</span></td>
                  <td className="num">{fmt(p.gw)}</td>
                  <td className="num muted">{fmt(p.gl)}</td>
                  <td className="num">{fmt(p.sw)}</td>
                  <td className="num">{fmt(p.aces)}</td>
                  <td className="num muted">{fmt(p.dfs)}</td>
                  <td className="num">{fmt(p.breaks)}</td>
                  <td className="muted">{fmtTime(p.startTime)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ============================================================
// PP PROJECTIONS TAB
// ============================================================
function PPTab({ rows }) {
  const { sorted, sortKey, sortDir, toggleSort } = useSort(rows, 'ev', 'desc');

  const top3ev = useMemo(() => [...rows].sort((a, b) => b.ev - a.ev).slice(0, 3).map(r => r.player + '|' + r.stat), [rows]);
  const worst3ev = useMemo(() => [...rows].sort((a, b) => a.ev - b.ev).slice(0, 3), [rows]);

  const SH = (props) => <SortHeader {...props} sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />;

  return (
    <>
      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Top EV Plays</div>
          <div className="metric-value">
            {[...rows].sort((a, b) => b.ev - a.ev).slice(0, 3).map((r, i) => (
              <div key={i} style={{fontSize: i === 0 ? '16px' : '13px', color: i === 0 ? 'var(--green)' : 'var(--text-muted)'}}>
                {r.player} {r.stat} <span style={{color:'var(--green)'}}>+{fmt(r.ev, 2)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="metric">
          <div className="metric-label">Worst EV (Fade)</div>
          <div className="metric-value">
            {worst3ev.map((r, i) => (
              <div key={i} style={{fontSize: i === 0 ? '16px' : '13px', color: i === 0 ? 'var(--red)' : 'var(--text-muted)'}}>
                {r.player} {r.stat} <span style={{color:'var(--red)'}}>{fmt(r.ev, 2)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <SH label="Player" colKey="player" />
              <SH label="Stat" colKey="stat" />
              <SH label="PP Line" colKey="line" />
              <SH label="Projected" colKey="projected" />
              <SH label="EV" colKey="ev" />
              <SH label="Play" colKey="direction" />
              <SH label="Win%" colKey="wp" />
              <SH label="Opp" colKey="opponent" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => {
              const key = r.player + '|' + r.stat;
              const isTop = top3ev.includes(key);
              const isWorst = worst3ev.some(w => w.player === r.player && w.stat === r.stat);
              return (
                <tr key={key}>
                  <td className="muted">{i + 1}</td>
                  <td className="name">{r.player}</td>
                  <td>{r.stat}</td>
                  <td className="num">{fmt(r.line, 1)}</td>
                  <td className="num"><span className="cell-proj">{fmt(r.projected, 2)}</span></td>
                  <td className="num">
                    <span className={isTop ? 'cell-ev-top' : isWorst ? 'cell-ev-worst' : r.ev > 0 ? 'cell-ev-pos' : r.ev < 0 ? 'cell-ev-neg' : ''}>
                      {r.ev > 0 ? '+' : ''}{fmt(r.ev, 2)}
                    </span>
                  </td>
                  <td><span style={{color: r.direction === 'MORE' ? 'var(--green)' : r.direction === 'LESS' ? 'var(--red)' : 'var(--text-dim)', fontWeight: 600}}>{r.direction}</span></td>
                  <td className="num muted">{fmtPct(r.wp)}</td>
                  <td className="muted">{r.opponent}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ============================================================
// LINEUP BUILDER TAB
// ============================================================
function BuilderTab({ players: rawPlayers }) {
  const [exposures, setExposures] = useState({});
  const [result, setResult] = useState(null);
  const [nLineups, setNLineups] = useState(45);
  const [salCap, setSalCap] = useState(50000);

  const sortedPlayers = useMemo(() => [...rawPlayers].sort((a, b) => b.val - a.val), [rawPlayers]);

  const setExp = (name, field, val) => {
    setExposures(prev => ({ ...prev, [name]: { ...prev[name], [field]: val } }));
  };

  const runBuild = () => {
    const pData = sortedPlayers.map(p => ({
      name: p.name, salary: p.salary, id: p.id, projection: p.proj,
      opponent: p.opponent,
      maxExp: exposures[p.name]?.max ?? 60,
      minExp: exposures[p.name]?.min ?? 0,
    }));
    const res = optimize(pData, nLineups, salCap, 6);
    setResult({ ...res, pData });
  };

  return (
    <>
      <div className="section-head">Lineup Builder</div>
      <div className="section-sub">Set exposure % per player, then build optimized lineups</div>

      <div style={{display:'flex', gap: 12, marginBottom: 16}}>
        <label style={{fontSize:13, color:'var(--text-muted)'}}>
          Lineups: <input style={{width:60, background:'var(--bg)', border:'1px solid var(--border)', borderRadius:4, color:'var(--text)', padding:'4px 8px', marginLeft:4}} type="number" value={nLineups} onChange={e => setNLineups(+e.target.value)} />
        </label>
        <label style={{fontSize:13, color:'var(--text-muted)'}}>
          Salary Cap: <input style={{width:70, background:'var(--bg)', border:'1px solid var(--border)', borderRadius:4, color:'var(--text)', padding:'4px 8px', marginLeft:4}} type="number" value={salCap} onChange={e => setSalCap(+e.target.value)} />
        </label>
      </div>

      <div className="builder-controls">
        {sortedPlayers.map(p => (
          <div className="ctrl-row" key={p.name}>
            <span className="ctrl-name">{p.name}</span>
            <span className="ctrl-proj">{fmt(p.proj, 1)}</span>
            <input type="number" placeholder="Min" value={exposures[p.name]?.min ?? 0}
              onChange={e => setExp(p.name, 'min', +e.target.value)} title="Min %" />
            <input type="number" placeholder="Max" value={exposures[p.name]?.max ?? 60}
              onChange={e => setExp(p.name, 'max', +e.target.value)} title="Max %" />
          </div>
        ))}
      </div>

      <button className="btn btn-primary" onClick={runBuild}>⚡ Build Lineups</button>

      {result && (
        <>
          <div style={{marginTop:20, marginBottom:8, fontSize:13, color:'var(--text-muted)'}}>
            Built {result.lineups.length} lineups from {result.total.toLocaleString()} valid combinations
          </div>

          <div className="section-head" style={{marginTop:20}}>Exposure</div>
          <div className="table-wrap" style={{marginBottom:20}}>
            <table>
              <thead><tr><th>Player</th><th>Salary</th><th>Proj</th><th>Value</th><th>Count</th><th>Exposure</th></tr></thead>
              <tbody>
                {result.pData.map((p, i) => {
                  const cnt = result.counts[i];
                  const pct = result.lineups.length > 0 ? (cnt / result.lineups.length * 100) : 0;
                  return (
                    <tr key={p.name}>
                      <td className="name">{p.name}</td>
                      <td className="num">{fmtSal(p.salary)}</td>
                      <td className="num">{fmt(p.projection, 1)}</td>
                      <td className="num">{fmt(p.projection / (p.salary / 1000), 2)}</td>
                      <td className="num">{cnt}</td>
                      <td>
                        <span className="exp-bar-bg"><span className="exp-bar" style={{width: pct + '%'}} /></span>
                        {pct.toFixed(1)}%
                      </td>
                    </tr>
                  );
                }).sort((a, b) => b.props.children[3].props.children - a.props.children[3].props.children)}
              </tbody>
            </table>
          </div>

          <div className="section-head">Lineups</div>
          <div className="lineup-grid">
            {result.lineups.slice(0, 30).map((lu, idx) => {
              const ps = lu.players.map(i => result.pData[i]).sort((a, b) => b.salary - a.salary);
              return (
                <div className="lu-card" key={idx}>
                  <div className="lu-header">
                    <span>#{idx + 1}</span>
                    <span className="lu-proj">{lu.proj} pts</span>
                  </div>
                  {ps.map(p => (
                    <div className="lu-row" key={p.name}>
                      <span className="lu-name">{p.name}</span>
                      <span className="lu-opp">vs {p.opponent}</span>
                      <span className="lu-sal">{fmtSal(p.salary)}</span>
                      <span className="lu-pts">{fmt(p.projection, 1)}</span>
                    </div>
                  ))}
                  <div className="lu-footer">
                    <span>{fmtSal(lu.sal)}</span>
                    <span>{lu.proj}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </>
  );
}

// ============================================================
// EXPORT TAB
// ============================================================
function ExportTab({ players }) {
  const [result, setResult] = useState(null);

  // Pull from builder state if available (or re-run)
  const sortedPlayers = useMemo(() => [...players].sort((a, b) => b.val - a.val), [players]);

  const download = (content, filename) => {
    const blob = new Blob([content], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  const exportDK = () => {
    // Quick build with defaults
    const pData = sortedPlayers.map(p => ({
      name: p.name, salary: p.salary, id: p.id, projection: p.proj,
      opponent: p.opponent, maxExp: 60, minExp: 0,
    }));
    const res = optimize(pData, 45, 50000, 6);
    let csv = 'P,P,P,P,P,P\n';
    res.lineups.forEach(lu => {
      const ps = lu.players.map(i => pData[i]).sort((a, b) => b.salary - a.salary);
      csv += ps.map(p => p.id).join(',') + '\n';
    });
    download(csv, 'dk_upload.csv');
  };

  const exportReadable = () => {
    const pData = sortedPlayers.map(p => ({
      name: p.name, salary: p.salary, id: p.id, projection: p.proj,
      opponent: p.opponent, maxExp: 60, minExp: 0,
    }));
    const res = optimize(pData, 45, 50000, 6);
    let csv = 'Rank,Proj,Salary,P1,P2,P3,P4,P5,P6\n';
    res.lineups.forEach((lu, i) => {
      const ps = lu.players.map(j => pData[j]).sort((a, b) => b.salary - a.salary);
      csv += `${i + 1},${lu.proj},${lu.sal},${ps.map(p => p.name).join(',')}\n`;
    });
    download(csv, 'lineups.csv');
  };

  const exportProjections = () => {
    let csv = 'Player,Salary,Win%,Proj,Value,GW,GL,SW,Aces,DFs,Breaks,P(2-0),Opponent\n';
    sortedPlayers.forEach(p => {
      csv += `${p.name},${p.salary},${(p.wp*100).toFixed(0)}%,${p.proj},${p.val},${fmt(p.gw)},${fmt(p.gl)},${fmt(p.sw)},${fmt(p.aces)},${fmt(p.dfs)},${fmt(p.breaks)},${fmtPct(p.pStraight)},${p.opponent}\n`;
    });
    download(csv, 'projections.csv');
  };

  return (
    <>
      <div className="section-head">Export</div>
      <div className="section-sub">Download lineup files for DraftKings</div>
      <div style={{maxWidth: 400, display: 'flex', flexDirection: 'column', gap: 8}}>
        <button className="btn btn-primary" onClick={exportDK}>📥 DraftKings Upload CSV</button>
        <button className="btn btn-outline" onClick={exportReadable}>📥 Readable Lineups CSV</button>
        <button className="btn btn-outline" onClick={exportProjections}>📥 Projections CSV</button>
      </div>
    </>
  );
}
