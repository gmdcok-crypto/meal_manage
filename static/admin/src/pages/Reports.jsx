import React from 'react';
import { FileSpreadsheet, Calendar, Users, Briefcase } from 'lucide-react';

const Reports = () => {
    const reports = [
        { title: '일일 식수 리포트', desc: '특정 날짜의 식사구분별/메뉴별 식수 통계', icon: <Calendar size={24} />, color: 'text-primary' },
        { title: '월별 정산 리포트', desc: '한 달간의 총 식수 및 금액 합계 (엑셀 출력)', icon: <FileSpreadsheet size={24} />, color: 'text-success' },
        { title: '부서별 통계', desc: '부서별 식사 이용 현황 및 비용 분석', icon: <Briefcase size={24} />, color: 'text-accent' },
        { title: '개인별 이용 명세', desc: '특정 사원의 기간 내 모든 식사 기록', icon: <Users size={24} />, color: 'text-warning' },
    ];

    const ReportCard = ({ report }) => (
        <div className="card hover:scale-[1.02] cursor-pointer group transition-all">
            <div className="flex items-start gap-5">
                <div className={`p-4 rounded-2xl bg-white/5 group-hover:bg-white/10 transition-all ${report.color}`}>
                    {report.icon}
                </div>
                <div className="flex-1">
                    <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-all">{report.title}</h3>
                    <p className="text-text-muted text-sm leading-relaxed">{report.desc}</p>
                </div>
            </div>
            <div className="mt-8 flex justify-between items-center">
                <div className="flex gap-2">
                    <input type="month" className="bg-white/5 border border-white/10 rounded-lg px-3 py-1 text-xs focus:outline-none" />
                </div>
                <button className="btn btn-primary p-2 flex items-center justify-center min-w-[40px]" title="엑셀 다운로드">
                    <FileSpreadsheet size={20} />
                </button>
            </div>
        </div>
    );

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-bold">리포트 및 정산</h2>
                <p className="text-text-muted text-sm mt-1">정산용 월별 리포트 및 각종 집계 데이터를 엑셀로 출력할 수 있습니다.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {reports.map((r, i) => <ReportCard key={i} report={r} />)}
            </div>

            <div className="card bg-primary bg-opacity-5 border-primary border-opacity-20 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center text-white">
                        <FileSpreadsheet size={24} />
                    </div>
                    <div>
                        <h4 className="font-bold text-lg">이번 달 간편 정산</h4>
                        <p className="text-sm text-text-muted">2024년 2월 현재 총 1,240식 (3,520,000원)</p>
                    </div>
                </div>
                <button className="btn btn-primary p-3" title="즉시 다운로드">
                    <FileSpreadsheet size={24} />
                </button>
            </div>
        </div>
    );
};

export default Reports;
