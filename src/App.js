import { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, CircleMarker, Circle, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import SCHOOLS from './schools.json';
import PhaseExplainer from './PhaseExplainer';
import './App.css';

// Fix Leaflet default icon issue with webpack
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const COLORS = { Easy: '#1D9E75', Moderate: '#BA7517', Competitive: '#D85A30' };
const YEARS = [2023, 2024, 2025];

function ratioClass(r) {
  if (r < 1.2) return 'easy';
  if (r < 2.0) return 'moderate';
  return 'competitive';
}

function postalToLatLng(postal) {
  const p = parseInt(postal);
  if (isNaN(p)) return null;
  const lat = Math.min(Math.max(1.28 + (p % 10000) / 100000 * 1.5, 1.25), 1.45);
  const lng = Math.min(Math.max(103.65 + (p % 1000) / 10000 * 3, 103.65), 104.0);
  return [lat, lng];
}

function MapController({ selected, homePos }) {
  const map = useMap();
  useEffect(() => {
    if (selected) map.panTo([selected.lat, selected.lng], { animate: true });
  }, [selected, map]);
  useEffect(() => {
    if (homePos) map.panTo(homePos, { animate: true });
  }, [homePos, map]);
  return null;
}

export default function App() {
  const [filters, setFilters] = useState({ zone: 'all', gender: 'all', type: 'all', p2c: 'all', search: '' });
  const [radius, setRadius] = useState(1);
  const [homePos, setHomePos] = useState(null);
  const [selected, setSelected] = useState(null);
  const [showExplainer, setShowExplainer] = useState(false);
  const listRef = useRef(null);

  const filtered = SCHOOLS.filter(s => {
    if (filters.zone !== 'all' && s.zone !== filters.zone) return false;
    if (filters.gender !== 'all' && s.gender !== filters.gender) return false;
    if (filters.type !== 'all' && !s.types.includes(filters.type)) return false;
    if (filters.p2c !== 'all' && s.p2c !== filters.p2c) return false;
    if (filters.search && !s.name.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  });

  const filteredNames = new Set(filtered.map(s => s.name));

  const handleSelect = useCallback((school) => {
    setSelected(school);
    // Scroll selected card into view
    setTimeout(() => {
      const el = listRef.current?.querySelector(`[data-name="${school.name}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }, []);

  const setChip = (key, val) => setFilters(f => ({ ...f, [key]: val }));

  const handleAddrKey = (e) => {
    if (e.key === 'Enter') {
      const pos = postalToLatLng(e.target.value.trim());
      setHomePos(pos);
    }
  };

  const maxHist = selected ? Math.max(...selected.hist) : 1;

  return (
    <div className="app">
      {/* ── SIDEBAR ── */}
      <div className="sidebar">
        <div className="nav">
          <div className="logo">
            <div className="logo-mark">
              <svg viewBox="0 0 14 14" fill="none" width="14" height="14">
                <circle cx="7" cy="7" r="5" stroke="#fff" strokeWidth="1.5"/>
                <path d="M4.5 7h5M7 4.5v5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <div>
              <div className="logo-text">P1 Finder</div>
              <div className="logo-sub">Singapore primary schools</div>
            </div>
          </div>
          <button className="help-btn" onClick={() => setShowExplainer(v => !v)} title="How phases work">?</button>
        </div>

        <div className="search-wrap">
          <input
            className="search-input"
            placeholder="Search schools..."
            value={filters.search}
            onChange={e => setChip('search', e.target.value)}
          />
        </div>

        <div className="filters">
          <FilterRow label="Zone" options={['all','North','South','East','West']} labels={['All','North','South','East','West']} value={filters.zone} onChange={v => setChip('zone', v)} />
          <FilterRow label="School" options={['all','Co-ed','Girls','Boys']} labels={['All','Co-ed','Girls','Boys']} value={filters.gender} onChange={v => setChip('gender', v)} />
          <FilterRow label="Type" options={['all','SAP','GEP','Autonomous','Affiliated']} labels={['All','SAP','GEP','Autonomous','Affiliated']} value={filters.type} onChange={v => setChip('type', v)} />
          <FilterRow label="Phase 2B" options={['all','Easy','Moderate','Competitive']} labels={['All','Easy','Moderate','Competitive']} value={filters.p2b} onChange={v => setChip('p2b', v)} />
          <FilterRow label="Phase 2C" options={['all','Easy','Moderate','Competitive']} labels={['All','Easy','Moderate','Competitive']} value={filters.p2c} onChange={v => setChip('p2c', v)} />
        </div>

        <div className="addr-row">
          <input className="addr-input" placeholder="Postal code + Enter..." type="text" onKeyDown={handleAddrKey} />
          <div className="radius-btns">
            {[1, 2].map(r => (
              <button key={r} className={`rbtn ${radius === r ? 'on' : ''}`} onClick={() => setRadius(r)}>{r}km</button>
            ))}
          </div>
        </div>

        <div className="results-bar">Showing {filtered.length} of {SCHOOLS.length} schools</div>

        <div className="school-list" ref={listRef}>
          {filtered.length === 0 && <div className="no-results">No schools match your filters</div>}
          {filtered.map(s => (
            <div
              key={s.name}
              data-name={s.name}
              className={`school-card ${selected?.name === s.name ? 'selected' : ''}`}
              onClick={() => handleSelect(s)}
            >
              <div className="sc-top">
                <div className="sc-name">{s.name}</div>
                <div className="sc-badges">
                  {s.types.map(t => <span key={t} className={`badge b-${t.toLowerCase()}`}>{t}</span>)}
                </div>
              </div>
              <div className="sc-addr">{s.addr}</div>
              {s.pv && <span className="badge b-pv">PV ballot required</span>}
              <div className="sc-metrics">
                <div className="metric">
                  <div className="m-label">Phase 2B</div>
                  <div className={`m-val ${ratioClass(s.p2b_ratio)}`}>{s.p2b_ratio.toFixed(2)}</div>
                </div>
                <div className="metric">
                  <div className="m-label">Phase 2C</div>
                  <div className={`m-val ${ratioClass(s.p2c_ratio)}`}>{s.p2c_ratio.toFixed(2)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── MAP PANEL ── */}
      <div className="map-panel">
        <div className="map-wrap">
          <MapContainer center={[1.3521, 103.8198]} zoom={12} style={{ width: '100%', height: '100%' }} zoomControl={true}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
              maxZoom={18}
            />
            <MapController selected={selected} homePos={homePos} />

            {/* Home radius ring */}
            {homePos && (
              <Circle
                center={homePos}
                radius={radius * 1000}
                pathOptions={{ color: '#1D9E75', weight: 1.5, dashArray: '6 5', fillColor: '#1D9E75', fillOpacity: 0.08 }}
              />
            )}

            {/* School markers */}
            {SCHOOLS.map(s => {
              const isFiltered = filteredNames.has(s.name);
              const isSelected = selected?.name === s.name;
              return (
                <CircleMarker
                  key={s.name}
                  center={[s.lat, s.lng]}
                  radius={isSelected ? 10 : 6}
                  pathOptions={{
                    fillColor: COLORS[s.p2c] || '#888',
                    fillOpacity: isFiltered ? 0.9 : 0.15,
                    color: isSelected ? '#fff' : 'transparent',
                    weight: isSelected ? 2 : 0,
                  }}
                  eventHandlers={{ click: () => handleSelect(s) }}
                >
                  <Popup>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{s.name}</div>
                    <div style={{ fontSize: 12, color: '#5f5e5a', marginTop: 2 }}>2C ratio: {s.p2c_ratio.toFixed(2)} · {s.p2c}</div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>

          {/* Legend */}
          <div className="map-legend">
            {Object.entries(COLORS).map(([label, color]) => (
              <div key={label} className="leg-item">
                <div className="leg-dot" style={{ background: color }} />
                {label}
              </div>
            ))}
          </div>

          {/* Phase explainer overlay */}
          {showExplainer && <PhaseExplainer onClose={() => setShowExplainer(false)} />}
        </div>

        {/* ── DETAIL PANEL ── */}
        {selected && (
          <div className="detail-panel">
            <div className="detail-top">
              <div>
                <div className="detail-name">{selected.name}</div>
                <div className="detail-meta">{selected.addr} · {selected.zone} · {selected.gender}{selected.types.length ? ' · ' + selected.types.join(', ') : ''}</div>
              </div>
              <button className="detail-close" onClick={() => setSelected(null)}>✕</button>
            </div>
            <div className="detail-metrics">
              <div className="dm"><div className="dm-label">Phase 2B ratio</div><div className={`dm-val ${ratioClass(selected.p2b_ratio)}`}>{selected.p2b_ratio.toFixed(2)}</div></div>
              <div className="dm"><div className="dm-label">Phase 2C ratio</div><div className={`dm-val ${ratioClass(selected.p2c_ratio)}`}>{selected.p2c_ratio.toFixed(2)}</div></div>
              <div className="dm"><div className="dm-label">PV ballot</div><div className="dm-val" style={{ fontSize: 13, paddingTop: 3, color: selected.pv ? '#D85A30' : '#1D9E75' }}>{selected.pv ? 'Required' : 'Open'}</div></div>
            </div>
            <div className="hist-section">
              <div className="hist-label">Phase 2C trend (applicants per vacancy)</div>
              <div className="hist-bars">
                {selected.hist.map((v, i) => {
                  const h = Math.round((v / maxHist) * 36) || 4;
                  const col = ratioClass(v) === 'easy' ? '#9FE1CB' : ratioClass(v) === 'moderate' ? '#FAC775' : '#F0997B';
                  return (
                    <div key={i} className="hbar-col">
                      <div className="hbar-ratio">{v.toFixed(2)}</div>
                      <div className="hbar" style={{ height: h, background: col }} />
                      <div className="hbar-year">{YEARS[i]}</div>
                    </div>
                  );
                })}
                <div className="hist-note">
                  {selected.hist[2] > selected.hist[0] ? 'Getting more competitive year on year.' : 'Trend stable or easing.'}
                  {selected.ccas?.length > 0 && <> CCAs: {selected.ccas.slice(0, 4).join(', ')}{selected.ccas.length > 4 ? '...' : ''}.</>}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function FilterRow({ label, options, labels, value, onChange }) {
  return (
    <div className="filter-row">
      <div className="filter-label">{label}</div>
      <div className="chips">
        {options.map((opt, i) => (
          <span key={opt} className={`chip ${value === opt ? 'on' : ''}`} onClick={() => onChange(opt)}>
            {labels[i]}
          </span>
        ))}
      </div>
    </div>
  );
}
