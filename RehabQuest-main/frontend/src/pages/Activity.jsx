import React from 'react';
import { useAppContext } from '../AppContext';
import { Check } from 'lucide-react';

const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
const DONE = [true, true, true, false, false, false, false];

const Activity = () => {
  const { completedSessions } = useAppContext();
  const totalMins = completedSessions.length * 7;
  const completion = Math.min(Math.round((completedSessions.length / 10) * 100), 100);

  return (
    <div className="page-wrap">
      <h1 style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:'1.6rem', marginBottom:24 }}>
        Activity
      </h1>

      {/* Stats Grid */}
      <div className="activity-stats">
        {[
          { icon:'🏅', num: completedSessions.length, label:'Sessions Done' },
          { icon:'🔥', num: 3, label:'Day Streak' },
          { icon:'⏱️', num: `${totalMins}m`, label:'Total Time' },
          { icon:'📈', num: `${completion}%`, label:'Goal Progress' },
        ].map(s => (
          <div key={s.label} className="activity-stat-card">
            <div className="activity-stat-icon">{s.icon}</div>
            <div className="activity-stat-num">{s.num}</div>
            <div className="activity-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Weekly Streak */}
      <h2 className="section-title" style={{ marginTop:0 }}>This Week</h2>
      <div style={{ background:'white', borderRadius:20, padding:20, marginBottom:24, boxShadow:'var(--shadow-sm)' }}>
        <div style={{ display:'flex', gap:8, marginBottom:12 }}>
          {DAYS.map((d, i) => (
            <div key={i} style={{ flex:1, textAlign:'center' }}>
              <div style={{ fontSize:12, color:'var(--text-muted)', marginBottom:6, fontWeight:600 }}>{d}</div>
              <div style={{ height:36, width:36, borderRadius:10, margin:'0 auto', background: DONE[i] ? 'var(--grad-pink)' : 'rgba(18,33,106,0.08)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                {DONE[i] && <Check size={16} color="white" strokeWidth={3} />}
              </div>
            </div>
          ))}
        </div>
        <div className="progress-bar-wrap">
          <div className="progress-bar-fill" style={{ width:`${completion}%` }} />
        </div>
        <p style={{ marginTop:8, fontSize:13, color:'var(--text-secondary)', textAlign:'right' }}>
          Weekly goal: {completion}% complete
        </p>
      </div>

      {/* History */}
      <h2 className="section-title" style={{ marginTop:0 }}>Session History</h2>
      {completedSessions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <h3>No sessions yet</h3>
          <p>Complete a workout to see your history here.</p>
        </div>
      ) : (
        completedSessions.map((s, i) => (
          <div key={i} className="history-item">
            <div className="history-dot" />
            <div className="history-info">
              <h4>{s.title}</h4>
              <p>{s.date}</p>
            </div>
            <span className="history-dur">{s.duration}</span>
          </div>
        ))
      )}
    </div>
  );
};

export default Activity;
