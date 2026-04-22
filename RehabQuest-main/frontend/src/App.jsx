import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './AppContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import PreWorkout from './pages/PreWorkout';
import ActiveSession from './pages/ActiveSession';
import './index.css';
import './ui.css';

const Workouts    = lazy(() => import('./pages/Workouts'));
const Programmes  = lazy(() => import('./pages/Programmes'));
const SavedWorkouts = lazy(() => import('./pages/SavedWorkouts'));
const Activity    = lazy(() => import('./pages/Activity'));
const Inbox       = lazy(() => import('./pages/Inbox'));
const Challenges  = lazy(() => import('./pages/Challenges'));

const Loader = () => (
  <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'60vh'}}>
    <div style={{width:40,height:40,border:'4px solid #FFD6EC',borderTopColor:'#FF5FAD',borderRadius:'50%',animation:'spin 0.8s linear infinite'}} />
  </div>
);

const App = () => (
  <AppProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard"    element={<Layout><Dashboard /></Layout>} />
        <Route path="/preworkout/:id" element={<Layout><PreWorkout /></Layout>} />
        <Route path="/session/:id"  element={<Layout><ActiveSession /></Layout>} />
        <Route path="/workouts"     element={<Layout><Suspense fallback={<Loader />}><Workouts /></Suspense></Layout>} />
        <Route path="/programmes"   element={<Layout><Suspense fallback={<Loader />}><Programmes /></Suspense></Layout>} />
        <Route path="/saved"        element={<Layout><Suspense fallback={<Loader />}><SavedWorkouts /></Suspense></Layout>} />
        <Route path="/activity"     element={<Layout><Suspense fallback={<Loader />}><Activity /></Suspense></Layout>} />
        <Route path="/inbox"        element={<Layout><Suspense fallback={<Loader />}><Inbox /></Suspense></Layout>} />
        <Route path="/challenges"   element={<Layout><Suspense fallback={<Loader />}><Challenges /></Suspense></Layout>} />
      </Routes>
    </BrowserRouter>
  </AppProvider>
);

export default App;
