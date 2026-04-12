// LineChart — Phase 2B and 2C trend over years
export function LineChart({ data2c, data2b, p2c_ratio, p2b_ratio }) {
  // If no historical data, build a flat line from current ratio
  const DEFAULT_YEARS = ["2021","2022","2023","2024","2025"];
  const effectiveData2c = (data2c && Object.keys(data2c).length > 0) ? data2c
    : DEFAULT_YEARS.reduce((acc, y) => ({ ...acc, [y]: p2c_ratio || 0 }), {});
  const effectiveData2b = (data2b && Object.keys(data2b).length > 0) ? data2b
    : DEFAULT_YEARS.reduce((acc, y) => ({ ...acc, [y]: p2b_ratio || 0 }), {});
  const years = Object.keys(effectiveData2c);
  const data2cFinal = effectiveData2c;
  const data2bFinal = effectiveData2b;
  const vals2c = years.map(y => data2cFinal[y]);
  const vals2b = years.map(y => data2bFinal[y] || 0);
  const allVals = [...vals2c, ...vals2b].filter(Boolean);
  const maxV = Math.max(...allVals, 1);
  const W = 320, H = 70, PAD = { l: 28, r: 8, t: 8, b: 18 };
  const gW = W - PAD.l - PAD.r;
  const gH = H - PAD.t - PAD.b;

  const px = (i) => PAD.l + (i / (years.length - 1)) * gW;
  const py = (v) => PAD.t + gH - (v / maxV) * gH;

  const mkPath = (vals) =>
    vals.map((v, i) => `${i === 0 ? 'M' : 'L'}${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(' ');

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: H }}>
        {/* Grid lines */}
        {[0, 0.5, 1].map(t => {
          const y = PAD.t + gH * (1 - t);
          const v = (maxV * t).toFixed(1);
          return (
            <g key={t}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y} y2={y} stroke="#e8e6e0" strokeWidth="0.5" />
              <text x={PAD.l - 3} y={y + 3} fontSize="7" fill="#b4b2a9" textAnchor="end">{v}</text>
            </g>
          );
        })}
        {/* Oversubscribed line at y=1 */}
        <line x1={PAD.l} x2={W - PAD.r} y1={py(1)} y2={py(1)} stroke="#D85A30" strokeWidth="0.8" strokeDasharray="3,3" opacity="0.5" />
        <text x={W - PAD.r + 2} y={py(1) + 3} fontSize="7" fill="#D85A30" opacity="0.7">1.0</text>

        {/* Phase 2B line */}
        <path d={mkPath(vals2b)} fill="none" stroke="#378ADD" strokeWidth="1.2" />
        {/* Phase 2C line */}
        <path d={mkPath(vals2c)} fill="none" stroke="#1D9E75" strokeWidth="1.5" />

        {/* Year labels */}
        {years.map((y, i) => (
          <text key={y} x={px(i)} y={H - 2} fontSize="7" fill="#b4b2a9" textAnchor="middle">{y}</text>
        ))}
      </svg>
      <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 10, color: '#888780' }}>
        <span><span style={{ display: 'inline-block', width: 12, height: 2, background: '#1D9E75', verticalAlign: 'middle', marginRight: 4 }} />Phase 2C</span>
        <span><span style={{ display: 'inline-block', width: 12, height: 2, background: '#378ADD', verticalAlign: 'middle', marginRight: 4 }} />Phase 2B</span>
        <span style={{ marginLeft: 'auto' }}>Dashed = oversubscribed threshold</span>
      </div>
    </div>
  );
}

// RadarChart — School vibe pentagon
export function RadarChart({ vibe }) {
  if (!vibe) return null;
  const DIMS = [
    { key: 'academic', label: 'Academic' },
    { key: 'homework', label: 'Homework' },
    { key: 'parentComp', label: 'Parents' },
    { key: 'teacherQ', label: 'Teachers' },
    { key: 'culture', label: 'Culture' },
  ];
  const N = DIMS.length;
  const CX = 60, CY = 60, R = 48;

  const angle = (i) => (Math.PI * 2 * i) / N - Math.PI / 2;
  const point = (i, r) => ({
    x: CX + r * Math.cos(angle(i)),
    y: CY + r * Math.sin(angle(i)),
  });

  const outerPts = DIMS.map((_, i) => point(i, R));
  const outerPath = outerPts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + 'Z';

  const dataPts = DIMS.map((d, i) => point(i, (vibe[d.key] / 10) * R));
  const dataPath = dataPts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + 'Z';

  // midline rings
  const rings = [0.25, 0.5, 0.75, 1].map(t => {
    const pts = DIMS.map((_, i) => point(i, R * t));
    return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + 'Z';
  });

  return (
    <svg viewBox="0 0 120 120" style={{ width: 110, height: 110, flexShrink: 0 }}>
      {rings.map((r, i) => <path key={i} d={r} fill="none" stroke="#e8e6e0" strokeWidth="0.5" />)}
      {outerPts.map((p, i) => (
        <line key={i} x1={CX} y1={CY} x2={p.x} y2={p.y} stroke="#e8e6e0" strokeWidth="0.5" />
      ))}
      <path d={dataPath} fill="rgba(212,83,126,0.2)" stroke="#D4537E" strokeWidth="1.2" />
      {DIMS.map((d, i) => {
        const lp = point(i, R + 10);
        return <text key={d.key} x={lp.x} y={lp.y} fontSize="7" fill="#888780" textAnchor="middle" dominantBaseline="middle">{d.label}</text>;
      })}
    </svg>
  );
}
