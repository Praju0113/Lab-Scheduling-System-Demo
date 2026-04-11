import React from 'react';

export function QuickActionCard({
  onClick,
  icon: Icon,
  title,
}: {
  onClick: () => void;
  icon: any;
  title: string;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-4 p-4 border border-gray-200 rounded-lg hover:bg-[#f3ebf7] hover:border-[#b491c8] transition-all"
    >
      <div className="bg-[#e1d0ea] p-3 rounded-lg">
        <Icon className="w-6 h-6 text-[#5D2582]" />
      </div>
      <span className="text-gray-900">{title}</span>
    </button>
  );
}
