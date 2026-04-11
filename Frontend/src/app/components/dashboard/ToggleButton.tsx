import React, { useState } from 'react';

export function ToggleButton({
  label,
  defaultChecked,
  onChange,
}: {
  label: string;
  defaultChecked: boolean;
  onChange?: (checked: boolean) => void;
}) {
  const [isChecked, setIsChecked] = useState(defaultChecked);

  const toggle = () => {
    const newVal = !isChecked;
    setIsChecked(newVal);
    if (onChange) onChange(newVal);
  };

  return (
    <div className="flex items-center justify-between">
      <label className="text-sm text-gray-600">{label}</label>
      <button
        type="button"
        onClick={toggle}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          isChecked ? "bg-[#5D2582]" : "bg-gray-300"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            isChecked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}
