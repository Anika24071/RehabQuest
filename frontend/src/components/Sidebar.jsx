import React from 'react';
import { Menu, User, Clock, Activity, Home, Bookmark, Inbox, Star, Settings } from 'lucide-react';
import { useAppContext } from '../AppContext';
import { useNavigate } from 'react-router-dom';

const Sidebar = () => {
  const { isSidebarOpen, toggleSidebar, injuryType, setInjuryType } = useAppContext();
  const navigate = useNavigate();

  if (!isSidebarOpen) return null;

  return (
    <>
      <div className="sidebar-overlay" onClick={toggleSidebar}></div>
      <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h2>Hello Avni !</h2>
          <button onClick={toggleSidebar}>
            <Menu size={24} color="#FFF" />
          </button>
        </div>
        
        <div className="profile-section">
          <div className="profile-avatar">
            <User size={80} color="#0b1a6c" strokeWidth={1.5} />
          </div>
        </div>

        <div className="nav-container">
          <ul className="nav-links">
            <li onClick={() => { navigate('/'); toggleSidebar(); }}><Home size={20} /> Home</li>
            <li><Clock size={20} /> Workouts</li>
            <li><Activity size={20} /> Programmes</li>
            <li><Bookmark size={20} /> Saved Workouts</li>
            <li><Activity size={20} /> Activity</li>
            <li><Inbox size={20} /> Inbox</li>
            <li><Star size={20} /> Challeges</li>
          </ul>

          <div className="injury-profiler">
            <p>Injury Profile:</p>
            <select 
              value={injuryType} 
              onChange={(e) => setInjuryType(e.target.value)}
              className="injury-select"
            >
              <option value="None">General / None</option>
              <option value="Shoulder">Shoulder / Upper Body</option>
              <option value="Wrist">Wrist / Hand</option>
              <option value="Knee">Knee / Lower Body</option>
            </select>
          </div>
          
          <div className="settings-btn">
            <Settings size={20} /> Settings
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
