import React from 'react';

export function TabButton({
  active,
  onClick,
  icon: Icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: any;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
        active
          ? "bg-[#5D2582] text-white"
          : "text-gray-700 hover:bg-gray-100"
      }`}
    >
      <Icon className="w-4 h-4" />
      {children}
    </button>
  );
}
