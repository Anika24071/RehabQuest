import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './AppContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import PreWorkout from './pages/PreWorkout';
import ActiveSession from './pages/ActiveSession';
import Login from './pages/Login';
import './index.css';
import './ui.css';

const App = () => {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          
          {/* Protected feeling routes wrapped in layout */}
          <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
          <Route path="/preworkout/:id" element={<Layout><PreWorkout /></Layout>} />
          <Route path="/session/:id" element={<Layout><ActiveSession /></Layout>} />
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
};

export default App;
