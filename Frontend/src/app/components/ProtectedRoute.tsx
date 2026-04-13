import { Navigate, Outlet } from 'react-router';
import { useAuthStore } from '../store/useAuthStore';

interface ProtectedRouteProps {
  allowedRoles?: ('Admin' | 'Receptionist')[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { role, token } = useAuthStore();

  // If there's no token, redirect to login
  if (!token) {
    return <Navigate to="/" replace />;
  }

  // If user role is not allowed, redirect to unauthorized or home
  if (allowedRoles && role && !allowedRoles.includes(role)) {
    // We could make an Unauthorized component later, or redirect back to role selection
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
