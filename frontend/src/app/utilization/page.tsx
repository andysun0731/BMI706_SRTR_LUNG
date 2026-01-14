'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getUtilizationSummary, getNationalUtilization, getUtilizationOPOs } from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';

interface UtilizationData {
    DON_OPO: string;
    Total_Donors: number;
    Used_Donors: number;
    Utilization_Rate: number;
}

interface NationalData {
    national_utilization: number;
    total_donors: number;
    used_donors: number;
}

export default function UtilizationPage() {
    const [casPeriod, setCasPeriod] = useState<string>('All');
    const [donorType, setDonorType] = useState<string>('All');
    const [selectedOPOs, setSelectedOPOs] = useState<string[]>([]);

    const { data: availableOPOs = { opos: [] } } = useQuery({
        queryKey: ['utilizationOPOs'],
        queryFn: getUtilizationOPOs,
    });

    const { data: nationalData } = useQuery<NationalData>({
        queryKey: ['nationalUtilization', casPeriod, donorType],
        queryFn: () => getNationalUtilization({ cas_period: casPeriod, donor_type: donorType }),
    });

    const { data: utilizationData = [], isLoading } = useQuery<UtilizationData[]>({
        queryKey: ['utilization', casPeriod, donorType, selectedOPOs],
        queryFn: () => getUtilizationSummary({
            cas_period: casPeriod,
            donor_type: donorType,
            opos: selectedOPOs.length > 0 ? selectedOPOs : undefined
        }),
    });

    const chartData = useMemo(() => {
        const nationalRow = {
            DON_OPO: 'National',
            Utilization_Rate: nationalData?.national_utilization || 0,
            isNational: true,
        };
        return [nationalRow, ...utilizationData.slice(0, 12).map(d => ({ ...d, isNational: false }))];
    }, [utilizationData, nationalData]);

    const toggleOPO = (opo: string) => {
        setSelectedOPOs(prev =>
            prev.includes(opo) ? prev.filter(o => o !== opo) : [...prev, opo]
        );
    };

    const selectedUtil = useMemo(() => {
        if (selectedOPOs.length === 0) return null;
        const selected = utilizationData.filter(d => selectedOPOs.includes(d.DON_OPO));
        const totalUsed = selected.reduce((sum, d) => sum + d.Used_Donors, 0);
        const totalDonors = selected.reduce((sum, d) => sum + d.Total_Donors, 0);
        return totalDonors > 0 ? totalUsed / totalDonors : 0;
    }, [utilizationData, selectedOPOs]);

    return (
        <div className="max-w-6xl mx-auto animate-fade-in">
            {/* Hero */}
            <div className="text-center py-16">
                <h1 className="text-[56px] font-semibold text-[#1d1d1f] leading-tight tracking-tight">
                    Utilization
                </h1>
                <p className="text-[21px] text-[#86868b] mt-4 max-w-2xl mx-auto leading-relaxed">
                    Compare donor utilization rates across OPOs, pre and post CAS implementation.
                </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-6 mb-12">
                <div className="apple-card p-8 text-center">
                    <p className="text-[40px] font-semibold text-[#1d1d1f]">
                        {nationalData ? `${(nationalData.national_utilization * 100).toFixed(1)}%` : '—'}
                    </p>
                    <p className="text-[14px] text-[#86868b] mt-1">National Rate</p>
                </div>
                <div className="apple-card p-8 text-center">
                    <p className={`text-[40px] font-semibold ${selectedUtil !== null
                            ? selectedUtil > (nationalData?.national_utilization || 0) ? 'text-[#34c759]' : 'text-[#ff3b30]'
                            : 'text-[#86868b]'
                        }`}>
                        {selectedUtil !== null ? `${(selectedUtil * 100).toFixed(1)}%` : '—'}
                    </p>
                    <p className="text-[14px] text-[#86868b] mt-1">Selected OPOs</p>
                </div>
                <div className="apple-card p-8 text-center">
                    <p className="text-[40px] font-semibold text-[#1d1d1f]">
                        {nationalData?.total_donors?.toLocaleString() || '—'}
                    </p>
                    <p className="text-[14px] text-[#86868b] mt-1">Total Donors</p>
                </div>
            </div>

            {/* Filters */}
            <div className="apple-card p-6 mb-8">
                <div className="flex flex-wrap items-center gap-8">
                    <div>
                        <p className="text-[12px] text-[#86868b] mb-2 uppercase tracking-wide">CAS Period</p>
                        <div className="flex gap-2">
                            {['All', 'Pre-CAS', 'Post-CAS'].map((p) => (
                                <button
                                    key={p}
                                    onClick={() => setCasPeriod(p)}
                                    className={`px-4 py-2 rounded-full text-[13px] font-medium transition-all ${casPeriod === p
                                            ? 'bg-[#0071e3] text-white'
                                            : 'bg-[#f5f5f7] text-[#1d1d1f] hover:bg-[#e8e8ed]'
                                        }`}
                                >
                                    {p}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div>
                        <p className="text-[12px] text-[#86868b] mb-2 uppercase tracking-wide">Donor Type</p>
                        <div className="flex gap-2">
                            {['All', 'DBD', 'DCD'].map((t) => (
                                <button
                                    key={t}
                                    onClick={() => setDonorType(t)}
                                    className={`px-4 py-2 rounded-full text-[13px] font-medium transition-all ${donorType === t
                                            ? 'bg-[#0071e3] text-white'
                                            : 'bg-[#f5f5f7] text-[#1d1d1f] hover:bg-[#e8e8ed]'
                                        }`}
                                >
                                    {t}
                                </button>
                            ))}
                        </div>
                    </div>
                    {selectedOPOs.length > 0 && (
                        <button onClick={() => setSelectedOPOs([])} className="apple-button-secondary ml-auto">
                            Clear ({selectedOPOs.length})
                        </button>
                    )}
                </div>
            </div>

            {/* OPO Selection */}
            <div className="apple-card p-6 mb-8">
                <h3 className="text-[17px] font-semibold text-[#1d1d1f] mb-4">Select OPOs</h3>
                <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
                    {availableOPOs.opos?.map((opo: string) => (
                        <button
                            key={opo}
                            onClick={() => toggleOPO(opo)}
                            className={`px-4 py-2 rounded-full text-[13px] font-medium transition-all ${selectedOPOs.includes(opo)
                                    ? 'bg-[#0071e3] text-white'
                                    : 'bg-[#f5f5f7] text-[#1d1d1f] hover:bg-[#e8e8ed]'
                                }`}
                        >
                            {opo}
                        </button>
                    ))}
                </div>
            </div>

            {/* Chart */}
            <div className="apple-card p-8">
                <h3 className="text-[17px] font-semibold text-[#1d1d1f] mb-6">Utilization Rates</h3>

                {isLoading ? (
                    <div className="h-[400px] flex items-center justify-center">
                        <div className="w-8 h-8 border-2 border-[#0071e3] border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : (
                    <div className="h-[400px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                                <XAxis
                                    dataKey="DON_OPO"
                                    angle={-45}
                                    textAnchor="end"
                                    height={70}
                                    stroke="#86868b"
                                    fontSize={11}
                                />
                                <YAxis
                                    domain={[0, 1]}
                                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                                    stroke="#86868b"
                                    fontSize={12}
                                />
                                <Tooltip
                                    contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }}
                                    formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
                                />
                                {nationalData && (
                                    <ReferenceLine
                                        y={nationalData.national_utilization}
                                        stroke="#86868b"
                                        strokeDasharray="5 5"
                                    />
                                )}
                                <Bar dataKey="Utilization_Rate" radius={[6, 6, 0, 0]}>
                                    {chartData.map((entry, i) => (
                                        <Cell key={i} fill={entry.isNational ? '#86868b' : '#0071e3'} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </div>
        </div>
    );
}
