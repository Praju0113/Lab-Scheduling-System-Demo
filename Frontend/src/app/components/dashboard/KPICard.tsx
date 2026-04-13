export function KPICard({ 
  title, 
  value, 
  icon: Icon, 
  color, 
  bgColor, 
  trend 
}: { 
  title: string; 
  value: number | string; 
  icon: any; 
  color: string; 
  bgColor: string; 
  trend?: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-3">
        <p className="text-gray-600">{title}</p>
        <div className={`${bgColor} p-2 rounded-lg`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
      </div>
      <div className="flex items-end justify-between">
        <p className={`text-3xl ${color}`}>{value}</p>
        {trend && (
          <span className={`text-sm ${
            trend.startsWith('+') ? 'text-green-600' : 'text-red-600'
          }`}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
