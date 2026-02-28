import React, { useState, useEffect } from 'react';
import {
    Users,
    UserPlus,
    AlertCircle,
    TrendingUp,
    Clock,
    Coffee,
    Sun,
    Moon
} from 'lucide-react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area
} from 'recharts';
import axios from 'axios';

const Dashboard = () => {
    const [stats, setStats] = useState({
        total_count: 0,
        employee_count: 0,
        guest_count: 0,
        exception_count: 0,
        meal_type: 'lunch',
        meal_summaries: []
    });

    const chartData = [
        { name: '08:00', count: 12 },
        { name: '09:00', count: 45 },
        { name: '10:00', count: 120 },
        { name: '11:00', count: 350 },
        { name: '12:00', count: 420 },
        { name: '13:00', count: 180 },
        { name: '14:00', count: 30 },
    ];

    const StatCard = ({ title, value, icon, color, trend }) => (
        <div className="card">
            <div className="flex justify-between items-start mb-4">
                <div className={`p-3 rounded-xl ${color} bg-opacity-10`}>
                    {React.cloneElement(icon, { className: color.replace('bg-', 'text-') })}
                </div>
                {trend && (
                    <div className="flex items-center gap-1 text-success text-sm font-semibold">
                        <TrendingUp size={14} />
                        {trend}
                    </div>
                )}
            </div>
            <h3 className="text-text-muted text-sm font-medium mb-1">{title}</h3>
            <p className="text-3xl font-bold">{value.toLocaleString()}</p>
        </div>
    );

    return (
        <div className="space-y-8">
            {/* Real-time Status */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="px-4 py-2 glass rounded-full flex items-center gap-2">
                        <Clock size={16} className="text-primary" />
                        <span className="font-semibold">{new Date().toLocaleDateString('ko-KR')}</span>
                    </div>
                    <div className="px-4 py-2 glass rounded-full flex items-center gap-2">
                        {stats.meal_type === 'lunch' ? <Sun size={16} className="text-warning" /> : <Moon size={16} className="text-accent" />}
                        <span className="font-semibold">{stats.meal_type === 'lunch' ? '중식 운영 중' : '석식 운영 중'}</span>
                    </div>
                </div>
                <button className="btn btn-primary" onClick={() => window.location.reload()}>
                    수동 새로고침
                </button>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="오늘 총 식수"
                    value={stats.total_count}
                    icon={<Users size={24} />}
                    color="bg-primary"
                    trend="+12%"
                />
                <StatCard
                    title="사원 식수"
                    value={stats.employee_count}
                    icon={<Coffee size={24} />}
                    color="bg-accent"
                />
                <StatCard
                    title="외부 손님"
                    value={stats.guest_count}
                    icon={<UserPlus size={24} />}
                    color="bg-success"
                />
                <StatCard
                    title="미처리/예외"
                    value={stats.exception_count}
                    icon={<AlertCircle size={24} />}
                    color="bg-danger"
                />
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 card">
                    <h3 className="text-xl font-bold mb-6">시간대별 식수 통계</h3>
                    <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData}>
                                <defs>
                                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis dataKey="name" stroke="#94a3b8" fontSize={14} tickLine={false} axisLine={false} />
                                <YAxis stroke="#94a3b8" fontSize={14} tickLine={false} axisLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                                    itemStyle={{ color: '#f8fafc' }}
                                />
                                <Area type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorCount)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="card">
                    <h3 className="text-xl font-bold mb-6">식사 종류별 점유율</h3>
                    <div className="space-y-6">
                        {stats.meal_summaries.map((menu, i) => (
                            <div key={i} className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="font-medium">{menu.meal_type}</span>
                                    <span className="text-text-muted">{menu.count}식</span>
                                </div>
                                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-primary"
                                        style={{ width: `${(menu.count / (stats.total_count || 1)) * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))}
                        {stats.meal_summaries.length === 0 && (
                            <p className="text-text-muted text-center py-10">오늘 등록된 식사 데이터가 없습니다.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
