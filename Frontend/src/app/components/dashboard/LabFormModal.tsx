import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from './Modal';
import { ToggleButton } from './ToggleButton';
import { Lab, Specialist } from '../../types';
import { LAB_CATEGORIES } from '../../constants/labCategories';

const labSchema = z.object({
  name: z.string().min(1, 'Lab Name is required'),
  category: z.string().min(1, 'Lab Category is required'),
  floor: z.string().min(1, 'Floor is required'),
  specialist_id: z.string().optional(),
  is_active: z.boolean().default(true),
});

export type LabFormData = z.infer<typeof labSchema>;

export function LabFormModal({
  isOpen,
  onClose,
  editingLab,
  specialists,
  onSave,
}: {
  isOpen: boolean;
  onClose: () => void;
  editingLab: Lab | null;
  specialists: Specialist[];
  onSave: (data: LabFormData) => void | Promise<void>;
}) {
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<LabFormData>({
    resolver: zodResolver(labSchema),
  });

  const isActive = watch('is_active', true);

  useEffect(() => {
    if (!isOpen) return;
    if (editingLab) {
      reset({
        name: editingLab.name,
        category: editingLab.category,
        floor: editingLab.floor,
        specialist_id: editingLab.specialist_id || '',
        is_active: editingLab.is_active,
      });
      return;
    }
    reset({
      name: '',
      category: '',
      floor: 'Ground Floor',
      specialist_id: '',
      is_active: true,
    });
  }, [editingLab, isOpen, reset]);

  if (!isOpen) return null;

  return (
    <Modal onClose={onClose} title={editingLab ? 'Edit Lab' : 'Add Lab'}>
      <form onSubmit={handleSubmit(onSave)} className="space-y-4">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Lab Name</label>
          <input
            {...register('name')}
            type="text"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
            placeholder="Lab 16"
          />
          {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Lab Category</label>
          <select
            {...register('category')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
          >
            <option value="">Select Lab Category</option>
            {LAB_CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          {errors.category && <p className="text-red-500 text-xs mt-1">{errors.category.message}</p>}
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Floor</label>
          <select
            {...register('floor')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
          >
            <option value="Ground Floor">Ground Floor</option>
            <option value="First Floor">First Floor</option>
          </select>
          {errors.floor && <p className="text-red-500 text-xs mt-1">{errors.floor.message}</p>}
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Assign Specialist</label>
          <select
            {...register('specialist_id')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#5D2582]"
          >
            <option value="">Select Specialist</option>
            {specialists.map((spec) => (
              <option key={spec.id} value={spec.id}>
                {spec.name}
              </option>
            ))}
          </select>
          {errors.specialist_id && <p className="text-red-500 text-xs mt-1">{errors.specialist_id.message}</p>}
        </div>

        <ToggleButton
          label="Active Status"
          defaultChecked={isActive}
          onChange={(checked) => setValue('is_active', checked)}
        />
        {errors.is_active && <p className="text-red-500 text-xs mt-1">{errors.is_active.message}</p>}

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
            {editingLab ? 'Save Changes' : 'Add Lab'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
