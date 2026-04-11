import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { LogOut, TrendingUp, Clock, CheckCircle, Users, Activity } from 'lucide-react';
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import logo from '../../assets/Nueberg_Logo.png';
import { useAppStore } from '../store/useAppStore';
import { frontendApi } from '../api/frontend';
import { Image } from '../components/Image';
import { KPICard } from '../components/dashboard/KPICard';
import { InsightCard } from '../components/dashboard/InsightCard';
import { useAuthStore } from '../store/useAuthStore';

type AdminDashboardPayload = {
  summary: {
    total_tests_completed: number;
    total_patients_attended: number;
    deferred_tests: number;
    unschedulable_tests: number;
    pending_queue_items: number;
  };
  lab_metrics: Array<{
    lab_id: string;
    name: string;
    completed: number;
    pending: number;
  }>;
  test_type_distribution: Array<{
    name: string;
    value: number;
  }>;
};

const chartColors = ['#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1', '#0ea5e9', '#ef4444'];

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { visits, labs, initializeData } = useAppStore();
  const logout = useAuthStore((state) => state.logout);
  const [dashboardData, setDashboardData] = useState<AdminDashboardPayload | null>(null);

  useEffect(() => {
    void initializeData();
  }, [initializeData]);

  useEffect(() => {
    const loadDashboardData = async () => {
      const data = await frontendApi.adminDashboard();
      setDashboardData(data);
    };

    void loadDashboardData();
  }, [visits, labs]);

  const completedTests = dashboardData?.summary.total_tests_completed ?? visits.filter((visit) => visit.status === 'Completed').length;
  const totalPatients = dashboardData?.summary.total_patients_attended ?? visits.length;
  const pendingQueue =
    dashboardData?.summary.pending_queue_items ??
    visits.filter((visit) => visit.status === 'Waiting' || visit.status === 'Pending').length;

  const avgCompletionTime = useMemo(() => {
    const completedVisits = visits.filter((visit) => visit.status === 'Completed' && visit.completed_at);
    if (completedVisits.length === 0) return null;

    const totalMinutes = completedVisits.reduce((sum, visit) => {
      const arrivalTime = new Date(visit.arrival_time);
      const completedAt = visit.completed_at ? new Date(visit.completed_at) : null;
      if (!completedAt) return sum;
      return sum + Math.max(0, Math.round((completedAt.getTime() - arrivalTime.getTime()) / 60000));
    }, 0);

    return Math.round(totalMinutes / completedVisits.length);
  }, [visits]);

  const labPerformance = useMemo(() => {
    const source =
      dashboardData?.lab_metrics ??
      labs.map((lab) => ({
        lab_id: lab.id,
        name: lab.name,
        completed: visits.filter((visit) => visit.lab_id === lab.id && visit.status === 'Completed').length,
        pending: visits.filter((visit) => visit.lab_id === lab.id && (visit.status === 'Waiting' || visit.status === 'Pending')).length,
      }));

    return source.map((labMetric) => {
      const total = labMetric.completed + labMetric.pending;
      const efficiency = total > 0 ? Math.round((labMetric.completed / total) * 100) : 0;
      return {
        ...labMetric,
        avgDuration: avgCompletionTime ?? 0,
        efficiency,
      };
    });
  }, [dashboardData, labs, visits, avgCompletionTime]);

  const hourlyData = useMemo(() => {
    const buckets = new Map<string, number>();
    visits.forEach((visit) => {
      const arrivalTime = new Date(visit.arrival_time);
      const bucket = `${String(arrivalTime.getHours()).padStart(2, '0')}:00`;
      buckets.set(bucket, (buckets.get(bucket) ?? 0) + 1);
    });

    return [...buckets.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([hour, count]) => ({ hour, visits: count }));
  }, [visits]);

  const testTypeData = useMemo(() => {
    const source = [...(dashboardData?.test_type_distribution ?? [])].sort((left, right) => right.value - left.value);
    const topEntries = source.slice(0, 8);
    const otherValue = source.slice(8).reduce((sum, entry) => sum + entry.value, 0);
    const collapsed = otherValue > 0 ? [...topEntries, { name: 'Others', value: otherValue }] : topEntries;

    return collapsed.map((entry, index) => ({
      ...entry,
      color: chartColors[index % chartColors.length],
    }));
  }, [dashboardData]);

  const peakHour = useMemo(() => {
    if (hourlyData.length === 0) return 'No patient arrivals yet';
    const peak = hourlyData.reduce((best, current) => (current.visits > best.visits ? current : best), hourlyData[0]);
    return `${peak.hour} (${peak.visits} patients)`;
  }, [hourlyData]);

  const bestPerformanceLab = useMemo(() => {
    if (labPerformance.length === 0) return 'No live lab data';
    const best = labPerformance.reduce((winner, current) => {
      if (current.efficiency > winner.efficiency) return current;
      if (current.efficiency === winner.efficiency && current.completed > winner.completed) return current;
      return winner;
    }, labPerformance[0]);
    return best.name;
  }, [labPerformance]);

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-[#5D2582] border-b border-gray-200 sticky top-0 z-10">
        <div className="px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="bg-white p-2 rounded-lg">
                <Image src={logo} alt="Neuberg Diagnostics" className="h-10" />
              </div>
              <div className="border-l border-white border-opacity-30 pl-4">
                <h1 className="text-xl text-white">Admin Dashboard</h1>
                <p className="text-sm text-[#c8a8d8]">Analytics & Performance Insights</p>
              </div>
            </div>
            <button
              onClick={() => {
                logout();
                navigate('/');
              }}
              className="flex items-center gap-2 px-4 py-2 bg-white text-black hover:bg-gray-100 rounded-lg transition-colors"
            >
              <LogOut className="w-5 h-5 text-black" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="px-8 py-6">
        <div className="grid grid-cols-4 gap-6 mb-6">
          <KPICard title="Total Tests" value={completedTests} icon={CheckCircle} color="text-green-600" bgColor="bg-green-50" />
          <KPICard title="Total Patients" value={totalPatients} icon={Users} color="text-blue-600" bgColor="bg-blue-50" />
          <KPICard title="Pending Queue" value={pendingQueue} icon={Clock} color="text-yellow-600" bgColor="bg-yellow-50" />
          <KPICard title="Avg Duration" value={avgCompletionTime !== null ? `${avgCompletionTime}m` : 'N/A'} icon={Activity} color="text-[#5D2582]" bgColor="bg-[#f3ebf7]" />
        </div>

        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-xl mb-4 text-gray-900">Patient Flow (Today)</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="hour" stroke="#6b7280" />
                <YAxis stroke="#6b7280" allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }} />
                <Legend />
                <Line type="monotone" dataKey="visits" stroke="#8b5cf6" strokeWidth={2} name="Patients" dot={{ fill: '#8b5cf6', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-xl mb-4 text-gray-900">Test Type Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={testTypeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => ((percent ?? 0) >= 0.08 ? `${name}: ${((percent ?? 0) * 100).toFixed(0)}%` : '')}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {testTypeData.map((entry, index) => (
                    <Cell key={`${entry.name}-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => [value, 'Tests']} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-xl mb-4 text-gray-900">Detailed Lab Metrics</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm text-gray-600">Lab Name</th>
                  <th className="text-left py-3 px-4 text-sm text-gray-600">Completed</th>
                  <th className="text-left py-3 px-4 text-sm text-gray-600">Pending</th>
                  <th className="text-left py-3 px-4 text-sm text-gray-600">Avg Duration</th>
                  <th className="text-left py-3 px-4 text-sm text-gray-600">Efficiency</th>
                </tr>
              </thead>
              <tbody>
                {labPerformance.map((lab) => (
                  <tr key={lab.lab_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">{lab.name}</td>
                    <td className="py-3 px-4"><span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">{lab.completed}</span></td>
                    <td className="py-3 px-4"><span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm">{lab.pending}</span></td>
                    <td className="py-3 px-4 text-gray-600">{avgCompletionTime !== null ? `${lab.avgDuration} min` : 'N/A'}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-[100px]">
                          <div className={`h-2 rounded-full ${lab.efficiency >= 75 ? 'bg-green-500' : lab.efficiency >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${lab.efficiency}%` }} />
                        </div>
                        <span className="text-sm text-gray-600 w-12">{lab.efficiency}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 mt-6">
          <InsightCard title="Peak Hours" value={peakHour} description="Highest patient traffic based on today's arrivals" icon={TrendingUp} color="text-blue-600" bgColor="bg-blue-50" />
          <InsightCard title="Queue Delay" value={avgCompletionTime !== null ? `Average ${avgCompletionTime} min` : 'No completion data'} description="Based on completed visits visible today" icon={Clock} color="text-yellow-600" bgColor="bg-yellow-50" />
          <InsightCard title="Best Performance" value={bestPerformanceLab} description="Highest lab efficiency among today's visible labs" icon={CheckCircle} color="text-green-600" bgColor="bg-green-50" />
        </div>
      </div>
    </div>
  );
}
