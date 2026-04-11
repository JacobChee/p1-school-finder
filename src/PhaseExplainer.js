import { useState } from 'react';
import './PhaseExplainer.css';

const SECTIONS = [
  {
    tag: 'What the ratio means',
    tagStyle: { background: '#F1EFE8', color: '#444441' },
    name: 'How to read the numbers',
    body: `RATIO`,
  },
  {
    tag: 'School vibe',
    tagStyle: { background: '#EAF3DE', color: '#27500A' },
    name: 'What the radar chart shows',
    body: `VIBE`,
  },
  {
    tag: 'Phase 1',
    tagStyle: { background: '#E6F1FB', color: '#0C447C' },
    name: 'Sibling in school',
    body: `P1`,
  },
  {
    tag: 'Phase 2A',
    tagStyle: { background: '#EAF3DE', color: '#27500A' },
    name: 'Alumni & staff',
    body: `P2A`,
  },
  {
    tag: 'Phase 2B',
    tagStyle: { background: '#FAEEDA', color: '#633806' },
    name: 'Volunteers & community',
    body: `P2B`,
  },
  {
    tag: 'Phase 2C',
    tagStyle: { background: '#FBEAF0', color: '#72243E' },
    name: 'Open to everyone',
    body: `P2C`,
  },
  {
    tag: '2C Supp',
    tagStyle: { background: '#F1EFE8', color: '#444441' },
    name: 'Last resort',
    body: `SUPP`,
  },
];

const BODIES = {
  RATIO: ({ }) => (
    <>
      <p>The ratio = <strong>applicants divided by vacancies</strong>. A ratio of 3.15 means 3 parents compete for every 1 spot.</p>
      <div style={{ display:'flex', flexDirection:'column', gap:6, marginTop:10 }}>
        <div className="tip tip-green"><strong>Below 1.0</strong> — more spots than applicants. No ballot needed.</div>
        <div className="tip tip-blue"><strong>1.0 – 1.9</strong> — slightly oversubscribed. Ballot likely but odds are ok.</div>
        <div className="tip" style={{background:'#FAEEDA',color:'#633806',padding:'8px 10px',borderRadius:8,fontSize:11,lineHeight:1.5}}><strong>2.0 – 2.9</strong> — competitive. Roughly 1 in 2–3 chance.</div>
        <div className="tip tip-red"><strong>3.0 and above</strong> — highly competitive. Less than 1 in 3 chance. Distance from school becomes crucial.</div>
      </div>
      <div className="tip tip-red" style={{marginTop:8}}><strong>PV ballot required</strong> — even parent volunteers must ballot. Volunteering 40 hours does not guarantee entry at these schools.</div>
    </>
  ),
  VIBE: ({ }) => (
    <>
      <p>Vibe scores are estimated from parent forum discussions on KiasuParents, Reddit, and community sources. Not official MOE data.</p>
      <div style={{ display:'flex', flexDirection:'column', gap:6, marginTop:10 }}>
        <div className="tip tip-blue"><strong>Academic pressure</strong> — how exam-focused the school culture feels</div>
        <div className="tip tip-blue"><strong>Homework load</strong> — amount of work sent home daily</div>
        <div className="tip tip-blue"><strong>Parent competitiveness</strong> — how kiasu the parent community is perceived to be</div>
        <div className="tip tip-blue"><strong>Teacher quality</strong> — responsiveness and teaching quality as reported by parents</div>
        <div className="tip tip-blue"><strong>School culture</strong> — warmth, inclusivity, and community feel</div>
      </div>
      <div className="tip" style={{background:'#F1EFE8',color:'#5f5e5a',marginTop:8,padding:'8px 10px',borderRadius:8,fontSize:11,lineHeight:1.5}}>Always visit the school and speak to current parents before deciding. Scores may not reflect current experience.</div>
    </>
  ),
  P1: ({ }) => (
    <>
      <p>Your child has an older sibling already enrolled at the same school. Almost guaranteed entry — schools rarely ballot at this phase.</p>
      <div className="tip tip-blue" style={{marginTop:8}}>Your second child can almost always follow your first into the same school, regardless of distance or competition.</div>
    </>
  ),
  P2A: ({ }) => (
    <>
      <p><strong>2A(1)</strong> — Parent is on the school's management or advisory committee, or is a staff member of the school or its MOE Kindergarten.</p>
      <p style={{marginTop:8}}><strong>2A(2)</strong> — Parent attended the primary school as a child and is a registered alumni member for at least 1 year before registration opens.</p>
      <div className="tip tip-green" style={{marginTop:10}}>Attending the secondary school does not count. Must be the primary school itself.</div>
    </>
  ),
  P2B: ({ }) => (
    <>
      <p>Three ways to qualify:</p>
      <ul style={{margin:'8px 0 0 16px',lineHeight:1.7}}>
        <li><strong>Parent volunteer</strong> — join by July 1, complete 40 hrs of service by June 30 the year before registration</li>
        <li><strong>Church or clan group</strong> — active member of a group affiliated with the school</li>
        <li><strong>Grassroots leader</strong> — endorsed by People's Association</li>
      </ul>
      <div className="tip tip-red" style={{marginTop:10}}>At popular schools even parent volunteers must ballot. A ratio of 3.15 means 3 volunteers compete for every 1 spot.</div>
    </>
  ),
  P2C: ({ }) => (
    <>
      <p>No criteria needed. Priority is purely by distance from home to school:</p>
      <ol style={{margin:'8px 0 0 16px',lineHeight:1.8,fontSize:12}}>
        <li>Singapore Citizens within 1km</li>
        <li>Singapore Citizens 1–2km</li>
        <li>Singapore Citizens beyond 2km</li>
        <li>PRs within 1km</li>
        <li>PRs 1–2km</li>
        <li>PRs beyond 2km</li>
      </ol>
      <div className="tip tip-pink" style={{marginTop:10}}>Living closer is your only lever here. Use the 1km/2km radius ring to check if you fall within the priority zone.</div>
    </>
  ),
  SUPP: ({ }) => (
    <p>For children still unregistered after Phase 2C. Only schools with remaining vacancies are available. If unsuccessful here, MOE assigns your child to a school — no appeals accepted.</p>
  ),
};

export default function PhaseExplainer({ onClose }) {
  const [open, setOpen] = useState(0);

  return (
    <div className="explainer">
      <div className="exp-header">
        <span className="exp-title">Guide & phase explainer</span>
        <button className="exp-close" onClick={onClose}>✕</button>
      </div>
      <div className="exp-phases">
        {SECTIONS.map((p, i) => {
          const Body = BODIES[p.body];
          return (
            <div key={i} className="phase-item">
              <div className="phase-hdr" onClick={() => setOpen(open === i ? null : i)}>
                <span className="phase-tag" style={p.tagStyle}>{p.tag}</span>
                <span className="phase-name">{p.name}</span>
                <span className={`phase-chev ${open === i ? 'open' : ''}`}>›</span>
              </div>
              {open === i && <div className="phase-body"><Body /></div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
