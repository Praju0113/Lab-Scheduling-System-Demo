import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Users,
  FlaskConical,
  Settings,
  LogOut,
  Search,
  RefreshCw,
  Clock,
  CheckCircle,
  Maximize2,
  UserPlus,
  Plus,
  Edit,
  Trash2,
} from 'lucide-react';
import logo from '../../assets/Nueberg_Logo.png';
import { useAppStore } from '../store/useAppStore';
import { Image } from '../components/Image';
import { TabButton } from '../components/dashboard/TabButton';
import { StatCard } from '../components/dashboard/StatCard';
import { QuickActionCard } from '../components/dashboard/QuickActionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { Modal } from '../components/dashboard/Modal';
import { useAuthStore } from '../store/useAuthStore';
import { SpecialistFormModal } from '../components/dashboard/SpecialistFormModal';
import { LabFormModal } from '../components/dashboard/LabFormModal';
import { PatientFormData, PatientFormModal } from '../components/dashboard/PatientFormModal';
import { Gender, Lab, Specialist, TestCatalogItem, Visit } from '../types';
import { frontendApi } from '../api/frontend';

type TabType = 'dashboard' | 'patients' | 'waiting' | 'labs' | 'config';
type ConfigTabType = 'specialist' | 'lab';

const compareByDisplayName = <T extends { name: string }>(left: T, right: T) =>
  left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: 'base' });

