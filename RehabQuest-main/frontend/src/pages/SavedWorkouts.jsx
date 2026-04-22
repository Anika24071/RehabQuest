import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../AppContext';
import { BookmarkX, Play } from 'lucide-react';
import { ALL_EXERCISES } from './Dashboard';

const SavedWorkouts = () => {
  const navigate = useNavigate();
  const { savedWorkouts, toggleSave } = useAppContext();

  const saved = ALL_EXERCISES.filter(ex => savedWorkouts.includes(ex.id));

  if (saved.length === 0) {
    return (
      <div className="page-wrap">
        <h1 style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:'1.6rem', marginBottom:24 }}>Saved Workouts</h1>
        <div className="empty-state">
          <div className="empty-state-icon">🔖</div>
          <h3>No saved workouts yet</h3>
          <p>Bookmark workouts from the Workouts page to find them here quickly.</p>
        </div>
      </div>
    );
  }

  const go = (ex) => navigate(`/preworkout/${ex.id}`, { state: { workout: ex } });

  return (
    <div className="page-wrap">
      <h1 style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:'1.6rem', marginBottom:8 }}>
        Saved Workouts
      </h1>
      <p style={{ color:'var(--text-secondary)', marginBottom:24, fontSize:14 }}>
        {saved.length} workout{saved.length !== 1 ? 's' : ''} saved
      </p>
      <div className="workouts-grid">
        {saved.map(ex => (
          <div key={ex.id} className="workout-card">
            <img src={ex.img} alt={ex.title} className="workout-card-img" />
            <div className="workout-card-body">
              <h3>{ex.title}</h3>
              <div className="workout-card-meta">
                <span className="badge badge-blue">{ex.duration}</span>
                <span className="badge badge-green">{ex.difficulty}</span>
              </div>
              <div style={{ display:'flex', gap:8 }}>
                <button className="workout-start-btn" style={{ flex:1 }} onClick={() => go(ex)}>
                  <Play size={14} style={{ display:'inline', marginRight:4 }} /> Start
                </button>
                <button className="save-btn saved" onClick={() => toggleSave(ex.id)} title="Remove">
                  <BookmarkX size={16} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SavedWorkouts;
