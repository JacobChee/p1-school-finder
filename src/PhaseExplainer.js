import { useState } from 'react';
import './PhaseExplainer.css';

const PHASES = [
  {
    tag: 'Phase 1',
    tagStyle: { background: '#E6F1FB', color: '#0C447C' },
    name: 'Sibling in school',
    body: (
      <>
        <p>Your child has an older sibling already enrolled at the same school. Almost guaranteed entry — schools rarely ballot at this phase.</p>
        <div className="tip tip-blue">Your second child can almost always follow your first into the same school, regardless of distance or competition.</div>
      </>
    ),
  },
  {
    tag: 'Phase 2A',
    tagStyle: { background: '#EAF3DE', color: '#27500A' },
    name: 'Alumni & staff',
    body: (
      <>
        <p><strong>2A(1)</strong> — Parent is on the school's management or advisory committee, or is a staff member of the school or its MOE Kindergarten.</p>
        <p style={{ marginTop: 8 }}><strong>2A(2)</strong> — Parent attended the primary school as a child and is a registered alumni member for at least 1 year before registration opens.</p>
        <div className="tip tip-green" style={{ marginTop: 10 }}>Attending the secondary school doesn't count. Must be the primary school itself.</div>
      </>
    ),
  },
  {
    tag: 'Phase 2B',
    tagStyle: { background: '#FAEEDA', color: '#633806' },
    name: 'Volunteers & community',
    body: (
      <>
        <p>Three ways to qualify:</p>
        <ul style={{ margin: '8px 0 0 16px', lineHeight: 1.7 }}>
          <li><strong>Parent volunteer</strong> — join by July 1, complete 40 hrs of service by June 30 the year before registration</li>
          <li><strong>Church or clan group</strong> — parent is active member of a group affiliated with the school</li>
          <li><strong>Grassroots leader</strong> — endorsed by People's Association</li>
        </ul>
        <div className="tip tip-red" style={{ marginTop: 10 }}>
          At popular schools, even parent volunteers must ballot. A ratio of 3.15 means 3 volunteers compete for every 1 spot. The <em>PV ballot required</em> flag warns you of this.
        </div>
      </>
    ),
  },
  {
    tag: 'Phase 2C',
    tagStyle: { background: '#FBEAF0', color: '#72243E' },
    name: 'Open to everyone',
    body: (
      <>
        <p>No criteria needed. Priority is determined purely by distance from home to school:</p>
        <ol style={{ margin: '8px 0 0 16px', lineHeight: 1.8, fontSize: 12 }}>
          <li>Singapore Citizens within 1km</li>
          <li>Singapore Citizens 1–2km</li>
          <li>Singapore Citizens beyond 2km</li>
          <li>PRs within 1km</li>
          <li>PRs 1–2km</li>
          <li>PRs beyond 2km</li>
        </ol>
        <div className="tip tip-pink" style={{ marginTop: 10 }}>
          Living closer is your only lever here. Use the 1km/2km radius ring to check if you fall within the priority zone.
        </div>
      </>
    ),
  },
  {
    tag: '2C Supp',
    tagStyle: { background: '#F1EFE8', color: '#444441' },
    name: 'Last resort',
    body: (
      <>
        <p>For children still unregistered after Phase 2C. Only schools with remaining vacancies are available. If unsuccessful here, MOE assigns your child to a school — no appeals accepted.</p>
      </>
    ),
  },
];

export default function PhaseExplainer({ onClose }) {
  const [open, setOpen] = useState(null);

  return (
    <div className="explainer">
      <div className="exp-header">
        <span className="exp-title">How P1 phases work</span>
        <button className="exp-close" onClick={onClose}>✕</button>
      </div>
      <div className="exp-phases">
        {PHASES.map((p, i) => (
          <div key={i} className="phase-item">
            <div className="phase-hdr" onClick={() => setOpen(open === i ? null : i)}>
              <span className="phase-tag" style={p.tagStyle}>{p.tag}</span>
              <span className="phase-name">{p.name}</span>
              <span className={`phase-chev ${open === i ? 'open' : ''}`}>›</span>
            </div>
            {open === i && <div className="phase-body">{p.body}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
