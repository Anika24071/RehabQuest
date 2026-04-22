import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Home, Dumbbell, LayoutList, Bookmark,
  BarChart2, Inbox, Trophy, Settings, X, User, Heart
} from 'lucide-react';
import { useAppContext } from '../AppContext';

const NAV = [
  { label: 'Home',          icon: Home,        path: '/dashboard' },
  { label: 'Workouts',      icon: Dumbbell,    path: '/workouts' },
  { label: 'Programmes',    icon: LayoutList,  path: '/programmes' },
  { label: 'Saved',         icon: Bookmark,    path: '/saved' },
  { label: 'Activity',      icon: BarChart2,   path: '/activity' },
  { label: 'Inbox',         icon: Inbox,       path: '/inbox' },
  { label: 'Challenges',    icon: Trophy,      path: '/challenges' },
];

const Sidebar = () => {
  const { isSidebarOpen, toggleSidebar, injuryType, setInjuryType } = useAppContext();
  const navigate = useNavigate();
  const location = useLocation();

  const go = (path) => { navigate(path); toggleSidebar(); };

  return (
    <>
      {isSidebarOpen && <div className="sidebar-overlay" onClick={toggleSidebar} />}
      <aside className={`sidebar${isSidebarOpen ? ' open' : ''}`}>
        {/* Header */}
        <div className="sb-header">
          <div className="sb-logo">
            <Heart size={20} fill="#FF5FAD" color="#FF5FAD" />
            <span className="sb-logo-text">RehabQuest</span>
          </div>
          <button className="sb-close" onClick={toggleSidebar}><X size={20} /></button>
        </div>

        {/* Profile */}
        <div className="sb-profile">
          <div className="sb-avatar"><User size={36} strokeWidth={1.5} color="#FF5FAD" /></div>
          <div>
            <p className="sb-name">Hello, Avni! 👋</p>
            <p className="sb-sub">Keep up the great work</p>
          </div>
        </div>

        {/* Nav Links */}
        <nav className="sb-nav">
          {NAV.map(({ label, icon: Icon, path }) => {
            const active = location.pathname === path;
            return (
              <button
                key={path}
                className={`sb-link${active ? ' active' : ''}`}
                onClick={() => go(path)}
              >
                <Icon size={20} />
                <span>{label}</span>
                {active && <div className="sb-active-dot" />}
              </button>
            );
          })}
        </nav>

        {/* Injury Profiler */}
        <div className="sb-injury">
          <p className="sb-injury-label">Injury Profile</p>
          <select
            value={injuryType}
            onChange={e => setInjuryType(e.target.value)}
            className="sb-select"
          >
            <option value="None">General / None</option>
            <option value="Shoulder">Shoulder / Upper Body</option>
            <option value="Wrist">Wrist / Hand</option>
            <option value="Knee">Knee / Lower Body</option>
          </select>
        </div>

        {/* Settings */}
        <button className="sb-settings">
          <Settings size={18} /><span>Settings</span>
        </button>
      </aside>
    </>
  );
};

export default Sidebar;
