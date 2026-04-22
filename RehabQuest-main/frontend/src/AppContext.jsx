import React, { createContext, useContext, useState } from 'react';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [injuryType, setInjuryType] = useState('None');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [savedWorkouts, setSavedWorkouts] = useState(['wrist_rotation']);
  const [completedSessions, setCompletedSessions] = useState([
    { id: 'shoulder_raise', title: 'Shoulder/Hand Raise', date: '2025-04-21', duration: '5 mins' },
    { id: 'wrist_rotation', title: 'Wrist 360 Rotation', date: '2025-04-20', duration: '5 mins' },
  ]);

  const toggleSidebar = () => setIsSidebarOpen(prev => !prev);

  const toggleSave = (id) => {
    setSavedWorkouts(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const addCompleted = (session) => {
    setCompletedSessions(prev => [session, ...prev]);
  };

  return (
    <AppContext.Provider value={{
      injuryType, setInjuryType,
      isSidebarOpen, setIsSidebarOpen, toggleSidebar,
      savedWorkouts, toggleSave,
      completedSessions, addCompleted,
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => useContext(AppContext);
