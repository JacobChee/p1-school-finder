import { useState, useRef, useCallback, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import SCHOOLS from './schools.json';
import PhaseExplainer from './PhaseExplainer';
import { LineChart, RadarChart } from './Charts';
import './App.css';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const COLORS = { Easy: '#1D9E75', Moderate: '#BA7517', Competitive: '#D85A30' };

function ratioClass(r) {
  if (r < 1.2) return 'easy';
  if (r < 2.0) return 'moderate';
  return 'competitive';
}

function getDistanceKm(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLng/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

async function postalToLatLng(postal) {
  try {
    const res = await fetch(
      `https://www.onemap.gov.sg/api/common/elastic/search?searchVal=${postal}&returnGeom=Y&getAddrDetails=Y&pageNum=1`
    );
    const data = await res.json();
    if (data.results && data.results.length > 0) {
      const { LATITUDE, LONGITUDE } = data.results[0];
      return [parseFloat(LATITUDE), parseFloat(LONGITUDE)];
    }
    return null;
  } catch {
    return null;
  }
}

function MapController({ selected, homePos }) {
  const map = useMap();
  if (selected) map.panTo([selected.lat, selected.lng], { animate: true });
  if (homePos && !selected) map.panTo(homePos, { animate: true });
  return null;
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

export default function App() {
  const [search, setSearch] = useState('');
  const [zone, setZone] = useState('all');
  const [gender, setGender] = useState('all');
  const [type, setType] = useState('all');
  const [p2b, setP2b] = useState('all');
  const [p2c, setP2c] = useState('all');
  const [radius, setRadius] = useState(1);
  const [homePos, setHomePos] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detailTab, setDetailTab] = useState('trend');
  const [showExplainer, setShowExplainer] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [mobileView, setMobileView] = useState('map');
  const [addrLoading, setAddrLoading] = useState(false);
  const listRef = useRef(null);

  const filtered = useMemo(() => SCHOOLS.filter(s => {
    if (zone !== 'all' && s.zone !== zone) return false;
    if (gender !== 'all' && s.gender !== gender) return false;
    if (type !== 'all' && !s.types.includes(type)) return false;
    if (p2b !== 'all' && s.p2b !== p2b) return false;
    if (p2c !== 'all' && s.p2c !== p2c) return false;
    if (search.trim() && !s.name.toLowerCase().includes(search.trim().toLowerCase())) return false;
    if (homePos && s.lat && s.lng) {
      const dist = getDistanceKm(homePos[0], homePos[1], s.lat, s.lng);
      if (dist > radius) return false;
    }
    return true;
  }), [search, zone, gender, type, p2b, p2c, homePos, radius]);

  const filteredNames = useMemo(() => new Set(filtered.map(s => s.name)), [filtered]);

  const handleSelect = useCallback((school) => {
    setSelected(school);
    setDetailTab('trend');
    setTimeout(() => {
      const el = listRef.current?.querySelector(`[data-name="${school.name}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }, []);

  const handleAddrKey = async (e) => {
    if (e.key === 'Enter') {
      const input = e.target.value.trim();
      if (!input) { setHomePos(null); return; }
      setAddrLoading(true);
      const pos = await postalToLatLng(input);
      setAddrLoading(false);
      if (pos) setHomePos(pos);
      else alert('Address not found. Try a valid Singapore postal code.');
    }
  };

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
          <div style={{ display:'flex', gap:6, alignItems:'center' }}>
            <button className="mobile-view-btn" onClick={() => setMobileView(v => v === 'list' ? 'map' : 'list')}>
              {mobileView === 'list' ? '🗺' : '☰'}
            </button>
            <button className="filter-toggle-btn" onClick={() => setShowFilters(v => !v)}>
              Filters {showFilters ? '▲' : '▼'}
            </button>
            <button className="help-btn" onClick={() => setShowExplainer(v => !v)}>?</button>
          </div>
        </div>

        <div className="search-wrap">
          <input
            className="search-input"
            placeholder="Search schools..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div className={`filters ${showFilters ? 'filters-open' : 'filters-closed'}`}>
          <FilterRow label="Zone" options={['all','North','South','East','West']} labels={['All','North','South','East','West']} value={zone} onChange={setZone} />
          <FilterRow label="School" options={['all','Co-ed','Girls','Boys']} labels={['All','Co-ed','Girls','Boys']} value={gender} onChange={setGender} />
          <FilterRow label="Type" options={['all','SAP','GEP','Autonomous','Affiliated']} labels={['All','SAP','GEP','Autonomous','Affiliated']} value={type} onChange={setType} />
          <FilterRow label="Phase 2B" options={['all','Easy','Moderate','Competitive']} labels={['All','Easy','Moderate','Competitive']} value={p2b} onChange={setP2b} />
          <FilterRow label="Phase 2C" options={['all','Easy','Moderate','Competitive']} labels={['All','Easy','Moderate','Competitive']} value={p2c} onChange={setP2c} />
        </div>

        <div className="addr-row">
          <input
            className="addr-input"
            placeholder={addrLoading ? 'Locating...' : 'Postal code + Enter...'}
            type="text"
            onKeyDown={handleAddrKey}
            disabled={addrLoading}
            style={addrLoading ? { opacity: 0.6 } : {}}
          />
          <div className="radius-btns">
            {[1, 2].map(r => (
              <button key={r} className={`rbtn ${radius === r ? 'on' : ''}`} onClick={() => setRadius(r)}>{r}km</button>
            ))}
          </div>
        </div>

        <div className="results-bar">
          Showing <strong>{filtered.length}</strong> of {SCHOOLS.length} schools{homePos ? ` within ${radius}km` : ''}
        </div>

        <div className="school-list" ref={listRef} style={{ display: mobileView === 'map' ? 'none' : 'block' }}>
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
          <MapContainer center={[1.3521, 103.8198]} zoom={11} style={{ width:'100%', height:'100%' }} zoomControl>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
              maxZoom={18}
            />
            <MapController selected={selected} homePos={homePos} />
            {homePos && (
              <Circle
                center={homePos}
                radius={radius * 1000}
                pathOptions={{ color:'#1D9E75', weight:1.5, dashArray:'6 5', fillColor:'#1D9E75', fillOpacity:0.08 }}
              />
            )}
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
                    fillOpacity: isFiltered ? 0.9 : 0.12,
                    color: isSelected ? '#fff' : 'transparent',
                    weight: isSelected ? 2 : 0,
                  }}
                  eventHandlers={{ click: () => handleSelect(s) }}
                >
                  <Popup>
                    <div style={{ fontSize:13, fontWeight:500 }}>{s.name}</div>
                    <div style={{ fontSize:12, color:'#5f5e5a', marginTop:2 }}>
                      2C ratio: {s.p2c_ratio.toFixed(2)} · {s.p2c}
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>

          <div className="map-legend">
            {Object.entries(COLORS).map(([label, color]) => (
              <div key={label} className="leg-item">
                <div className="leg-dot" style={{ background: color }} />
                {label}
              </div>
            ))}
          </div>

          {showExplainer && <PhaseExplainer onClose={() => setShowExplainer(false)} />}
        </div>

        <div className="disclaimer">
          Data from MOE Singapore. Balloting ratios updated annually every August.{' '}
          <a href="https://www.moe.gov.sg/primary/p1-registration" target="_blank" rel="noreferrer" style={{ color:'#1D9E75' }}>Verify with MOE</a> before deciding.
        </div>
      </div>

      {/* ── SCHOOL MODAL ── */}
      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <div className="modal-name">{selected.name}</div>
                <div className="modal-meta">
                  {selected.addr} · {selected.zone} · {selected.gender}
                  {selected.types.length ? ' · ' + selected.types.join(', ') : ''}
                </div>
              </div>
              <button className="detail-close" onClick={() => setSelected(null)}>✕</button>
            </div>
            <div className="modal-metrics">
              <div className="dm">
                <div className="dm-label">Phase 2B ratio</div>
                <div className={`dm-val ${ratioClass(selected.p2b_ratio)}`}>{selected.p2b_ratio.toFixed(2)}</div>
              </div>
              <div className="dm">
                <div className="dm-label">Phase 2C ratio</div>
                <div className={`dm-val ${ratioClass(selected.p2c_ratio)}`}>{selected.p2c_ratio.toFixed(2)}</div>
              </div>
              <div className="dm">
                <div className="dm-label">PV ballot</div>
                <div className="dm-val" style={{ fontSize:13, paddingTop:3, color: selected.pv ? '#D85A30' : '#1D9E75' }}>
                  {selected.pv ? 'Required' : 'Open'}
                </div>
              </div>
            </div>
            <div className="detail-tabs">
              <button className={`dtab ${detailTab==='trend'?'on':''}`} onClick={() => setDetailTab('trend')}>Trend</button>
              <button className={`dtab ${detailTab==='vibe'?'on':''}`} onClick={() => setDetailTab('vibe')}>School vibe</button>
            </div>
            {detailTab === 'trend' && selected.hist2c && (
              <div className="trend-section">
                <LineChart data2c={selected.hist2c} data2b={selected.hist2b} />
                {selected.ccas?.length > 0 && <div className="cca-row">CCAs: {selected.ccas.slice(0,5).join(', ')}</div>}
              </div>
            )}
            {detailTab === 'vibe' && selected.vibe && (
              <div className="vibe-section">
                <RadarChart vibe={selected.vibe} />
                <div className="vibe-scores">
                  {[['Academic','academic'],['Homework','homework'],['Parent competitiveness','parentComp'],['Teacher quality','teacherQ'],['Culture','culture']].map(([label,key]) => (
                    <div key={key} className="vs-row">
                      <span className="vs-label">{label}</span>
                      <div className="vs-bar-wrap">
                        <div className="vs-bar" style={{ width:`${selected.vibe[key]*10}%`, background: selected.vibe[key]>=7.5?'#D85A30':selected.vibe[key]>=6?'#BA7517':'#1D9E75' }} />
                      </div>
                      <span className="vs-val">{selected.vibe[key].toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
