import React from 'react';

export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Waiting: "bg-yellow-100 text-yellow-700",
    Active: "bg-blue-100 text-blue-700",
    Completed: "bg-green-100 text-green-700",
    Pending: "bg-orange-100 text-orange-700",
  };
  
  const statusColor = colors[status] || "bg-gray-100 text-gray-700";
  
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColor}`}>
      {status}
    </span>
  );
}
