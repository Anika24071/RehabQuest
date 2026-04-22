import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../AppContext';
import { ChevronRight } from 'lucide-react';

const Dashboard = () => {
  const navigate = useNavigate();
  const { injuryType } = useAppContext();

  // Use the exact generated assets mapping to the exercise files
  const recommendedData = [
    { id: 'shoulder_raise', title: 'Shoulder/Hand Raise', type: 'Shoulder', img: '/shoulder_raise_1776543143345.png', script: 'Rehab_Hand_Raise.py', duration: '5 mins', difficulty: 'Beginner' },
    { id: 'wrist_rotation', title: 'Wrist 360 Rotation', type: 'Wrist', img: '/wrist_rotation_1776543209412.png', script: 'Rehab_Wrist_Exercise.py', duration: '5 mins', difficulty: 'Intermediate' },
    { id: 'leg_raise', title: 'High Knee Leg Raises', type: 'Knee', img: '/leg_raise_1776543225072.png', script: 'Rehab_Leg_Raise.py', duration: '8 mins', difficulty: 'Beginner' },
    { id: 'full_body', title: 'Full Body Complete Session', type: 'None', img: '/full_body_1776543319773.png', script: 'Rehab_Quest_Session_v2.py', duration: '20 mins', difficulty: 'Advanced' },
  ];

  const filteredRecommended = recommendedData.filter(ex => 
    injuryType === 'None' || ex.type === injuryType || ex.type === 'None'
  );

  const startWorkout = (workout) => {
    navigate(`/preworkout/${workout.id}`, { state: { workout } });
  };

  return (
    <div className="dashboard">
      <h2 className="section-title">Recommended Exercises</h2>
      <div className="horizontal-scroll">
        {filteredRecommended.map((ex, idx) => (
          <div key={idx} className="card large-card" onClick={() => startWorkout(ex)}>
            <img src={ex.img} className="card-bg" alt={ex.title} />
            <div className="card-overlay">
              <h3>{ex.title}</h3>
              <ChevronRight size={28} color="#4285F4" className="nav-arrow" />
            </div>
          </div>
        ))}
      </div>

      <h2 className="section-title recent-title">
        <img src="https://cdn-icons-png.flaticon.com/512/3207/3207869.png" style={{width:'24px', marginRight:'8px'}} alt="shoe"/> 
        Recent Workouts
      </h2>
      <div className="recent-list">
        {recommendedData.slice(0, 2).map((ex, idx) => (
          <div key={`recent-${idx}`} className="recent-card">
            <div className="recent-info">
              <img src={ex.img} alt="thumb" />
              <div>
                <h3>{ex.title}</h3>
                <p>{ex.difficulty}<br/>{ex.type === 'None' ? 'Full Body Regimen' : `${ex.type} Mobility Focus`}</p>
              </div>
            </div>
            <span className="time">{ex.duration}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;
