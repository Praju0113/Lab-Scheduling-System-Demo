import React from 'react';
import { AlertTriangle, Info, CheckCircle, XCircle } from 'lucide-react';

interface AlertProps {
  type?: 'warning' | 'error' | 'success' | 'info';
  title: string;
  message: string;
}

export function Alert({ type = 'warning', title, message }: AlertProps) {
  const styles = {
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  };

  const icons = {
    warning: <AlertTriangle className="w-5 h-5 text-yellow-600" />,
    error: <XCircle className="w-5 h-5 text-red-600" />,
    success: <CheckCircle className="w-5 h-5 text-green-600" />,
    info: <Info className="w-5 h-5 text-blue-600" />,
  };

  return (
    <div className={`flex items-start gap-3 p-4 border rounded-xl ${styles[type]}`}>
      <div className="flex-shrink-0 mt-0.5">{icons[type]}</div>
      <div>
        <h4 className="font-semibold">{title}</h4>
        <p className="text-sm mt-1 opacity-90">{message}</p>
      </div>
    </div>
  );
}
