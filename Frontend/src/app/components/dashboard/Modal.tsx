import React from 'react';

export function Modal({
  onClose,
  title,
  children,
  widthClass = 'max-w-md',
}: {
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  widthClass?: string;
}) {
  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-md flex items-center justify-center z-50 p-4">
      <div className={`bg-white rounded-xl shadow-xl w-full p-6 ${widthClass}`}>
        <h3 className="text-xl mb-4 text-gray-900">{title}</h3>
        {children}
      </div>
    </div>
  );
}
