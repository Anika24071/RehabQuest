import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const ActiveSession = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const workout = location.state?.workout || { id: 'full_body', duration: '20 mins', title: 'Full Body Session' };
  const [time, setTime] = useState(14 * 60 + 56); 
  const [streamActive, setStreamActive] = useState(false);
  const [streamUrl] = useState(`http://localhost:8000/video_feed?t=${Date.now()}`);
  const streamStarted = useRef(false);

  useEffect(() => {
    // Only call start_stream exactly ONCE per mount to avoid hardware camera collisions
    if (!streamStarted.current) {
        streamStarted.current = true;
        fetch(`http://localhost:8000/start_stream?exercise=${workout.id}`)
          .then(() => setStreamActive(true))
          .catch(err => console.error(err));
    }

    const interval = setInterval(() => {
      setTime(prev => prev > 0 ? prev - 1 : 0);
    }, 1000);

    const handleKeyDown = (e) => {
      // Send valid single character keys to Backend OpenCV running thread
      if (e.key.length === 1 || e.key === ' ') {
         const keyTarget = e.key === ' ' ? ' ' : e.key;
         fetch(`http://localhost:8000/send_key?key=${encodeURIComponent(keyTarget)}`)
            .catch(err => console.error("Could not send keystroke", err));
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    
    return () => {
       clearInterval(interval);
       window.removeEventListener('keydown', handleKeyDown);
    };
  }, [workout.id]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const skipWorkout = async () => {
    await fetch(`http://localhost:8000/stop_stream`).catch(e => console.log(e));
    navigate(-1);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(err => {
        console.log("Error attempting to enable fullscreen:", err);
      });
    } else {
      document.exitFullscreen();
    }
  };

  return (
    <div className="active-session-container">
      <div className="session-header">
        <button className="back-arrow-btn" onClick={skipWorkout}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="session-title-area">
          <h1>{workout.duration}:</h1>
          <h2>{workout.title}</h2>
        </div>
        <div className="session-timer">
          <span>{formatTime(time)}</span> <span className="ms">43</span>
        </div>
      </div>

      <div className="video-viewport">
        {streamActive ? (
          <img 
            src={streamUrl} 
            alt="Live Stream" 
            style={{width: '100%', height:'100%', objectFit: 'contain', background: '#000'}}
          />
        ) : (
           <div style={{width:'100%', height:'100%', background:'#111', display:'flex', alignItems:'center', justifyContent:'center', color:'#ff66b2', fontWeight:'bold', fontSize:'1.4rem'}}>
              Loading Camera feed... 
           </div>
        )}

        <div className="video-placeholder" style={{position:'absolute', inset:0, pointerEvents:'none', background:'none'}}>
          <button className="next-rest-btn" style={{pointerEvents:'auto'}} onClick={skipWorkout}>
             <div className="next-label">END <span className="arrow">›</span></div>
             <div className="rest-clock">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#222" strokeWidth="1.5">
                   <circle cx="12" cy="12" r="10"></circle>
                   <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
             </div>
             <div className="rest-text">Quit</div>
          </button>
          
          <button className="fullscreen-btn" style={{pointerEvents:'auto'}} onClick={toggleFullscreen}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ActiveSession;
