import { createBrowserRouter } from "react-router";
import RoleSelection from "./pages/RoleSelection";
import ReceptionistDashboard from "./pages/ReceptionistDashboard";
import LabSpecialistDashboard from "./pages/LabSpecialistDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import QueueDisplay from "./pages/QueueDisplay";

import { ProtectedRoute } from "./components/ProtectedRoute";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: RoleSelection,
  },
  {
    path: "/receptionist",
    Component: () => <ProtectedRoute allowedRoles={['Receptionist']} />,
    children: [
      {
        path: "",
        Component: ReceptionistDashboard,
      }
    ]
  },
  {
    path: "/lab-specialist",
    Component: () => <ProtectedRoute allowedRoles={['LabSpecialist']} />,
    children: [
      {
        path: "",
        Component: LabSpecialistDashboard,
      }
    ]
  },
  {
    path: "/admin",
    Component: () => <ProtectedRoute allowedRoles={['Admin']} />,
    children: [
      {
        path: "",
        Component: AdminDashboard,
      }
    ]
  },
  {
    path: "/queue-display",
    Component: QueueDisplay,
  },
]);
