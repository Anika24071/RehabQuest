import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../AppContext';
import { Bookmark, BookmarkCheck, Play } from 'lucide-react';
import { ALL_EXERCISES } from './Dashboard';

const CATEGORIES = ['All', 'Upper Body', 'Lower Body', 'Full Body'];

const categoryMap = {
  'Shoulder': 'Upper Body',
  'Wrist': 'Upper Body',
  'Knee': 'Lower Body',
  'None': 'Full Body',
};

const diffColor = { Beginner:'badge-green', Intermediate:'badge-orange', Advanced:'badge-pink' };

const Workouts = () => {
  const navigate = useNavigate();
  const { savedWorkouts, toggleSave } = useAppContext();
  const [active, setActive] = useState('All');

  const filtered = ALL_EXERCISES.filter(ex => {
    if (active === 'All') return true;
    return categoryMap[ex.type] === active;
  });

  const go = (ex) => navigate(`/preworkout/${ex.id}`, { state: { workout: ex } });

  return (
    <div className="page-wrap">
      <h1 style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:'1.6rem', marginBottom:20 }}>
        All Workouts
      </h1>

      <div className="filter-row">
        {CATEGORIES.map(c => (
          <button key={c} className={`filter-chip${active === c ? ' active' : ''}`} onClick={() => setActive(c)}>
            {c}
          </button>
        ))}
      </div>

      <div className="workouts-grid">
        {filtered.map(ex => {
          const saved = savedWorkouts.includes(ex.id);
          return (
            <div key={ex.id} className="workout-card">
              <img src={ex.img} alt={ex.title} className="workout-card-img" />
              <div className="workout-card-body">
                <h3>{ex.title}</h3>
                <div className="workout-card-meta">
                  <span className={`badge ${diffColor[ex.difficulty]}`}>{ex.difficulty}</span>
                  <span className="badge badge-blue">{ex.duration}</span>
                  <span className="badge badge-purple">{categoryMap[ex.type]}</span>
                </div>
                <div style={{ display:'flex', gap:8 }}>
                  <button className="workout-start-btn" style={{ flex:1 }} onClick={() => go(ex)}>
                    <Play size={14} style={{ display:'inline', marginRight:4 }} /> Start
                  </button>
                  <button
                    className={`save-btn ${saved ? 'saved' : 'unsaved'}`}
                    onClick={() => toggleSave(ex.id)}
                  >
                    {saved ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Workouts;
