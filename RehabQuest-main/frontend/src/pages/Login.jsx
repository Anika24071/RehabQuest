import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, Heart } from 'lucide-react';

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
    if (email && password) navigate('/dashboard');
  };

  return (
    <div className="login-page">
      <div className="login-left">
        <div className="login-brand">
          <Heart size={52} fill="#FF5FAD" color="#FF5FAD" style={{margin:'0 auto', display:'block'}} />
          <h1>REHABQUEST</h1>
          <p>Your personal physiotherapy companion</p>
        </div>
        <div className="login-card">
          <h2>Welcome Back 👋</h2>
          <p>Login to continue your recovery journey.</p>
          <form onSubmit={handleLogin}>
            <div className="input-group">
              <Mail size={20} />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="input-group">
              <Lock size={20} />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="login-submit-btn" id="login-btn">
              Login →
            </button>
          </form>
          <div className="login-footer">
            Don't have an account? <span className="signup-link">Sign Up</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
