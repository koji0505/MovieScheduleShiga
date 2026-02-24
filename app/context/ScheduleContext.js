import React, { createContext, useContext } from 'react';
import { useSchedule } from '../hooks/useSchedule';

const ScheduleContext = createContext(null);

export function ScheduleProvider({ children }) {
  const value = useSchedule();
  return <ScheduleContext.Provider value={value}>{children}</ScheduleContext.Provider>;
}

export function useScheduleContext() {
  return useContext(ScheduleContext);
}
