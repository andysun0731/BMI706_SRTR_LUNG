'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getSurvivalCurves, getSurvivalStats, getSurvivalOPOs } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#0071e3', '#ff9500', '#34c759', '#ff3b30', '#af52de', '#5856d6'];

interface SurvivalData {
    GraftTime: number;
    survival_prob: number;
    Group: string;
}

interface StatData {
    OPO: string;
    P_Value: number;
}

export default function SurvivalPage() {
    const [selectedOPOs, setSelectedOPOs] = useState<string[]>([]);
    const [showNationwide, setShowNationwide] = useState(true);

    const { data: availableOPOs = { opos: [] } } = useQuery({
        queryKey: ['survivalOPOs'],
        queryFn: getSurvivalOPOs,
    });

    const { data: curveData = [], isLoading } = useQuery<SurvivalData[]>({
        queryKey: ['survivalCurves', selectedOPOs, showNationwide],
        queryFn: () => getSurvivalCurves({ opos: selectedOPOs, include_nationwide: showNationwide }),
    });

    const { data: statsData = [] } = useQuery<StatData[]>({
        queryKey: ['survivalStats', selectedOPOs],
        queryFn: () => getSurvivalStats(selectedOPOs),
        enabled: selectedOPOs.length > 0,
    });

    const groups = useMemo(() => {
        return Array.from(new Set(curveData.map(d => d.Group)));
    }, [curveData]);

    const toggleOPO = (opo: string) => {
        setSelectedOPOs(prev =>
            prev.includes(opo) ? prev.filter(o => o !== opo) : [...prev, opo]
        );
    };

    return (
        <div className="max-w-6xl mx-auto animate-fade-in">
            {/* Hero */}
            <div className="text-center py-16">
                <h1 className="text-[56px] font-semibold text-[#1d1d1f] leading-tight tracking-tight">
                    Survival Analysis
                </h1>
                <p className="text-[21px] text-[#86868b] mt-4 max-w-2xl mx-auto leading-relaxed">
                    Kaplan-Meier survival curves comparing 5-year outcomes across OPOs.
                </p>
            </div>

            {/* Controls */}
            <div className="apple-card p-6 mb-8">
                <div className="flex items-center justify-between">
                    <label className="flex items-center space-x-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={showNationwide}
                            onChange={(e) => setShowNationwide(e.target.checked)}
                            className="w-5 h-5 rounded border-gray-300 text-[#0071e3] focus:ring-[#0071e3]"
                        />
                        <span className="text-[14px] text-[#1d1d1f]">Show Nationwide Reference</span>
                    </label>
                    {selectedOPOs.length > 0 && (
                        <button onClick={() => setSelectedOPOs([])} className="apple-button-secondary">
                            Clear ({selectedOPOs.length})
                        </button>
                    )}
                </div>
            </div>

            {/* OPO Selection */}
            <div className="apple-card p-6 mb-8">
                <h3 className="text-[17px] font-semibold text-[#1d1d1f] mb-4">Select OPOs to Compare</h3>
                <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto">
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
            <div className="apple-card p-8 mb-8">
                <h3 className="text-[17px] font-semibold text-[#1d1d1f] mb-6">Kaplan-Meier Curves</h3>

                {isLoading ? (
                    <div className="h-[400px] flex items-center justify-center">
                        <div className="w-8 h-8 border-2 border-[#0071e3] border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : curveData.length === 0 ? (
                    <div className="h-[400px] flex items-center justify-center text-[#86868b]">
                        Select OPOs or enable Nationwide to view curves
                    </div>
                ) : (
                    <div className="h-[400px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                                <XAxis
                                    dataKey="GraftTime"
                                    type="number"
                                    domain={[0, 1825]}
                                    tickFormatter={(v) => `${Math.round(v / 365)}y`}
                                    stroke="#86868b"
                                    fontSize={12}
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
                                <Legend />
                                {groups.map((group, i) => {
                                    const data = curveData.filter(d => d.Group === group);
                                    const color = group === 'Nationwide' ? '#86868b' : COLORS[i % COLORS.length];
                                    return (
                                        <Line
                                            key={group}
                                            data={data}
                                            type="stepAfter"
                                            dataKey="survival_prob"
                                            name={group}
                                            stroke={color}
                                            strokeWidth={group === 'Nationwide' ? 2 : 2}
                                            strokeDasharray={group === 'Nationwide' ? '5 5' : '0'}
                                            dot={false}
                                        />
                                    );
                                })}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </div>

            {/* Stats */}
            {statsData.length > 0 && (
                <div className="apple-card p-8">
                    <h3 className="text-[17px] font-semibold text-[#1d1d1f] mb-2">Log-Rank Test Results</h3>
                    <p className="text-[13px] text-[#86868b] mb-6">P-values comparing each OPO against rest of nation</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {statsData.map((stat) => (
                            <div
                                key={stat.OPO}
                                className={`p-4 rounded-xl text-center ${stat.P_Value < 0.05 ? 'bg-red-50 border border-red-200' : 'bg-[#f5f5f7]'
                                    }`}
                            >
                                <p className="text-[15px] font-semibold text-[#1d1d1f]">{stat.OPO}</p>
                                <p className={`text-[13px] mt-1 ${stat.P_Value < 0.05 ? 'text-[#ff3b30] font-medium' : 'text-[#86868b]'}`}>
                                    p = {stat.P_Value.toFixed(4)}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