export default function ReceptionistDashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [configTab, setConfigTab] = useState<ConfigTabType>('specialist');
  const logout = useAuthStore((state) => state.logout);
  const {
    visits,
    labs,
    specialists,
    deleteSpecialist,
    deleteLab,
    saveSpecialist,
    saveLab,
    saveVisit,
    initializeData,
    isLoading,
  } = useAppStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('All');
  const [filterLabCategory, setFilterLabCategory] = useState<string>('All');
  const [showSpecialistModal, setShowSpecialistModal] = useState(false);
  const [showLabModal, setShowLabModal] = useState(false);
  const [showPatientModal, setShowPatientModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [editingSpecialist, setEditingSpecialist] = useState<Specialist | null>(null);
  const [editingLab, setEditingLab] = useState<Lab | null>(null);
  const [editingVisit, setEditingVisit] = useState<Visit | null>(null);
  const [testCatalog, setTestCatalog] = useState<TestCatalogItem[]>([]);

  useEffect(() => {
    initializeData().catch((error) => console.error('Failed to load receptionist dashboard', error));
    frontendApi.getTestCatalog().then(setTestCatalog).catch((error) => console.error('Failed to load test catalog', error));
  }, [initializeData]);

  const completedCount = visits.filter((visit) => visit.status === 'Completed').length;
  const waitingCount = visits.filter((visit) => visit.status === 'Waiting').length;

  const visitLabCategories = useMemo(() => {
    const categoriesByVisit = new Map<string, string[]>();

    visits.forEach((visit) => {
      const categories = new Set<string>();
      labs.forEach((lab) => {
        if (visit.lab_id === lab.id || lab.current_patient_id === visit.id || lab.queue.includes(visit.id)) {
          categories.add(lab.category);
        }
      });
      categoriesByVisit.set(visit.id, [...categories]);
    });

    return categoriesByVisit;
  }, [labs, visits]);

  const labCategories = useMemo(
    () => [
      'All',
      ...new Set(
        labs
          .map((lab) => lab.category)
          .filter(Boolean)
          .sort((left, right) => left.localeCompare(right, undefined, { numeric: true, sensitivity: 'base' })),
      ),
    ],
    [labs],
  );

  const sortedLabs = useMemo(() => [...labs].sort(compareByDisplayName), [labs]);
  const sortedSpecialists = useMemo(() => [...specialists].sort(compareByDisplayName), [specialists]);
  const labNameById = useMemo(() => new Map(labs.map((lab) => [lab.id, lab.name])), [labs]);

  const filteredVisits = useMemo(
    () =>
      visits.filter((visit) => {
        const matchesSearch =
          visit.patient_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          visit.id.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = filterStatus === 'All' || visit.status === filterStatus;
        const categories = visitLabCategories.get(visit.id) ?? [];
        const matchesLabCategory = filterLabCategory === 'All' || categories.includes(filterLabCategory);

        return matchesSearch && matchesStatus && matchesLabCategory;
      }),
    [visits, searchTerm, filterStatus, filterLabCategory, visitLabCategories],
  );

  const waitingVisits = useMemo(() => visits.filter((visit) => visit.status === 'Waiting'), [visits]);

  const handleSaveVisit = async (data: PatientFormData) => {
    await saveVisit(editingVisit?.id ?? null, {
      patient_name: data.patientName,
      patient_age: data.patientAge,
      patient_gender: data.patientGender,
      priority_type: data.priorityType,
      phone: data.phone ?? '',
      test_names: data.testNames,
    });
    setShowPatientModal(false);
    setEditingVisit(null);
    setActiveTab('patients');
  };

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
                <h1 className="text-xl text-white">Receptionist Dashboard</h1>
                <p className="text-sm text-[#c8a8d8]">Patient & Lab Management</p>
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
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6 p-2">
          <div className="flex gap-4 justify-between">
            <TabButton active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} icon={Users}>
              Dashboard
            </TabButton>
            <TabButton active={activeTab === 'patients'} onClick={() => setActiveTab('patients')} icon={Users}>
              Patients
            </TabButton>
            <TabButton active={activeTab === 'waiting'} onClick={() => setActiveTab('waiting')} icon={Clock}>
              Waiting Hall
            </TabButton>
            <TabButton active={activeTab === 'labs'} onClick={() => setActiveTab('labs')} icon={FlaskConical}>
              Lab Monitoring
            </TabButton>
            <TabButton active={activeTab === 'config'} onClick={() => setActiveTab('config')} icon={Settings}>
              Configuration
            </TabButton>
          </div>
        </div>

        {activeTab === 'dashboard' && (
          <div>
            <div className="grid grid-cols-2 gap-6 mb-6">
              <StatCard title="Patients Completed" value={completedCount} icon={CheckCircle} color="text-green-600" bgColor="bg-green-50" />
              <StatCard title="Patients Waiting" value={waitingCount} icon={Clock} color="text-yellow-600" bgColor="bg-yellow-50" />
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl text-gray-900">Quick Actions</h2>
                <button
                  onClick={() => navigate('/queue-display')}
                  className="flex items-center gap-2 px-4 py-2 bg-[#5D2582] text-white rounded-lg hover:bg-[#4a1e68] transition-colors"
                >
                  <Maximize2 className="w-4 h-4" />
                  Queue Display
                </button>
              </div>
              <div className="grid grid-cols-4 gap-4">
                <QuickActionCard
                  onClick={() => {
                    setEditingVisit(null);
                    setShowPatientModal(true);
                  }}
                  icon={UserPlus}
                  title="Add Patient"
                />
                <QuickActionCard onClick={() => setActiveTab('patients')} icon={Users} title="Manage Patients" />
                <QuickActionCard onClick={() => setActiveTab('waiting')} icon={Clock} title="View Waiting Hall" />
                <QuickActionCard onClick={() => setActiveTab('labs')} icon={FlaskConical} title="Monitor Labs" />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'patients' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl text-gray-900">Patient Management</h2>
              <button
                onClick={() => {
                  setEditingVisit(null);
                  setShowPatientModal(true);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-[#5D2582] text-white rounded-lg hover:bg-[#4a1e68] transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Patient
              </button>
            </div>

            <div className="flex gap-4 mb-6">
              <div className="flex-1 relative">
                <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by Patient ID or Name..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
                />
              </div>
              <select
                value={filterStatus}
                onChange={(event) => setFilterStatus(event.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
              >
                <option>All</option>
                <option>Waiting</option>
                <option>Pending</option>
                <option>Completed</option>
              </select>
              <select
                value={filterLabCategory}
                onChange={(event) => setFilterLabCategory(event.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
                aria-label="Filter by Lab Category"
              >
                {labCategories.map((category) => (
                  <option key={category} value={category}>
                    {category === 'All' ? 'All Lab Categories' : category}
                  </option>
                ))}
              </select>
              <button
                onClick={() => initializeData()}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm text-gray-600">Patient ID</th>
                    <th className="text-left py-3 px-4 text-sm text-gray-600">Name</th>
                    <th className="text-left py-3 px-4 text-sm text-gray-600">Age</th>
                    <th className="text-left py-3 px-4 text-sm text-gray-600">Requested Tests</th>
                    <th className="text-left py-3 px-4 text-sm text-gray-600">Lab Name</th>
                    <th className="text-left py-3 px-4 text-sm text-gray-600">Status</th>
                    <th className="text-left py-3 px-4 text-sm text-gray-600">Registered At</th>
                    <th className="text-left py-3 px-4 text-sm text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVisits.map((visit) => (
                    <tr key={visit.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-sm text-gray-600">{visit.id.toUpperCase()}</td>
                      <td className="py-3 px-4">{visit.patient_name}</td>
                      <td className="py-3 px-4 text-sm text-gray-600">{visit.patient_age}</td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        <div className="flex flex-wrap gap-1">
                          {visit.tests.map((testName, index) => (
                            <span key={`${visit.id}-${testName}-${index}`} className="px-2 py-1 bg-[#f3ebf7] text-[#5D2582] rounded text-xs">
                              {testName}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">{visit.lab_id ? labNameById.get(visit.lab_id) ?? '-' : '-'}</td>
                      <td className="py-3 px-4">
                        <StatusBadge status={visit.status} />
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {new Date(visit.arrival_time).toLocaleString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => {
                            setEditingVisit(visit);
                            setShowPatientModal(true);
                          }}
                          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors text-sm"
                        >
                          <Edit className="w-4 h-4 text-gray-600" />
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {isLoading && <div className="py-4 text-sm text-gray-500">Loading latest backend data...</div>}
            </div>
          </div>
        )}

        {activeTab === 'waiting' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl text-gray-900">Waiting Hall Monitoring</h2>
              <div className="flex items-center gap-2 px-4 py-2 bg-yellow-50 text-yellow-700 rounded-lg">
                <Clock className="w-5 h-5" />
                <span>{waitingCount} Patients Waiting</span>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4 max-h-[calc(100vh-350px)] overflow-y-auto pr-2">
              {waitingVisits.map((visit) => (
                <div key={visit.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <StatusBadge status={visit.status} />
                  </div>
                  <h3 className="text-lg mb-2 text-gray-900">{visit.patient_name}</h3>
                  <div className="space-y-1 text-sm text-gray-600">
                    <p>ID: {visit.id.toUpperCase()}</p>
                    <div>
                      <p className="mb-1">Requested Tests:</p>
                      <div className="flex flex-wrap gap-1">
                        {visit.tests.map((testName, index) => (
                          <span key={`${visit.id}-waiting-${testName}-${index}`} className="px-2 py-1 bg-[#f3ebf7] text-[#5D2582] rounded text-xs">
                            {testName}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'labs' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-2xl mb-6 text-gray-900">Live Lab Monitoring</h2>
              <div className="grid grid-cols-3 gap-6 max-h-[calc(100vh-350px)] overflow-y-auto pr-2">
                {sortedLabs.map((lab) => {
                  const currentVisit = visits.find((visit) => visit.id === lab.current_patient_id);
                  const nextVisitId = lab.queue[0];
                  const nextVisit = nextVisitId ? visits.find((visit) => visit.id === nextVisitId) : undefined;

                  return (
                    <div key={lab.id} className="bg-white border-2 rounded-lg p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-lg text-black">{lab.name}</h3>
                          <p className="text-sm text-gray-700">{lab.floor}</p>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-sm ${lab.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                          {lab.is_active ? 'Active' : 'Inactive'}
                        </div>
                      </div>

                      <div className="space-y-3 mb-4">
                        <div className="flex items-center gap-2 text-sm text-gray-700">
                          <FlaskConical className="w-4 h-4" />
                          <span>{lab.category}</span>
                        </div>
                      </div>

                      {currentVisit ? (
                        <div className="bg-green-50 border-2 rounded-lg p-4 mb-3">
                          <p className="text-xs text-green-800 mb-1">Current Patient</p>
                          <p className="text-lg text-green-900 font-bold">{currentVisit.id.toUpperCase()}</p>
                          <p className="text-sm text-green-800 mb-1">{currentVisit.patient_name}</p>
                        </div>
                      ) : (
                        <div className="bg-gray-50 border-2 border-gray-300 rounded-lg p-4 mb-3 text-center text-gray-500">
                          No active patient
                        </div>
                      )}

                      {nextVisit ? (
                        <div className="bg-amber-50 border-2 rounded-lg p-4">
                          <p className="text-xs text-amber-800 mb-2">Next Patient</p>
                          <p className="text-lg text-amber-900 font-bold">{nextVisit.id.toUpperCase()}</p>
                          <p className="text-sm text-amber-800 mb-1">{nextVisit.patient_name}</p>
                        </div>
                      ) : (
                        <div className="bg-gray-50 border-2 border-gray-300 rounded-lg p-4 text-center">
                          <span className="text-sm text-gray-500">No patient in queue</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'config' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-2">
              <div className="flex gap-2">
                <button
                  onClick={() => setConfigTab('specialist')}
                  className={`flex-1 px-6 py-3 rounded-lg transition-colors ${configTab === 'specialist' ? 'bg-[#5D2582] text-white' : 'text-gray-700 hover:bg-gray-100'}`}
                >
                  Specialist Management
                </button>
                <button
                  onClick={() => setConfigTab('lab')}
                  className={`flex-1 px-6 py-3 rounded-lg transition-colors ${configTab === 'lab' ? 'bg-[#5D2582] text-white' : 'text-gray-700 hover:bg-gray-100'}`}
                >
                  Lab Management
                </button>
              </div>
            </div>

            {configTab === 'specialist' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl text-gray-900">Specialist Management</h2>
                  <button
                    onClick={() => {
                      setEditingSpecialist(null);
                      setShowSpecialistModal(true);
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-[#5D2582] text-white rounded-lg hover:bg-[#4a1e68] transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    Add Specialist
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-4 max-h-[calc(100vh-380px)] overflow-y-auto pr-2">
                  {sortedSpecialists.map((specialist) => (
                    <div key={specialist.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-lg text-gray-900">{specialist.name}</h3>
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setEditingSpecialist(specialist);
                              setShowSpecialistModal(true);
                            }}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                          >
                            <Edit className="w-4 h-4 text-gray-600" />
                          </button>
                          <button
                            onClick={() => setShowDeleteConfirm(specialist.id)}
                            className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <Trash2 className="w-4 h-4 text-red-600" />
                          </button>
                        </div>
                      </div>
                      <div className="space-y-1 text-sm text-gray-600">
                        <p>Gender: {specialist.gender}</p>
                        <p>Shift: {specialist.shift_start} - {specialist.shift_end}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {configTab === 'lab' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl text-gray-900">Lab Management</h2>
                  <button
                    onClick={() => {
                      setEditingLab(null);
                      setShowLabModal(true);
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-[#5D2582] text-white rounded-lg hover:bg-[#4a1e68] transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    Add Lab
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-4 max-h-[calc(100vh-380px)] overflow-y-auto pr-2">
                  {sortedLabs.map((lab) => {
                    const specialist = specialists.find((item) => item.id === lab.specialist_id);
                    return (
                      <div key={lab.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <h3 className="text-lg text-gray-900">{lab.name}</h3>
                            <p className="text-sm text-gray-500">{lab.category}</p>
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => {
                                setEditingLab(lab);
                                setShowLabModal(true);
                              }}
                              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                              <Edit className="w-4 h-4 text-gray-600" />
                            </button>
                            <button
                              onClick={() => setShowDeleteConfirm(lab.id)}
                              className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                            >
                              <Trash2 className="w-4 h-4 text-red-600" />
                            </button>
                          </div>
                        </div>
                        <div className="space-y-1 text-sm text-gray-600">
                          <p>Floor: {lab.floor}</p>
                          <p>Specialist: {specialist?.name ?? '-'}</p>
                          <p>Status: {lab.is_active ? 'Active' : 'Inactive'}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {showDeleteConfirm && (
        <Modal onClose={() => setShowDeleteConfirm(null)} title="Confirm Delete">
          <p className="text-gray-600 mb-6">Are you sure you want to delete this item? This action cannot be undone.</p>
          <div className="flex gap-3 justify-end">
            <button
              onClick={() => setShowDeleteConfirm(null)}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                if (showDeleteConfirm.startsWith('s')) {
                  void deleteSpecialist(showDeleteConfirm).then(() => setShowDeleteConfirm(null));
                } else {
                  void deleteLab(showDeleteConfirm).then(() => setShowDeleteConfirm(null));
                }
              }}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Delete
            </button>
          </div>
        </Modal>
      )}

      <PatientFormModal
        isOpen={showPatientModal}
        onClose={() => {
          setShowPatientModal(false);
          setEditingVisit(null);
        }}
        editingPatient={editingVisit}
        testCatalog={testCatalog}
        onSave={(data) => void handleSaveVisit(data)}
      />

      <SpecialistFormModal
        isOpen={showSpecialistModal}
        onClose={() => setShowSpecialistModal(false)}
        editingSpecialist={editingSpecialist}
        onSave={(data) => {
          void saveSpecialist(editingSpecialist?.id ?? null, {
            name: data.name,
            gender: data.gender as Gender,
            shift_start: data.shift_start,
            shift_end: data.shift_end,
          }).then(() => {
            setShowSpecialistModal(false);
            setEditingSpecialist(null);
          });
        }}
      />

      <LabFormModal
        isOpen={showLabModal}
        onClose={() => setShowLabModal(false)}
        editingLab={editingLab}
        specialists={specialists}
        onSave={(data) => {
          void saveLab(editingLab?.id ?? null, {
            name: data.name,
            category: data.category,
            floor: data.floor,
            specialist_id: data.specialist_id,
            is_active: data.is_active,
          }).then(() => {
            setShowLabModal(false);
            setEditingLab(null);
          });
        }}
      />
    </div>
  );
}
