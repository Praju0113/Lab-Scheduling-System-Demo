import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { X, Maximize2 } from 'lucide-react';
import nuebergLogo from '../../assets/Nueberg_Logo.png';
import { useAppStore } from '../store/useAppStore';

const compareByDisplayName = <T extends { name: string }>(left: T, right: T) =>
  left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: 'base' });

export default function QueueDisplay() {
  const navigate = useNavigate();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const { visits, labs, initializeData } = useAppStore();

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    void initializeData();
  }, [initializeData]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const getLabQueue = (labId: string) => {
    const lab = labs.find((item) => item.id === labId);
    const currentVisit = visits.find((visit) => visit.id === lab?.current_patient_id) || null;
    const nextVisit = lab?.queue?.[0] ? visits.find((visit) => visit.id === lab.queue[0]) || null : null;
    return { currentVisit, nextVisit };
  };

  const sortedLabs = [...labs].sort(compareByDisplayName);

  return (
    <div className="flex flex-col h-screen bg-black text-white">
      <div className="bg-[#5D2582] border-b border-white border-opacity-20 flex-shrink-0">
        <div className="px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="bg-white p-2 rounded-lg">
                <img src={nuebergLogo} alt="Neuberg Diagnostics" className="h-8" />
              </div>
              <div className="border-l border-white border-opacity-30 pl-4">
                <h1 className="text-xl mb-0.5">Queue Display System</h1>
                <p className="text-xs text-[#c8a8d8]">Real-time Patient Status</p>
              </div>
            </div>
            <div className="flex items-center gap-8">
              <div className="text-right">
                <p className="text-lg">{currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</p>
                <p className="text-xs text-[#c8a8d8]">{currentTime.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
              </div>
              <div className="flex gap-2">
                <button onClick={toggleFullscreen} className="p-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-lg transition-colors">
                  <Maximize2 className="w-5 h-5 text-black" />
                </button>
                <button onClick={() => navigate('/receptionist')} className="p-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-lg transition-colors">
                  <X className="w-5 h-5 text-black" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-4 bg-black">
        <div className="grid grid-cols-4 gap-4">
          {sortedLabs.map((lab) => {
            const { currentVisit, nextVisit } = getLabQueue(lab.id);
            return (
              <div key={lab.id} className="bg-white rounded-[14px] p-4 flex flex-col">
                <div className="text-center mb-2 mt-1">
                  <h3 className="text-black font-extrabold text-[22px] tracking-tight">{lab.name}</h3>
                </div>
                <div className="border-b-[1.5px] border-gray-400 opacity-60 mb-4" />
                <div className="flex items-start gap-0 mb-2">
                  <div className="flex-1">
                    <p className="text-[#333] font-bold text-[14px] mb-1">Current</p>
                    {currentVisit ? <p className="text-[#00c853] font-bold text-[22px] tracking-tight">{currentVisit.id.toUpperCase()}</p> : <p className="text-gray-300 text-sm font-bold">-</p>}
                  </div>
                  <div className="border-r-[1.5px] border-gray-400 opacity-60 h-10 mx-3 mt-1"></div>
                  <div className="flex-1">
                    <p className="text-[#333] font-bold text-[14px] mb-1">Next</p>
                    {nextVisit ? <p className="text-[#ff9800] font-bold text-[22px] tracking-tight">{nextVisit.id.toUpperCase()}</p> : <p className="text-gray-300 text-sm font-bold">-</p>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

