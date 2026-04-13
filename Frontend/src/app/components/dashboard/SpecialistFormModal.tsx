import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from './Modal';
import { Specialist } from '../../types';

const specialistSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 chars length'),
  gender: z.enum(['Male', 'Female', 'Other']),
  shift_start: z.string().min(1, 'Shift Start is required'),
  shift_end: z.string().min(1, 'Shift End is required'),
});

export type SpecialistFormData = z.infer<typeof specialistSchema>;

export function SpecialistFormModal({
  isOpen,
  onClose,
  editingSpecialist,
  onSave,
}: {
  isOpen: boolean;
  onClose: () => void;
  editingSpecialist: Specialist | null;
  onSave: (data: SpecialistFormData) => void | Promise<void>;
}) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SpecialistFormData>({
    resolver: zodResolver(specialistSchema),
  });

  useEffect(() => {
    if (!isOpen) return;
    if (editingSpecialist) {
      reset({
        name: editingSpecialist.name,
        gender: editingSpecialist.gender as any,
        shift_start: editingSpecialist.shift_start,
        shift_end: editingSpecialist.shift_end,
      });
      return;
    }
    reset({
      name: '',
      gender: 'Male',
      shift_start: '08:00',
      shift_end: '16:00',
    });
  }, [editingSpecialist, isOpen, reset]);

  if (!isOpen) return null;

  return (
    <Modal onClose={onClose} title={editingSpecialist ? 'Edit Specialist' : 'Add Specialist'}>
      <form onSubmit={handleSubmit(onSave)} className="space-y-4">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Name</label>
          <input
            {...register('name')}
            type="text"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
            placeholder="Dr. John Doe"
          />
          {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Gender</label>
          <select
            {...register('gender')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
          >
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
          {errors.gender && <p className="text-red-500 text-xs mt-1">{errors.gender.message}</p>}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Shift Start</label>
            <input
              {...register('shift_start')}
              type="time"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
            />
            {errors.shift_start && <p className="text-red-500 text-xs mt-1">{errors.shift_start.message}</p>}
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Shift End</label>
            <input
              {...register('shift_end')}
              type="time"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
            />
            {errors.shift_end && <p className="text-red-500 text-xs mt-1">{errors.shift_end.message}</p>}
          </div>
        </div>

        <div className="flex gap-3 justify-end mt-6">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 bg-[#5D2582] text-white rounded-lg hover:bg-[#4a1e68] transition-colors"
          >
            {editingSpecialist ? 'Save Changes' : 'Add Specialist'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
