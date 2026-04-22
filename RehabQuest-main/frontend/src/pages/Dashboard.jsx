import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../AppContext';
import { Zap, ChevronRight } from 'lucide-react';

const ALL_EXERCISES = [
  { id:'shoulder_raise', title:'Shoulder/Hand Raise', type:'Shoulder', img:'/shoulder_raise_1776543143345.png', duration:'5 mins', difficulty:'Beginner' },
  { id:'wrist_rotation', title:'Wrist 360 Rotation', type:'Wrist', img:'/wrist_rotation_1776543209412.png', duration:'5 mins', difficulty:'Intermediate' },
  { id:'leg_raise', title:'High Knee Leg Raises', type:'Knee', img:'/leg_raise_1776543225072.png', duration:'8 mins', difficulty:'Beginner' },
  { id:'full_body', title:'Full Body Session', type:'None', img:'/full_body_1776543319773.png', duration:'20 mins', difficulty:'Advanced' },
];

export { ALL_EXERCISES };

const Dashboard = () => {
  const navigate = useNavigate();
  const { injuryType, completedSessions } = useAppContext();

  const recommended = ALL_EXERCISES.filter(ex =>
    injuryType === 'None' || ex.type === injuryType || ex.type === 'None'
  );

  const diffColor = { Beginner:'badge-green', Intermediate:'badge-orange', Advanced:'badge-pink' };

  const go = (ex) => navigate(`/preworkout/${ex.id}`, { state: { workout: ex } });

  return (
    <div className="dashboard">
      {/* Hero Banner */}
      <div className="dash-hero">
        <p className="dash-greeting">Tuesday, April 22</p>
        <h1>Hello, Avni! 💪</h1>
        <p>Ready to continue your recovery journey? You're doing amazing.</p>
        <button className="dash-quick-btn" onClick={() => go(recommended[0])}>
          <Zap size={18} /> Quick Start
        </button>
        <div className="dash-stats">
          <div className="dash-stat">
            <div className="dash-stat-num">{completedSessions.length}</div>
            <div className="dash-stat-label">Sessions Done</div>
          </div>
          <div className="dash-stat">
            <div className="dash-stat-num">3</div>
            <div className="dash-stat-label">Day Streak 🔥</div>
          </div>
          <div className="dash-stat">
            <div className="dash-stat-num">18m</div>
            <div className="dash-stat-label">This Week</div>
          </div>
        </div>
      </div>

      {/* Recommended */}
      <div style={{ display:'flex', alignItems:'center' }}>
        <h2 className="section-title" style={{marginTop:0}}>Recommended</h2>
        <span className="section-link" onClick={() => navigate('/workouts')}>See all</span>
      </div>
      <div className="h-scroll">
        {recommended.map(ex => (
          <div key={ex.id} className="ex-card" onClick={() => go(ex)}>
            <img src={ex.img} alt={ex.title} />
            <div className="ex-card-overlay">
              <div className="ex-card-title">{ex.title}</div>
              <div className="ex-card-badges">
                <span className={`badge ${diffColor[ex.difficulty]}`}>{ex.difficulty}</span>
                <span className="badge badge-blue">{ex.duration}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent */}
      <h2 className="section-title">Recent Workouts</h2>
      <div className="recent-list">
        {completedSessions.slice(0,3).map((s, i) => {
          const ex = ALL_EXERCISES.find(e => e.id === s.id) || ALL_EXERCISES[0];
          return (
            <div key={i} className="recent-card" onClick={() => go(ex)}>
              <img src={ex.img} alt={ex.title} className="recent-thumb" />
              <div className="recent-info">
                <h3>{s.title}</h3>
                <p>{s.date} · {ex.type === 'None' ? 'Full Body' : `${ex.type} Focus`}</p>
              </div>
              <span className="recent-time">{s.duration}</span>
              <ChevronRight size={18} color="var(--text-muted)" />
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Dashboard;
