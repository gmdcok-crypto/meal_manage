import React, { useState } from 'react';
import DataTable from '../components/DataTable';
import { Trash2, CheckCircle, Smartphone, Keyboard, Info } from 'lucide-react';

const RawData = () => {
    const [data, setData] = useState([
        { id: 1, user: { name: '김철수', emp_no: '2024001' }, policy: { meal_type: '중식' }, path: 'PWA', created_at: '2024-02-26 12:15:30', is_void: false },
        { id: 2, user: { name: '이영희', emp_no: '2024002' }, policy: { meal_type: '중식' }, path: 'MANUAL', created_at: '2024-02-26 12:18:45', is_void: false },
        { id: 3, user: { name: '외부손님', emp_no: '-' }, policy: { meal_type: '일반' }, path: 'QR', created_at: '2024-02-26 12:20:12', is_void: true, void_reason: '입력 실수' },
    ]);

    const columns = [
        {
            header: '시간',
            accessor: 'created_at',
            render: (row) => <span className="text-text-muted">{row.created_at.split(' ')[1]}</span>
        },
        { header: '이름', render: (row) => row.user.name },
        { header: '사번', render: (row) => row.user.emp_no },
        { header: '식사 종류', render: (row) => row.policy?.meal_type || '일반' },
        {
            header: '입력 경로',
            render: (row) => (
                <div className="flex items-center gap-2">
                    {row.path === 'PWA' ? <Smartphone size={14} className="text-primary" /> : <Keyboard size={14} className="text-accent" />}
                    <span className="text-xs">{row.path}</span>
                </div>
            )
        },
        {
            header: '상태',
            render: (row) => (
                <span className={`px-2 py-1 rounded-md text-xs font-bold ${row.is_void ? 'bg-danger/10 text-danger' : 'bg-success/10 text-success'
                    }`}>
                    {row.is_void ? '취소됨(VOID)' : '정상'}
                </span>
            )
        },
        {
            header: '작업',
            render: (row) => (
                <div className="flex items-center gap-2">
                    {!row.is_void && (
                        <button className="btn btn-ghost p-2 text-danger hover:bg-danger/10 transition-all" title="취소 처리">
                            <Trash2 size={16} />
                        </button>
                    )}
                    {row.is_void && (
                        <button className="p-2 text-text-muted hover:text-white transition-all" title={row.void_reason}>
                            <Info size={16} />
                        </button>
                    )}
                </div>
            )
        }
    ];

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold">원시 데이터 (조회/수정)</h2>
                    <p className="text-text-muted text-sm mt-1">모든 식사 원장 기록입니다. 삭제 대신 취소(VOID) 처리를 권장합니다.</p>
                </div>
                <div className="flex gap-3">
                    <button className="btn btn-primary">
                        <CheckCircle size={18} />
                        수동 식수 입력
                    </button>
                </div>
            </div>

            <div className="flex-1">
                <DataTable
                    columns={columns}
                    data={data}
                    onSearch={(val) => console.log('Search Raw:', val)}
                    filters={
                        <>
                            <input type="date" className="bg-white/5 border border-white/10 rounded-xl py-2 px-4 text-sm focus:outline-none" />
                            <select className="bg-white/5 border border-white/10 rounded-xl py-2 px-4 text-sm focus:outline-none">
                                <option value="">모든 경로</option>
                                <option value="PWA">PWA</option>
                                <option value="MANUAL">MANUAL</option>
                                <option value="QR">QR</option>
                            </select>
                        </>
                    }
                />
            </div>
        </div>
    );
};

export default RawData;
