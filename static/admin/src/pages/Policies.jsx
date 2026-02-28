import React, { useState } from 'react';
import { Save, Clock, DollarSign, Plus } from 'lucide-react';

const Policies = () => {
    const [policies, setPolicies] = useState([
        { id: 1, meal_type: 'lunch', start_time: '11:00', end_time: '14:00', base_price: 0, guest_price: 6000, is_active: true },
        { id: 2, meal_type: 'dinner', start_time: '17:00', end_time: '19:30', base_price: 0, guest_price: 6000, is_active: true },
    ]);

    const PolicyCard = ({ policy }) => (
        <div className="card space-y-6">
            <div className="flex justify-between items-center">
                <h3 className="text-xl font-bold capitalize">{policy.meal_type === 'lunch' ? '중식' : '석식'} 정책</h3>
                <div className={`px-3 py-1 rounded-full text-xs font-bold ${policy.is_active ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}`}>
                    {policy.is_active ? '운영 중' : '중지됨'}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-xs text-text-muted font-medium">시작 시간</label>
                    <div className="relative">
                        <Clock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                        <input type="time" defaultValue={policy.start_time} className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-sm focus:border-primary focus:outline-none" />
                    </div>
                </div>
                <div className="space-y-2">
                    <label className="text-xs text-text-muted font-medium">종료 시간</label>
                    <div className="relative">
                        <Clock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                        <input type="time" defaultValue={policy.end_time} className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-sm focus:border-primary focus:outline-none" />
                    </div>
                </div>
                <div className="space-y-2">
                    <label className="text-xs text-text-muted font-medium">직원 단가 (기본)</label>
                    <div className="relative">
                        <DollarSign size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                        <input type="number" defaultValue={policy.base_price} className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-sm focus:border-primary focus:outline-none" />
                    </div>
                </div>
                <div className="space-y-2">
                    <label className="text-xs text-text-muted font-medium">외부 손님 단가</label>
                    <div className="relative">
                        <DollarSign size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                        <input type="number" defaultValue={policy.guest_price} className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-sm focus:border-primary focus:outline-none" />
                    </div>
                </div>
            </div>

            <div className="pt-4 flex justify-end">
                <button className="btn btn-primary">
                    <Save size={18} />
                    변경 사항 저장
                </button>
            </div>
        </div>
    );

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-bold">식사 정책 설정</h2>
                <p className="text-text-muted text-sm mt-1">식사 시간대별 운영 시간과 단가를 설정합니다.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {policies.map(p => <PolicyCard key={p.id} policy={p} />)}

                <button className="border-2 border-dashed border-white/10 rounded-2xl flex flex-col items-center justify-center p-10 hover:bg-white/5 hover:border-primary/50 transition-all text-text-muted group">
                    <div className="w-12 h-12 bg-white/5 rounded-full flex items-center justify-center mb-4 group-hover:bg-primary/20 group-hover:text-primary transition-all">
                        <Plus size={24} />
                    </div>
                    <span className="font-semibold">신규 정책 추가</span>
                    <span className="text-xs mt-1">조식 등 새로운 식사 구분 추가</span>
                </button>
            </div>
        </div>
    );
};

export default Policies;
