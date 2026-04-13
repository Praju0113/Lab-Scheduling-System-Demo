import type { DefinedLabCategory } from './constants/labCategories';

export type LabCategory = DefinedLabCategory | string;

export type VisitStatus = 'Waiting' | 'Pending' | 'Completed';
export type Gender = 'Male' | 'Female' | 'Other';
export type PriorityType = 'NORMAL' | 'EMERGENCY';

export interface Visit {
  id: string;
  patient_name: string;
  patient_age: number;
  patient_gender: Gender;
  phone: string;
  priority_type?: PriorityType;
  tests: string[];
  status: VisitStatus;
  lab_id?: string | null;
  arrival_time: Date | string;
  completed_at?: Date | string | null;
  queue_number: number;
}

export interface TestCatalogItem {
  test_name: string;
  test_code: string;
  category: string;
  duration_minutes: number;
  tags: string[];
  condition_category?: string | null;
}

export interface WaitingCandidate {
  visit_id: string;
  visit_test_id: number;
  patient_name: string;
  patient_age: number;
  patient_gender: string;
  test_name: string;
  queue_number: number;
  arrival_time: string;
  is_queue_eligible?: boolean;
  active_queue_status?: string | null;
  active_lab_id?: string | null;
  active_lab_name?: string | null;
  is_dependency_blocked?: boolean;
}

export interface Specialist {
  id: string;
  name: string;
  gender: Gender;
  shift_start: string;
  shift_end: string;
}

export interface Lab {
  id: string;
  name: string;
  category: LabCategory;
  floor: string;
  specialist_id?: string | null;
  is_active: boolean;
  current_patient_id?: string | null;
  queue: string[];
}

export interface QueueItem {
  patient_id: string;
  position: number;
  estimated_wait_time: number;
}
