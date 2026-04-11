import { useNavigate } from 'react-router';
import { UserCircle, FlaskConical, ShieldCheck } from 'lucide-react';
import { useState, useEffect } from 'react';
import logo from '../../assets/Nueberg_Logo.png';
import { useAuthStore } from '../store/useAuthStore';

export default function RoleSelection() {
  const navigate = useNavigate();
  const setAuth = useAuthStore(state => state.setAuth);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const roles = [
    {
      title: 'Receptionist',
      headerTitle: 'Reception',
      description: 'Manage patients, labs, and system configuration',
      icon: UserCircle,
      path: '/receptionist',
      role: 'Receptionist' as const,
    },
    {
      title: 'Lab Specialist',
      headerTitle: 'Lab Desk',
      description: 'Process tests and manage lab queue',
      icon: FlaskConical,
      path: '/lab-specialist',
      role: 'LabSpecialist' as const,
    },
    {
      title: 'Admin',
      headerTitle: 'Analytics',
      description: 'View analytics and system insights',
      icon: ShieldCheck,
      path: '/admin',
      role: 'Admin' as const,
    },
  ];

  const handleRoleSelection = (role: string, path: string) => {
    setAuth('mock-jwt-token-for-' + role, role as any);
    navigate(path);
  };


  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f3ebf7] via-white to-red-50">
      {/* Header */}
      <div className="bg-[#5D2582]">
        <div className="px-12 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="bg-white p-3 rounded-lg">
                <img src={logo} alt="Neuberg Diagnostics" className="h-12" />
              </div>
              <h1 className="text-3xl text-white">Lab Scheduling System</h1>
            </div>
            <div className="text-right text-white">
              <p className="text-2xl">{currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</p>
              <p className="text-sm text-[#c8a8d8]">{currentTime.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex items-center justify-center p-12">
        <div className="w-[1200px]">
          <div className="text-center mb-12">
            <h2 className="text-4xl mb-3 text-gray-900">Select Login Type</h2>
            <p className="text-gray-600">Select your role to continue</p>
          </div>

          <div className="grid grid-cols-3 gap-6">
            {roles.map((role) => {
              const Icon = role.icon;
              return (
                <button
                  key={role.path}
                  onClick={() => handleRoleSelection(role.role, role.path)}
                  className="bg-white rounded-2xl overflow-hidden transition-all duration-200 transform hover:scale-105 shadow-lg hover:shadow-xl h-[240px] flex flex-col"
                >
                  {/* Gradient Header */}
                  <div className="bg-gradient-to-r from-[#5D2582] via-[#5D2582] via-[#5D2582] via-[#7D3BA2] to-[#D4AF37] p-4 flex items-center justify-between">
                    <h2 className="text-xl text-white">{role.headerTitle}</h2>
                    <Icon className="w-8 h-8 text-white" />
                  </div>
                  
                  {/* Content */}
                  <div className="p-8 flex-1 flex flex-col justify-center">
                    <h3 className="text-2xl mb-3 text-gray-900">{role.title}</h3>
                    <p className="text-gray-600">{role.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
