import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppContext } from '../AppContext';

const ActiveSession = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { addCompleted } = useAppContext();
  const workout = location.state?.workout || { id:'full_body', duration:'20 mins', title:'Full Body Session' };

  // Timer starts IMMEDIATELY — decoupled from camera
  const [time, setTime] = useState(0);
  const [cameraReady, setCameraReady] = useState(false);
  const streamStarted = useRef(false);
  const startTime = useRef(Date.now());

  const streamUrl = useRef(`http://localhost:8000/video_feed?t=${Date.now()}`).current;

  // Auto-dismiss the spinner after 2.5s — camera may already be showing frames
  useEffect(() => {
    const timer = setTimeout(() => setCameraReady(true), 2500);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    // Fire-and-forget: start stream in background, don't wait for it
    if (!streamStarted.current) {
      streamStarted.current = true;
      fetch(`http://localhost:8000/start_stream?exercise=${workout.id}`)
        .catch(err => console.warn('Backend not available:', err));
    }

    // Timer: purely JS-based, starts immediately
    const interval = setInterval(() => {
      setTime(Math.floor((Date.now() - startTime.current) / 1000));
    }, 500);

    // Key forwarding
    const handleKeyDown = (e) => {
      const key = e.key === ' ' ? ' ' : e.key;
      if (key.length === 1) {
        fetch(`http://localhost:8000/send_key?key=${encodeURIComponent(key)}`).catch(() => {});
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearInterval(interval);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [workout.id]);

  const formatTime = (s) => {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  };

  const endSession = async () => {
    await fetch('http://localhost:8000/stop_stream').catch(() => {});
    addCompleted({
      id: workout.id,
      title: workout.title,
      date: new Date().toISOString().slice(0, 10),
      duration: `${Math.floor(time / 60)}m ${time % 60}s`,
    });
    navigate('/dashboard');
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  };

  return (
    <div className="active-session-container">
      <div className="session-header">
        <button className="back-arrow-btn" onClick={endSession}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="session-title-area">
          <h2>{workout.title}</h2>
        </div>
        <div className="session-timer">
          <span>{formatTime(time)}</span>
        </div>
      </div>

      <div className="video-viewport">
        {/* Camera overlay — fades out when stream connects */}
        <div className={`camera-init-overlay${cameraReady ? ' hidden' : ''}`}>
          <div className="camera-spinner" />
          <span className="camera-init-text">Starting camera…</span>
        </div>

        {/* Stream — always mounted to start loading immediately */}
        <img
          src={streamUrl}
          alt="Live exercise stream"
          onLoad={() => setCameraReady(true)}
          onError={() => setCameraReady(false)}
          style={{ width:'100%', height:'100%', objectFit:'contain', background:'#000', display:'block' }}
        />

        <button className="fullscreen-btn" onClick={toggleFullscreen}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
          </svg>
        </button>

        <button className="end-btn" onClick={endSession}>
          End Session
        </button>
      </div>
    </div>
  );
};

export default ActiveSession;
