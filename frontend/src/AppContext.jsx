import React, { createContext, useContext, useState } from 'react';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [injuryType, setInjuryType] = useState('None'); // E.g., 'None', 'Shoulder', 'Knee', 'Wrist'
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen(prev => !prev);

  return (
    <AppContext.Provider value={{
      injuryType,
      setInjuryType,
      isSidebarOpen,
      setIsSidebarOpen,
      toggleSidebar
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => useContext(AppContext);
