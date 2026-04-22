import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const PreWorkout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const workout = location.state?.workout || { 
    id: "full_body",
    title: "Full Body Complete Session",
    duration: "20 mins",
    difficulty: "Advanced",
    img: "/full_body_1776543319773.png",
    type: "None"
  };

  const getBullets = (id) => {
    switch(id) {
      case 'shoulder_raise': return ["Overhead reaches x15", "Controlled descent", "Posture checking"];
      case 'wrist_rotation': return ["360 degree slow rotations", "Direction switches", "Full mobility extension"];
      case 'leg_raise': return ["High knee raise x10/leg", "Balance hold for 3s", "Core stabilization"];
      default: return ["Standing on one leg", "Walking heel-to-toe", "Balance board exercises"];
    }
  }

  const bullets = getBullets(workout.id);

  return (
    <div className="preworkout-container">
      <div className="pre-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
           <ArrowLeft size={28} color="#FF66B2" />
        </button>
      </div>

      <div className="pre-content">
        <div className="pre-hero">
          <img src={workout.img} className="hero-bg" alt="Hero background" />
          <div className="hero-content">
            <h1 className="hero-duration">{workout.duration}:</h1>
            <h1 className="hero-title">{workout.title}</h1>

            <div className="detail-card">
              <h3>{workout.difficulty}</h3>
              <p className="detail-sub">{workout.type === 'None' ? 'Full routine to prevent falls and improve stability' : `${workout.type} focused mobility set`}</p>
              
              <div className="detail-bullets">
                <p><strong>Breakdown:</strong></p>
                <ul>
                  {bullets.map((b, i) => <li key={i}>{b}</li>)}
                </ul>
              </div>
            </div>

            <button className="start-btn" onClick={() => navigate(`/session/${workout.id}`, { state: { workout } })}>
              Start Workout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PreWorkout;
