import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
    BarChart3,
    Users,
    Database,
    Settings,
    FileText,
    LogOut,
    Bell
} from 'lucide-react';

const Layout = () => {
    const menuItems = [
        { name: '대시보드', path: '/', icon: <BarChart3 size={20} /> },
        { name: '사원 관리', path: '/employees', icon: <Users size={20} /> },
        { name: '원시 데이터', path: '/raw-data', icon: <Database size={20} /> },
        { name: '식사 정책', path: '/policies', icon: <Settings size={20} /> },
        { name: '리포트', path: '/reports', icon: <FileText size={20} /> },
    ];

    return (
        <div className="flex min-h-screen">
            {/* Sidebar */}
            <aside className="w-64 glass fixed h-full z-10 flex flex-col p-6">
                <div className="mb-10 flex items-center gap-3">
                    <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                        <BarChart3 size={18} color="white" />
                    </div>
                    <span className="text-xl font-bold tracking-tight">Meal Admin</span>
                </div>

                <nav className="flex-1 space-y-2">
                    {menuItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={({ isActive }) =>
                                `flex items-center gap-3 p-3 rounded-xl transition-all ${isActive
                                    ? 'bg-primary text-white shadow-lg shadow-primary/20'
                                    : 'text-text-muted hover:bg-white/5 hover:text-text-main'
                                }`
                            }
                        >
                            {item.icon}
                            <span className="font-medium">{item.name}</span>
                        </NavLink>
                    ))}
                </nav>

                <div className="pt-6 border-t border-glass-border">
                    <button className="flex items-center gap-3 p-3 rounded-xl text-text-muted hover:bg-danger/10 hover:text-danger w-full transition-all">
                        <LogOut size={20} />
                        <span className="font-medium">로그아웃</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 ml-64 p-8">
                <header className="flex justify-between items-center mb-10">
                    <div>
                        <h2 className="text-text-muted font-medium mb-1">환영합니다</h2>
                        <h1 className="text-3xl font-bold">관리자 시스템</h1>
                    </div>
                    <div className="flex items-center gap-4">
                        <button className="w-10 h-10 rounded-full flex items-center justify-center bg-white/5 hover:bg-white/10 transition-all relative">
                            <Bell size={20} />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-danger rounded-full border-2 border-bg-dark"></span>
                        </button>
                        <div className="flex items-center gap-3 pl-4 border-l border-glass-border">
                            <div className="text-right">
                                <p className="text-sm font-semibold">최고관리자</p>
                                <p className="text-xs text-text-muted">admin@meal.com</p>
                            </div>
                            <div className="w-10 h-10 bg-accent rounded-full flex items-center justify-center text-white font-bold">
                                A
                            </div>
                        </div>
                    </div>
                </header>

                <div className="fade-in">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};

export default Layout;
