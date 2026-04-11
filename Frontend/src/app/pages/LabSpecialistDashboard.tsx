import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { FlaskConical, LogOut, CheckCircle, Clock, XCircle } from 'lucide-react';
import logo from '../../assets/Nueberg_Logo.png';
import { Visit, Lab, WaitingCandidate } from '../types';
import { useAppStore } from '../store/useAppStore';
import { useAuthStore } from '../store/useAuthStore';
import { Image } from '../components/Image';
import { frontendApi } from '../api/frontend';

interface QueueSnapshot {
  current: { visit_id: string; visit_test_id: number; test_name?: string | null } | null;
  next: { visit_id: string; visit_test_id: number; test_name?: string | null } | null;
  pending: Array<{ visit_id: string; visit_test_id: number; test_name?: string | null }>;
  consecutive_pending_accepts?: number;
}

const compareByDisplayName = <T extends { name: string }>(left: T, right: T) =>
  left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: 'base' });

export default function LabSpecialistDashboard() {
  const navigate = useNavigate();
  const { visits, labs, specialists, initializeData, updateLabQueue } = useAppStore();
  const logout = useAuthStore((state) => state.logout);
  const [selectedLab, setSelectedLab] = useState<Lab | null>(null);
  const [queueSnapshot, setQueueSnapshot] = useState<QueueSnapshot | null>(null);
  const [waitingCandidates, setWaitingCandidates] = useState<WaitingCandidate[]>([]);

  const applyQueueSnapshot = (labId: string, snapshot: QueueSnapshot) => {
    setQueueSnapshot(snapshot);
    updateLabQueue(labId, snapshot);
  };

  const refreshSelectedLabQueue = async (labId?: string) => {
    if (!labId) return;
    const [snapshot, waiting] = await Promise.all([
      frontendApi.getQueueSnapshot(labId),
      frontendApi.getWaitingCandidates(labId),
    ]);
    applyQueueSnapshot(labId, snapshot);
    setWaitingCandidates(waiting.items);
  };

  const nextVisit = queueSnapshot?.next ? visits.find((visit) => visit.id === queueSnapshot.next.visit_id) || null : null;
  const currentVisit = queueSnapshot?.current ? visits.find((visit) => visit.id === queueSnapshot.current.visit_id) || null : null;

  const pendingQueueVisits = (queueSnapshot?.pending || [])
    .map((item) => {
      const visit = visits.find((candidate) => candidate.id === item.visit_id);
      if (!visit) return null;
      return { visit, test_name: item.test_name ?? '-', visit_test_id: item.visit_test_id };
    })
    .filter((item): item is { visit: Visit; test_name: string; visit_test_id: number } => Boolean(item));

  const sortedLabs = [...labs].sort(compareByDisplayName);

  const handleAcceptNext = async () => {
    if (!selectedLab || !nextVisit || !queueSnapshot?.next) return;
    const optimisticSnapshot: QueueSnapshot = { ...queueSnapshot, current: queueSnapshot.next, next: null };
    applyQueueSnapshot(selectedLab.id, optimisticSnapshot);
    try {
      const snapshot = await frontendApi.acceptCurrent(selectedLab.id);
      applyQueueSnapshot(selectedLab.id, snapshot);
      await refreshSelectedLabQueue(selectedLab.id);
    } catch (error) {
      console.error('Failed to accept next patient', error);
      await refreshSelectedLabQueue(selectedLab.id);
    }
  };

  const handlePendingNext = async () => {
    if (!selectedLab || !nextVisit || !queueSnapshot?.next) return;
    const optimisticSnapshot: QueueSnapshot = {
      ...queueSnapshot,
      pending: [...queueSnapshot.pending, queueSnapshot.next],
      next: null,
    };
    applyQueueSnapshot(selectedLab.id, optimisticSnapshot);
    try {
      const snapshot = await frontendApi.moveCurrentToPending(selectedLab.id);
      applyQueueSnapshot(selectedLab.id, snapshot);
      await refreshSelectedLabQueue(selectedLab.id);
    } catch (error) {
      console.error('Failed to move next patient to pending', error);
      await refreshSelectedLabQueue(selectedLab.id);
    }
  };

  const handleCompleteTest = async () => {
    if (!selectedLab || !currentVisit || !queueSnapshot) return;
    const optimisticSnapshot: QueueSnapshot = { ...queueSnapshot, current: null };
    applyQueueSnapshot(selectedLab.id, optimisticSnapshot);
    try {
      const snapshot = await frontendApi.completeCurrent(selectedLab.id);
      applyQueueSnapshot(selectedLab.id, snapshot);
      await refreshSelectedLabQueue(selectedLab.id);
    } catch (error) {
      console.error('Failed to complete current patient', error);
      await refreshSelectedLabQueue(selectedLab.id);
    }
  };

  const handleCurrentToPending = async () => {
    if (!selectedLab || !currentVisit || !queueSnapshot?.current) return;
    const optimisticSnapshot: QueueSnapshot = {
      ...queueSnapshot,
      current: null,
      pending: [...queueSnapshot.pending, queueSnapshot.current],
    };
    applyQueueSnapshot(selectedLab.id, optimisticSnapshot);
    try {
      const snapshot = await frontendApi.moveCurrentToPending(selectedLab.id);
      applyQueueSnapshot(selectedLab.id, snapshot);
      await refreshSelectedLabQueue(selectedLab.id);
    } catch (error) {
      console.error('Failed to move current patient to pending', error);
      await refreshSelectedLabQueue(selectedLab.id);
    }
  };

  const handleAcceptFromPending = async (visit_test_id?: number) => {
    if (!selectedLab) return;
    try {
      const snapshot = await frontendApi.acceptFromPending(selectedLab.id, visit_test_id);
      applyQueueSnapshot(selectedLab.id, snapshot);
      await refreshSelectedLabQueue(selectedLab.id);
    } catch (error) {
      console.error('Failed to accept patient from pending', error);
      await refreshSelectedLabQueue(selectedLab.id);
    }
  };

  useEffect(() => {
    initializeData().catch((error) => console.error('Failed to load lab dashboard', error));
  }, [initializeData]);

  useEffect(() => {
    if (selectedLab) {
      void refreshSelectedLabQueue(selectedLab.id);
    } else {
      setQueueSnapshot(null);
      setWaitingCandidates([]);
    }
  }, [selectedLab, labs, visits]);

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
                <h1 className="text-xl text-white">Lab Specialist Dashboard</h1>
                <p className="text-sm text-[#c8a8d8]">Test Processing & Queue Management</p>
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
        {!selectedLab ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            <h2 className="text-2xl mb-6 text-gray-900">Select Your Lab Station</h2>
            <div className="grid grid-cols-4 gap-4 max-h-[calc(100vh-300px)] overflow-y-auto pr-2">
              {sortedLabs.map((lab) => (
                <button
                  key={lab.id}
                  onClick={() => setSelectedLab(lab)}
                  className="border-2 border-gray-200 rounded-xl p-6 hover:border-[#5D2582] hover:bg-[#f3ebf7] transition-all text-left"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-[#e1d0ea] p-3 rounded-lg">
                      <FlaskConical className="w-6 h-6 text-[#5D2582]" />
                    </div>
                    <div>
                      <h3 className="text-lg text-gray-900">{lab.name}</h3>
                      <p className="text-sm text-gray-500">{lab.category}</p>
                    </div>
                  </div>
                  <div className="space-y-1 text-sm text-gray-600">
                    <p>Floor: {lab.floor}</p>
                    <p>Specialist: {specialists.find((specialist) => specialist.id === lab.specialist_id)?.name ?? '-'}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="bg-[#e1d0ea] p-3 rounded-lg">
                    <FlaskConical className="w-8 h-8 text-[#5D2582]" />
                  </div>
                  <div>
                    <h2 className="text-2xl text-gray-900">{selectedLab.name}</h2>
                    <p className="text-gray-600">{selectedLab.category}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="text-xl mb-4 text-gray-900">Current Patient</h3>
                {currentVisit ? (
                  <div>
                    <div className="bg-gradient-to-br from-[#e1d0ea] to-[#f3ebf7] rounded-xl p-6 mb-4">
                      <h4 className="text-2xl mb-3 text-[#2a123d]">{currentVisit.patient_name}</h4>
                      <div className="space-y-3 text-sm text-[#3a1852]">
                        <div>
                          <p className="text-[#5D2582] mb-1">Patient ID</p>
                          <p className="font-medium">{currentVisit.id.toUpperCase()}</p>
                        </div>
                        <div>
                          <p className="text-[#5D2582] mb-1">Test</p>
                          <p className="font-medium">{queueSnapshot?.current?.test_name ?? '-'}</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={handleCompleteTest} className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                        <CheckCircle className="w-5 h-5" />
                        Complete
                      </button>
                      <button onClick={handleCurrentToPending} className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors">
                        <XCircle className="w-5 h-5" />
                        Pending
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-xl p-12 text-center">
                    <Clock className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">No active patient</p>
                  </div>
                )}
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="text-xl mb-4 text-gray-900">Next Patient</h3>
                {nextVisit ? (
                  <div>
                    <div className="bg-yellow-50 rounded-xl p-6 mb-4 border border-yellow-200">
                      <h4 className="text-2xl mb-3 text-yellow-900">{nextVisit.patient_name}</h4>
                      <div className="space-y-3 text-sm text-yellow-800">
                        <div>
                          <p className="text-yellow-600 mb-1">Patient ID</p>
                          <p>{nextVisit.id.toUpperCase()}</p>
                        </div>
                        <div>
                          <p className="text-yellow-600 mb-1">Test</p>
                          <p>{queueSnapshot?.next?.test_name ?? '-'}</p>
                        </div>
                      </div>
                    </div>

                    {!currentVisit && (
                      <div className="flex gap-2">
                        <button onClick={handleAcceptNext} className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-[#5D2582] text-white rounded-lg hover:bg-[#4a1e68] transition-colors">
                          <CheckCircle className="w-5 h-5" />
                          Accept
                        </button>
                        <button onClick={handlePendingNext} className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors">
                          <XCircle className="w-5 h-5" />
                          Pending
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-xl p-12 text-center">
                    <Clock className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">No patients in queue</p>
                  </div>
                )}
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl text-gray-900">Waiting</h3>
                  <span className="px-3 py-1 bg-[#f3ebf7] text-[#5D2582] rounded-lg text-sm">{waitingCandidates.length}</span>
                </div>

                {waitingCandidates.length > 0 ? (
                  <div className="space-y-3 max-h-[420px] overflow-y-auto pr-2">
                    {waitingCandidates.map((item) => {
                      const infoTone = item.is_queue_eligible ? 'border-gray-200 bg-white' : 'border-orange-200 bg-orange-50';
                      return (
                        <div key={`${item.visit_id}-${item.visit_test_id}`} className={`border rounded-lg p-4 ${infoTone}`}>
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <h4 className="text-gray-900">{item.patient_name}</h4>
                              <p className="text-xs text-gray-500 mt-1">{item.visit_id.toUpperCase()}</p>
                            </div>
                            <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">#{item.queue_number || '-'}</span>
                          </div>
                          <p className="text-sm text-[#5D2582] mt-3">{item.test_name}</p>
                          <div className="mt-2 space-y-1 text-xs text-gray-500">
                            <p>
                              {new Date(item.arrival_time).toLocaleString('en-US', {
                                month: 'short',
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </p>
                            {!item.is_queue_eligible && item.active_lab_name && item.active_queue_status && (
                              <p className="text-orange-700">Busy in {item.active_lab_name} ({item.active_queue_status})</p>
                            )}
                            {!item.is_queue_eligible && !item.active_lab_name && item.is_dependency_blocked && (
                              <p className="text-orange-700">Blocked by dependency</p>
                            )}
                            {item.is_queue_eligible && <p className="text-green-700">Queue eligible</p>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-xl p-12 text-center text-gray-500">No waiting candidates</div>
                )}
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl text-gray-900">Pending Queue</h3>
                <span className="px-4 py-2 bg-yellow-100 text-yellow-700 rounded-lg">{pendingQueueVisits.length} patients waiting</span>
              </div>

              {pendingQueueVisits.length > 0 ? (
                <div className="grid grid-cols-5 gap-4 max-h-[400px] overflow-y-auto pr-2">
                  {pendingQueueVisits.map(({ visit, test_name, visit_test_id }) => (
                    <div key={`${visit.id}-${visit_test_id}`} className="border rounded-lg p-4 border-gray-200 bg-white hover:shadow-md transition-shadow">
                      <h4 className="mb-2 text-gray-900">{visit.patient_name}</h4>
                      <p className="text-xs text-gray-500 mb-2">ID: {visit.id.toUpperCase()}</p>
                      <div className="mb-3">
                        <p className="text-xs text-gray-600 mb-1">Test:</p>
                        <p className="text-sm text-gray-800">{test_name}</p>
                      </div>
                      <button
                        onClick={() => void handleAcceptFromPending(visit_test_id)}
                        disabled={currentVisit !== null}
                        className={`w-full px-3 py-2 rounded-lg text-sm transition-colors ${currentVisit !== null ? 'bg-gray-200 text-gray-500 cursor-not-allowed' : 'bg-[#5D2582] text-white hover:bg-[#4a1e68]'}`}
                      >
                        Accept
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">No patients in pending queue</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
