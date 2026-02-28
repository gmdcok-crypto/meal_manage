import React, { useState, useEffect, useCallback } from 'react';
import DataTable from '../components/DataTable';
import { UserPlus, Trash2 } from 'lucide-react';
import { employeeApi } from '../api';

const Employees = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedIds, setSelectedIds] = useState([]);
    const [deptFilter, setDeptFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('ACTIVE');
    const [search, setSearch] = useState('');

    const fetchList = useCallback(async () => {
        setLoading(true);
        try {
            const params = {};
            if (deptFilter) params.dept = deptFilter;
            if (statusFilter) params.status = statusFilter;
            if (search) params.search = search;
            const res = await employeeApi.list(params);
            const list = res.data || [];
            setData(list.map((row) => ({
                id: row.id,
                emp_no: row.emp_no,
                name: row.name,
                dept: row.department_name ?? row.department_ref?.name ?? '-',
                status: row.status,
                role: row.role ?? 'USER'
            })));
        } catch (e) {
            console.error('사원 목록 조회 실패:', e);
            setData([]);
        } finally {
            setLoading(false);
        }
    }, [deptFilter, statusFilter, search]);

    useEffect(() => {
        fetchList();
    }, [fetchList]);

    const handleDelete = async (ids, clearSelection) => {
        if (!ids?.length) return;
        const id = ids[0];
        try {
            await employeeApi.delete(id);
            setData((prev) => prev.filter((row) => row.id !== id));
            clearSelection();
            alert('삭제되었습니다.');
        } catch (e) {
            console.error('삭제 실패:', e);
            alert(e.response?.data?.detail ?? '삭제에 실패했습니다.');
        }
    };

    const columns = [
        { header: '사번', accessor: 'emp_no' },
        { header: '이름', accessor: 'name' },
        { header: '부서', accessor: 'dept' },
        {
            header: '권한',
            render: (row) => (
                <span className={`px-2 py-1 rounded-md text-xs font-bold ${row.role === 'SITE_MANAGER' ? 'bg-accent/20 text-accent' : 'bg-white/10 text-text-muted'
                    }`}>
                    {row.role === 'SITE_MANAGER' ? '관리자' : '일반'}
                </span>
            )
        },
        {
            header: '상태',
            render: (row) => (
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${row.status === 'ACTIVE' ? 'bg-success' : 'bg-danger'}`} />
                    <span>{row.status === 'ACTIVE' ? '재직' : '퇴사'}</span>
                </div>
            )
        }
    ];

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold">사원 관리</h2>
                <div className="flex gap-3">
                    <button className="btn btn-ghost border border-white/10">
                        엑셀 업로드
                    </button>
                    <button className="btn btn-primary">
                        <UserPlus size={18} />
                        신규 사원 추가
                    </button>
                </div>
            </div>

            <div className="flex-1">
                <DataTable
                    columns={columns}
                    data={data}
                    loading={loading}
                    onSearch={setSearch}
                    selectable
                    selectedIds={selectedIds}
                    onSelectionChange={setSelectedIds}
                    toolbarActions={(ids, clearSelection) => (
                        <button
                            type="button"
                            className="btn btn-ghost border border-danger/30 text-danger hover:bg-danger/10 flex items-center gap-2"
                            onClick={() => handleDelete(ids, clearSelection)}
                        >
                            <Trash2 size={16} />
                            삭제
                        </button>
                    )}
                    filters={
                        <>
                            <select
                                className="bg-white/5 border border-white/10 rounded-xl py-2 px-4 text-sm focus:outline-none"
                                value={deptFilter}
                                onChange={(e) => setDeptFilter(e.target.value)}
                            >
                                <option value="">모든 부서</option>
                                {/* 부서 목록은 API로 채울 수 있음 */}
                            </select>
                            <select
                                className="bg-white/5 border border-white/10 rounded-xl py-2 px-4 text-sm focus:outline-none"
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                            >
                                <option value="ACTIVE">재직자</option>
                                <option value="RESIGNED">퇴사자</option>
                            </select>
                        </>
                    }
                />
            </div>
        </div>
    );
};

export default Employees;
