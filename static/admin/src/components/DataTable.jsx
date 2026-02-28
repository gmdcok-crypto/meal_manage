import React from 'react';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';

const DataTable = ({
    columns,
    data,
    loading,
    onSearch,
    filters,
    selectable = false,
    getRowId = (row) => row.id,
    selectedIds = [],
    onSelectionChange = () => {},
    toolbarActions
}) => {
    const allIds = data.map(getRowId).filter(Boolean);
    const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.includes(id));
    const someSelected = selectedIds.length > 0;

    const toggleAll = () => {
        if (allSelected) {
            onSelectionChange([]);
        } else {
            onSelectionChange([...allIds]);
        }
    };

    const toggleRow = (id) => {
        if (selectedIds.includes(id)) {
            onSelectionChange(selectedIds.filter((s) => s !== id));
        } else {
            onSelectionChange([...selectedIds, id]);
        }
    };

    const displayColumns = selectable
        ? [{ header: '', accessor: '__select__', width: 40 }, ...columns]
        : columns;
    const colSpan = displayColumns.length;

    return (
        <div className="card h-full flex flex-col p-0 overflow-hidden">
            <div className="p-6 border-b border-white/5 flex flex-wrap items-center justify-between gap-4">
                <div className="relative w-full md:w-80">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" size={18} />
                    <input
                        type="text"
                        placeholder="검색어를 입력하세요..."
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-10 pr-4 focus:outline-none focus:border-primary transition-all text-sm"
                        onChange={(e) => onSearch(e.target.value)}
                    />
                </div>
                <div className="flex items-center gap-3">
                    {filters}
                    {selectable && someSelected && toolbarActions && (
                        <div className="flex items-center gap-2">
                            {toolbarActions(selectedIds, () => onSelectionChange([]))}
                        </div>
                    )}
                </div>
            </div>

            <div className="overflow-x-auto flex-1">
                <table className="w-full text-left text-sm">
                    <thead className="bg-white/5 text-text-muted font-medium">
                        <tr>
                            {displayColumns.map((col, i) => (
                                <th key={i} className="px-6 py-4 border-b border-white/5" style={col.width ? { width: col.width } : undefined}>
                                    {col.accessor === '__select__' ? (
                                        <input
                                            type="checkbox"
                                            checked={allSelected}
                                            onChange={toggleAll}
                                            className="rounded border-white/20 bg-white/5"
                                        />
                                    ) : (
                                        col.header
                                    )}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {loading ? (
                            <tr>
                                <td colSpan={colSpan} className="px-6 py-10 text-center text-text-muted">
                                    데이터를 불러오는 중...
                                </td>
                            </tr>
                        ) : data.length === 0 ? (
                            <tr>
                                <td colSpan={colSpan} className="px-6 py-10 text-center text-text-muted">
                                    조회 결과가 없습니다.
                                </td>
                            </tr>
                        ) : (
                            data.map((row, i) => {
                                const rowId = getRowId(row);
                                return (
                                    <tr key={rowId ?? i} className="hover:bg-white/5 transition-all">
                                        {displayColumns.map((col, j) => (
                                            <td key={j} className="px-6 py-4 whitespace-nowrap">
                                                {col.accessor === '__select__' ? (
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedIds.includes(rowId)}
                                                        onChange={() => toggleRow(rowId)}
                                                        className="rounded border-white/20 bg-white/5"
                                                    />
                                                ) : col.render ? (
                                                    col.render(row)
                                                ) : (
                                                    row[col.accessor]
                                                )}
                                            </td>
                                        ))}
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>

            <div className="p-6 border-t border-white/5 flex items-center justify-between bg-white/5">
                <span className="text-xs text-text-muted">전체 {data.length}개 항목</span>
                <div className="flex items-center gap-2">
                    <button className="p-2 hover:bg-white/10 rounded-lg transition-all disabled:opacity-30" disabled>
                        <ChevronLeft size={16} />
                    </button>
                    <div className="flex items-center gap-1">
                        <span className="w-8 h-8 flex items-center justify-center bg-primary rounded-lg text-xs font-bold">1</span>
                    </div>
                    <button className="p-2 hover:bg-white/10 rounded-lg transition-all disabled:opacity-30" disabled>
                        <ChevronRight size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DataTable;
