import { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, CircleMarker, Circle, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import SCHOOLS from './schools.json';
import PhaseExplainer from './PhaseExplainer';
import { LineChart, RadarChart } from './Charts';
import './App.css';

// Fix Leaflet default icon issue with webpack
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});


function getDistanceKm(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLng/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

const COLORS = { Easy: '#1D9E75', Moderate: '#BA7517', Competitive: '#D85A30' };

function ratioClass(r) {
  if (r < 1.2) return 'easy';
  if (r < 2.0) return 'moderate';
  return 'competitive';
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
  useEffect(() => {
    if (selected) map.panTo([selected.lat, selected.lng], { animate: true });
  }, [selected, map]);
  useEffect(() => {
    if (homePos) map.panTo(homePos, { animate: true });
  }, [homePos, map]);
  return null;
}

export default function App() {
  const [filters, setFilters] = useState({ zone: 'all', gender: 'all', type: 'all', p2b: 'all', p2c: 'all', search: '' });
  const [radius, setRadius] = useState(1);
  const [homePos, setHomePos] = useState(null);
  const [selected, setSelected] = useState(null);
  const [showExplainer, setShowExplainer] = useState(false);
  const [detailTab, setDetailTab] = useState('trend');
  const [addrLoading, setAddrLoading] = useState(false);
  const listRef = useRef(null);

  const filtered = SCHOOLS.filter(s => {
    if (filters.zone !== 'all' && s.zone !== filters.zone) return false;
    if (filters.gender !== 'all' && s.gender !== filters.gender) return false;
    if (filters.type !== 'all' && !s.types.includes(filters.type)) return false;
    if (filters.p2b !== 'all' && s.p2b !== filters.p2b) return false;
    if (filters.p2c !== 'all' && s.p2c !== filters.p2c) return false;
    if (filters.search && !s.name.toLowerCase().includes(filters.search.toLowerCase())) return false;
    if (homePos && s.lat && s.lng) {
      const dist = getDistanceKm(homePos[0], homePos[1], s.lat, s.lng);
      if (dist > radius) return false;
    }
    return true;
  });

  const filteredNames = new Set(filtered.map(s => s.name));

  const handleSelect = useCallback((school) => {
    setSelected(school);
    setDetailTab('trend');
    // Scroll selected card into view
    setTimeout(() => {
      const el = listRef.current?.querySelector(`[data-name="${school.name}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }, []);

  const setChip = (key, val) => setFilters(f => ({ ...f, [key]: val }));

  const handleAddrKey = async (e) => {
    if (e.key === 'Enter') {
      const input = e.target.value.trim();
      if (!input) { setHomePos(null); return; }
      setAddrLoading(true);
      const pos = await postalToLatLng(input);
      setAddrLoading(false);
      if (pos) {
        setHomePos(pos);
      } else {
        alert('Address not found. Please try a valid Singapore postal code.');
      }
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
          <input className="addr-input" placeholder={addrLoading ? "Locating..." : "Postal code + Enter..."} type="text" onKeyDown={handleAddrKey} disabled={addrLoading} style={addrLoading ? {opacity:0.6} : {}} />
          <div className="radius-btns">
            {[1, 2].map(r => (
              <button key={r} className={`rbtn ${radius === r ? 'on' : ''}`} onClick={() => setRadius(r)}>{r}km</button>
            ))}
          </div>
        </div>

        <div className="results-bar">Showing {filtered.length} of {SCHOOLS.length} schools{homePos ? ` within ${radius}km` : ''}</div>

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

        {/* ── DISCLAIMER ── */}
      <div className="disclaimer">
        Data sourced from MOE Singapore. Balloting ratios updated annually every August. Always verify with <a href="https://www.moe.gov.sg/primary/p1-registration" target="_blank" rel="noreferrer" style={{color:'#1D9E75'}}>MOE directly</a> before making decisions.
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
            <div className="detail-tabs">
              <button className={`dtab ${detailTab==='trend'?'on':''}`} onClick={()=>setDetailTab('trend')}>Trend</button>
              <button className={`dtab ${detailTab==='vibe'?'on':''}`} onClick={()=>setDetailTab('vibe')}>School vibe</button>
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
                  {[['Academic','academic'],['Homework','homework'],['Parent competitiveness','parentComp'],['Teacher quality','teacherQ'],['Culture','culture']].map(([label,key])=>(
                    <div key={key} className="vs-row">
                      <span className="vs-label">{label}</span>
                      <div className="vs-bar-wrap"><div className="vs-bar" style={{width:`${selected.vibe[key]*10}%`, background: selected.vibe[key]>=7.5?'#D85A30':selected.vibe[key]>=6?'#BA7517':'#1D9E75'}} /></div>
                      <span className="vs-val">{selected.vibe[key].toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
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
