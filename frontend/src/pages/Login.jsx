import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail } from 'lucide-react';

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
    if (email && password) {
      navigate('/dashboard');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <span className="logo-icon">*</span>
          <div className="logo-text" style={{textAlign:'center'}}>
            <span className="logo-rehab">REHAB</span><br/>
            <span className="logo-quest">QUEST</span>
          </div>
        </div>
        
        <h2>Welcome Back</h2>
        <p>Login to your account to continue your recovery journey.</p>
        
        <form onSubmit={handleLogin} className="login-form">
          <div className="input-group">
            <Mail className="input-icon" size={20} color="#0A1448" />
            <input 
              type="email" 
              placeholder="Email address" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          
          <div className="input-group">
            <Lock className="input-icon" size={20} color="#0A1448" />
            <input 
              type="password" 
              placeholder="Password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button type="submit" className="login-submit-btn">
            Login
          </button>
        </form>
        
        <div className="login-footer">
          Don't have an account? <span className="signup-link">Sign Up</span>
        </div>
      </div>
    </div>
  );
}

export default Login;
