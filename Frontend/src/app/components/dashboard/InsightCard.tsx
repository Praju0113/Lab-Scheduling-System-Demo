import React from 'react';

export function InsightCard({ 
  title, 
  value, 
  description, 
  icon: Icon, 
  color, 
  bgColor 
}: { 
  title: string; 
  value: string; 
  description: string; 
  icon: any; 
  color: string; 
  bgColor: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col justify-between">
      <div className="flex items-start gap-4 mb-4">
        <div className={`${bgColor} p-3 rounded-lg flex-shrink-0`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
        <div>
          <h4 className="text-gray-900 font-medium mb-1">{title}</h4>
          <p className="text-xl text-gray-900 mb-1">{value}</p>
        </div>
      </div>
      <p className="text-sm text-gray-500">{description}</p>
    </div>
  );
}
