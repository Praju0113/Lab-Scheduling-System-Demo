import { create } from 'zustand';
import { Lab, Specialist, Visit } from '../types';
import { frontendApi, FrontendDeltaResponse } from '../api/frontend';

interface VisitPayload {
  patient_name: string;
  patient_age: number;
  patient_gender: string;
  priority_type: string;
  phone: string;
  test_names: string[];
}

interface QueueSnapshotLike {
  current?: { visit_id: string } | null;
  next?: { visit_id: string } | null;
  pending?: Array<{ visit_id: string }>;
}

const sortVisits = (visits: Visit[]) =>
  [...visits].sort((left, right) => new Date(left.arrival_time).getTime() - new Date(right.arrival_time).getTime());

const sortLabs = (labs: Lab[]) =>
  [...labs].sort((left, right) => left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: 'base' }));

const sortSpecialists = (specialists: Specialist[]) =>
  [...specialists].sort((left, right) => left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: 'base' }));

const upsertById = <T extends { id: string }>(items: T[], nextItem: T) => {
  const existingIndex = items.findIndex((item) => item.id === nextItem.id);
  if (existingIndex === -1) {
    return [...items, nextItem];
  }
  return items.map((item, index) => (index === existingIndex ? nextItem : item));
};

interface AppState {
  visits: Visit[];
  labs: Lab[];
  specialists: Specialist[];
  isLoading: boolean;
  lastDeltaAt: Date | null;
  setVisits: (visits: Visit[]) => void;
  setLabs: (labs: Lab[]) => void;
  setSpecialists: (specialists: Specialist[]) => void;
  initializeData: () => Promise<void>;
  mergeDelta: (payload: FrontendDeltaResponse) => void;
  updateLabQueue: (labId: string, snapshot: QueueSnapshotLike) => void;
  updateVisitStatus: (id: string, status: Visit['status']) => void;
  createVisit: (payload: VisitPayload) => Promise<void>;
  saveVisit: (id: string | null, payload: VisitPayload) => Promise<void>;
  saveSpecialist: (id: string | null, payload: Omit<Specialist, 'id'>) => Promise<void>;
  saveLab: (id: string | null, payload: Omit<Lab, 'id' | 'queue' | 'current_patient_id'>) => Promise<void>;
  deleteSpecialist: (id: string) => Promise<void>;
  deleteLab: (id: string) => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  visits: [],
  labs: [],
  specialists: [],
  isLoading: false,
  lastDeltaAt: null,

  setVisits: (visits) => set({ visits: sortVisits(visits) }),
  setLabs: (labs) => set({ labs: sortLabs(labs) }),
  setSpecialists: (specialists) => set({ specialists: sortSpecialists(specialists) }),
  initializeData: async () => {
    set({ isLoading: true });
    try {
      const data = await frontendApi.bootstrap();
      set({
        visits: sortVisits(data.visits),
        labs: sortLabs(data.labs),
        specialists: sortSpecialists(data.specialists),
        lastDeltaAt: new Date(),
        isLoading: false,
      });
    } catch (error) {
      console.error('Failed to bootstrap frontend data', error);
      set({ isLoading: false });
    }
  },

  mergeDelta: (payload) => set((state) => {
    let visits = [...state.visits];
    let labs = [...state.labs];
    let specialists = [...state.specialists];

    for (const visit of payload.visits ?? []) {
      visits = upsertById(visits, visit);
    }
    for (const lab of payload.labs ?? []) {
      labs = upsertById(labs, lab);
    }
    for (const specialist of payload.specialists ?? []) {
      specialists = upsertById(specialists, specialist);
    }

    return {
      visits: sortVisits(visits),
      labs: sortLabs(labs),
      specialists: sortSpecialists(specialists),
      lastDeltaAt: payload.now ? new Date(payload.now) : state.lastDeltaAt,
    };
  }),

  updateLabQueue: (labId, snapshot) => set((state) => ({
    labs: sortLabs(
      state.labs.map((lab) =>
        lab.id === labId
          ? {
              ...lab,
              current_patient_id: snapshot.current?.visit_id ?? undefined,
              queue: [
                ...(snapshot.next?.visit_id ? [snapshot.next.visit_id] : []),
                ...((snapshot.pending ?? []).map((item) => item.visit_id)),
              ],
            }
          : lab,
      ),
    ),
  })),

  updateVisitStatus: (id, status) => set((state) => ({
    visits: state.visits.map((visit) => (visit.id === id ? { ...visit, status } : visit)),
  })),

  createVisit: async (payload) => {
    const visit = await frontendApi.createPatient(payload);
    set((state) => ({ visits: sortVisits(upsertById(state.visits, visit)) }));
  },

  saveVisit: async (id, payload) => {
    const visit = id ? await frontendApi.updatePatient(id, payload) : await frontendApi.createPatient(payload);
    set((state) => ({ visits: sortVisits(upsertById(state.visits, visit)) }));
  },

  saveSpecialist: async (id, payload) => {
    const specialist = id ? await frontendApi.updateSpecialist(id, payload) : await frontendApi.createSpecialist(payload);
    set((state) => ({ specialists: sortSpecialists(upsertById(state.specialists, specialist)) }));
  },

  saveLab: async (id, payload) => {
    const lab = id ? await frontendApi.updateLab(id, payload) : await frontendApi.createLab(payload);
    set((state) => ({ labs: sortLabs(upsertById(state.labs, lab)) }));
  },

  deleteSpecialist: async (id) => {
    await frontendApi.deleteSpecialist(id);
    set((state) => ({ specialists: state.specialists.filter((specialist) => specialist.id !== id) }));
  },

  deleteLab: async (id) => {
    await frontendApi.deleteLab(id);
    set((state) => ({ labs: state.labs.filter((lab) => lab.id !== id) }));
  },
}));
