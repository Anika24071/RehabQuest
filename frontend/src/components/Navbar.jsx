import React from 'react';
import { Menu, User } from 'lucide-react';
import { useAppContext } from '../AppContext';
import { useNavigate } from 'react-router-dom';

const Navbar = () => {
  const { toggleSidebar } = useAppContext();
  const navigate = useNavigate();

  return (
    <nav className="navbar">
      <button className="menu-btn" onClick={toggleSidebar}>
        <Menu size={28} color="#FF66B2" />
      </button>
      
      <div className="logo" onClick={() => navigate('/')}>
        <span className="logo-icon">*</span>
        <div className="logo-text">
          <span className="logo-rehab">REHAB</span>
          <br/>
          <span className="logo-quest">QUEST</span>
        </div>
      </div>
      
      <button className="profile-btn">
        <User size={28} color="#FF66B2" />
      </button>
    </nav>
  );
};

export default Navbar;
