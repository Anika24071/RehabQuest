import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ALL_EXERCISES } from './Dashboard';

const PROGRAMMES = [
  {
    id: 'shoulder_prog',
    title: 'Shoulder Recovery Plan',
    desc: 'Designed for shoulder injuries — restore mobility and reduce pain over 2 weeks.',
    icon: '💪', color: '#FFE4F0', border: '#FF5FAD',
    exercises: ['shoulder_raise', 'wrist_rotation'],
    sessions: 6, weeks: 2,
  },
  {
    id: 'knee_prog',
    title: 'Knee Rehab Series',
    desc: 'Focused lower body sessions to rebuild strength and stability after knee injuries.',
    icon: '🦵', color: '#E4F0FF', border: '#3B7EFF',
    exercises: ['leg_raise', 'full_body'],
    sessions: 8, weeks: 3,
  },
  {
    id: 'wrist_prog',
    title: 'Wrist & Hand Mobility',
    desc: 'Gentle wrist rotations and hand exercises to restore range of motion.',
    icon: '🖐️', color: '#F0E4FF', border: '#8B5CF6',
    exercises: ['wrist_rotation'],
    sessions: 4, weeks: 1,
  },
  {
    id: 'full_prog',
    title: 'Full Body Rehab',
    desc: 'A comprehensive programme combining all exercises for full-body conditioning.',
    icon: '🏃', color: '#E4FFF0', border: '#10B981',
    exercises: ['shoulder_raise', 'wrist_rotation', 'leg_raise', 'full_body'],
    sessions: 12, weeks: 4,
  },
];

const Programmes = () => {
  const navigate = useNavigate();

  return (
    <div className="page-wrap">
      <h1 style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:'1.6rem', marginBottom:8 }}>
        Programmes
      </h1>
      <p style={{ color:'var(--text-secondary)', marginBottom:24, fontSize:14 }}>
        Structured injury-specific plans to guide your recovery.
      </p>

      {PROGRAMMES.map(prog => {
        const exList = prog.exercises.map(id => ALL_EXERCISES.find(e => e.id === id)).filter(Boolean);
        return (
          <div key={prog.id} className="prog-card" style={{ borderLeft: `4px solid ${prog.border}` }}>
            <div className="prog-card-header">
              <div className="prog-icon" style={{ background: prog.color }}>
                {prog.icon}
              </div>
              <div>
                <h3>{prog.title}</h3>
                <p>{prog.desc}</p>
                <div style={{ display:'flex', gap:8, marginTop:8 }}>
                  <span className="badge badge-blue">{prog.sessions} sessions</span>
                  <span className="badge badge-purple">{prog.weeks} weeks</span>
                </div>
              </div>
            </div>
            <div className="prog-exercises">
              {exList.map(ex => (
                <div key={ex.id} className="prog-ex-row">
                  <img src={ex.img} alt={ex.title} />
                  <span>{ex.title}</span>
                  <span className="badge badge-green" style={{ marginLeft:'auto' }}>{ex.duration}</span>
                </div>
              ))}
            </div>
            <button
              className="prog-start-btn"
              onClick={() => navigate(`/preworkout/${exList[0].id}`, { state: { workout: exList[0] } })}
            >
              Start Programme →
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default Programmes;
