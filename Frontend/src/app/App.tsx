import { useEffect } from 'react';
import { RouterProvider } from 'react-router';
import { useRealTimeUpdates } from './hooks/useRealTimeUpdates';
import { router } from './routes';
import { useAppStore } from './store/useAppStore';

export default function App() {
  const initializeData = useAppStore((state) => state.initializeData);
  useRealTimeUpdates();

  useEffect(() => {
    initializeData().catch((error) => console.error('Failed to load initial data', error));
  }, [initializeData]);

  return <RouterProvider router={router} />;
}
