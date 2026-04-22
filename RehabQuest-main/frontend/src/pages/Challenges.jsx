import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trophy } from 'lucide-react';

const CHALLENGES = [
  {
    id:'c1', title:'7-Day Consistency', badge:'🏆',
    desc:'Complete at least one session every day for 7 days.',
    progress:3, total:7, bgColor:'#12216A', textColor:'white',
    startId:'full_body',
  },
  {
    id:'c2', title:'Shoulder Warrior', badge:'💪',
    desc:'Complete the shoulder raise exercise 5 times.',
    progress:2, total:5, bgColor:'#FF5FAD', textColor:'white',
    startId:'shoulder_raise',
  },
  {
    id:'c3', title:'Wrist Master', badge:'🖐️',
    desc:'Complete 3 wrist rotation sessions in a week.',
    progress:1, total:3, bgColor:'#8B5CF6', textColor:'white',
    startId:'wrist_rotation',
  },
  {
    id:'c4', title:'Full Body Champion', badge:'🏃',
    desc:'Finish 2 full body sessions back to back.',
    progress:0, total:2, bgColor:'#10B981', textColor:'white',
    startId:'full_body',
  },
];

const Challenges = () => {
  const navigate = useNavigate();
  const [challenges] = useState(CHALLENGES);

  return (
    <div className="page-wrap">
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8 }}>
        <Trophy size={28} color="var(--pink)" />
        <h1 style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:'1.6rem' }}>Challenges</h1>
      </div>
      <p style={{ color:'var(--text-secondary)', marginBottom:28, fontSize:14 }}>
        Complete challenges to earn badges and push your recovery forward.
      </p>

      <div className="challenges-grid">
        {challenges.map(ch => {
          const pct = Math.round((ch.progress / ch.total) * 100);
          const done = ch.progress >= ch.total;
          return (
            <div
              key={ch.id}
              className="challenge-card"
              style={{ background: ch.bgColor, color: ch.textColor, opacity: done ? 0.85 : 1 }}
            >
              <span className="challenge-badge">{done ? '✅' : ch.badge}</span>
              <h3>{ch.title}</h3>
              <p>{ch.desc}</p>
              <div className="challenge-prog-label">
                <span>Progress</span>
                <span>{ch.progress}/{ch.total} {done ? '🎉 Complete!' : ''}</span>
              </div>
              <div style={{ background:'rgba(255,255,255,0.2)', borderRadius:99, height:8, overflow:'hidden' }}>
                <div style={{ height:'100%', width:`${pct}%`, background:'rgba(255,255,255,0.8)', borderRadius:99, transition:'width 1s ease' }} />
              </div>
              {!done && (
                <button
                  className="challenge-start-btn"
                  style={{ background:'rgba(255,255,255,0.2)', color: ch.textColor, border:'2px solid rgba(255,255,255,0.4)' }}
                  onClick={() => {
                    const ex = { id: ch.startId, title: ch.title, duration:'10 mins' };
                    navigate(`/preworkout/${ch.startId}`, { state: { workout: ex } });
                  }}
                >
                  Continue →
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Challenges;
