import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Menu, Bell, Heart } from 'lucide-react';
import { useAppContext } from '../AppContext';

const Navbar = () => {
  const { toggleSidebar } = useAppContext();
  const navigate = useNavigate();
  const location = useLocation();

  const titles = {
    '/dashboard': 'Home',
    '/workouts': 'Workouts',
    '/programmes': 'Programmes',
    '/saved': 'Saved',
    '/activity': 'Activity',
    '/inbox': 'Inbox',
    '/challenges': 'Challenges',
  };

  const title = titles[location.pathname] || 'RehabQuest';

  return (
    <header className="navbar">
      <button className="nav-menu-btn" onClick={toggleSidebar} id="sidebar-toggle">
        <Menu size={24} />
      </button>
      <div className="nav-logo" onClick={() => navigate('/dashboard')}>
        <Heart size={18} fill="#FF5FAD" color="#FF5FAD" style={{flexShrink:0}} />
        <span className="nav-logo-rehab">REHAB</span>
        <span className="nav-logo-quest">QUEST</span>
      </div>
      <button className="nav-bell" onClick={() => navigate('/inbox')}>
        <Bell size={22} />
        <span className="bell-dot" />
      </button>
    </header>
  );
};

export default Navbar;
