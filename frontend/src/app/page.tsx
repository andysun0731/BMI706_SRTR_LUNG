'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ComposableMap, Geographies, Geography, Marker, Line } from 'react-simple-maps';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { getOPOs, getMapConnections } from '@/lib/api';

const geoUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

interface OPO {
    OPO: string;
    Transplants: number;
    DCU_Rate: number;
    OPO_Lat: number;
    OPO_Lon: number;
}

interface Connection {
    OPO: string;
    Center: string;
    Transplants: number;
    OPO_Lat: number;
    OPO_Lon: number;
    Center_Lat: number;
    Center_Lon: number;
}

function getDCUColor(rate: number): string {
    if (rate <= 0.5) {
        const t = rate / 0.5;
        return `rgb(${Math.round(33 + 120 * t)}, ${Math.round(102 + 10 * t)}, ${Math.round(172 - 1 * t)})`;
    } else {
        const t = (rate - 0.5) / 0.5;
        return `rgb(${Math.round(153 + 25 * t)}, ${Math.round(112 - 88 * t)}, ${Math.round(171 - 128 * t)})`;
    }
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function generateYearMonths(): { value: number; label: string }[] {
    const result: { value: number; label: string }[] = [];
    for (let year = 2018; year <= 2024; year++) {
        for (let month = 1; month <= 12; month++) {
            result.push({ value: year * 100 + month, label: `${MONTHS[month - 1]} ${year}` });
        }
    }
    return result;
}

const ALL_YEAR_MONTHS = generateYearMonths();
const CAS_INDEX = ALL_YEAR_MONTHS.findIndex(ym => ym.value === 202303);

export default function MapPage() {
    const [selectedRange, setSelectedRange] = useState<[number, number]>([0, ALL_YEAR_MONTHS.length - 1]);
    const [selectedOPO, setSelectedOPO] = useState<string | null>(null);
    const [hoveredOPO, setHoveredOPO] = useState<OPO | null>(null);

    const startYM = ALL_YEAR_MONTHS[selectedRange[0]].value;
    const endYM = ALL_YEAR_MONTHS[selectedRange[1]].value;

    const { data: opos = [], isLoading } = useQuery<OPO[]>({
        queryKey: ['opos', startYM, endYM],
        queryFn: () => getOPOs({
            start_year: Math.floor(startYM / 100),
            end_year: Math.floor(endYM / 100),
            start_month: startYM % 100,
            end_month: endYM % 100
        }),
    });

    const { data: connections = [] } = useQuery<Connection[]>({
        queryKey: ['connections', startYM, endYM, selectedOPO],
        queryFn: () => getMapConnections({
            start_year: Math.floor(startYM / 100),
            end_year: Math.floor(endYM / 100),
            start_month: startYM % 100,
            end_month: endYM % 100,
            opo: selectedOPO || undefined
        }),
        enabled: !!selectedOPO,
    });

    const metrics = useMemo(() => {
        const totalTransplants = opos.reduce((sum, o) => sum + o.Transplants, 0);
        const avgDCU = opos.length > 0 ? opos.reduce((sum, o) => sum + o.DCU_Rate, 0) / opos.length : 0;
        return { totalOPOs: opos.length, totalTransplants, avgDCU };
    }, [opos]);

    const startLabel = ALL_YEAR_MONTHS[selectedRange[0]].label;
    const endLabel = ALL_YEAR_MONTHS[selectedRange[1]].label;

    return (
        <div className="max-w-6xl mx-auto animate-fade-in">
            {/* Hero Section */}
            <div className="text-center py-16">
                <h1 className="text-[56px] font-semibold text-[#1d1d1f] leading-tight tracking-tight">
                    OPO Connections
                </h1>
                <p className="text-[21px] text-[#86868b] mt-4 max-w-2xl mx-auto leading-relaxed">
                    Explore transplant center connections across the United States.
                    Click on any OPO to reveal its network.
                </p>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-3 gap-6 mb-12">
                {[
                    { label: 'OPOs', value: metrics.totalOPOs },
                    { label: 'Total Transplants', value: metrics.totalTransplants.toLocaleString() },
                    { label: 'Avg DCU Rate', value: `${(metrics.avgDCU * 100).toFixed(1)}%` }
                ].map((stat, i) => (
                    <div key={i} className="apple-card p-8 text-center">
                        <p className="text-[40px] font-semibold text-[#1d1d1f]">{stat.value}</p>
                        <p className="text-[14px] text-[#86868b] mt-1">{stat.label}</p>
                    </div>
                ))}
            </div>

            {/* Date Range */}
            <div className="apple-card p-8 mb-8">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h3 className="text-[17px] font-semibold text-[#1d1d1f]">Date Range</h3>
                        <p className="text-[14px] text-[#86868b] mt-1">{startLabel} — {endLabel}</p>
                    </div>
                </div>

                {/* CAS Marker */}
                <div className="relative h-6 mb-3 mx-1">
                    <div
                        className="absolute text-center"
                        style={{ left: `${(CAS_INDEX / (ALL_YEAR_MONTHS.length - 1)) * 100}%`, transform: 'translateX(-50%)' }}
                    >
                        <div className="text-[11px] font-medium text-[#ff3b30]">CAS Implementation</div>
                        <div className="text-[10px] text-[#ff3b30]">▼</div>
                    </div>
                </div>

                <div className="px-1">
                    <Slider
                        range
                        min={0}
                        max={ALL_YEAR_MONTHS.length - 1}
                        value={selectedRange}
                        onChange={(v) => setSelectedRange(v as [number, number])}
                        trackStyle={[{ backgroundColor: '#0071e3', height: 4 }]}
                        handleStyle={[
                            { backgroundColor: 'white', borderColor: '#0071e3', borderWidth: 2, height: 20, width: 20, marginTop: -8, boxShadow: '0 2px 8px rgba(0,0,0,0.15)' },
                            { backgroundColor: 'white', borderColor: '#0071e3', borderWidth: 2, height: 20, width: 20, marginTop: -8, boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }
                        ]}
                        railStyle={{ backgroundColor: '#e8e8ed', height: 4 }}
                    />
                </div>

                <div className="flex justify-between text-[11px] text-[#86868b] mt-3 px-1">
                    <span>Jan 2018</span>
                    <span>Dec 2024</span>
                </div>
            </div>

            {/* Map */}
            <div className="apple-card overflow-hidden mb-8">
                <div className="flex justify-between items-center p-6 border-b border-gray-100">
                    <h3 className="text-[17px] font-semibold text-[#1d1d1f]">
                        {selectedOPO ? `Connections from ${selectedOPO}` : 'Interactive Map'}
                    </h3>
                    {selectedOPO && (
                        <button
                            onClick={() => setSelectedOPO(null)}
                            className="apple-button-secondary"
                        >
                            Reset
                        </button>
                    )}
                </div>

                {isLoading ? (
                    <div className="h-[600px] flex items-center justify-center bg-[#fbfbfd]">
                        <div className="w-8 h-8 border-2 border-[#0071e3] border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : (
                    <div className="relative h-[600px] bg-[#fbfbfd]">
                        <ComposableMap
                            projection="geoAlbersUsa"
                            projectionConfig={{ scale: 1300 }}
                            style={{ width: '100%', height: '100%' }}
                        >
                            <Geographies geography={geoUrl}>
                                {({ geographies }: { geographies: any[] }) =>
                                    geographies.map((geo: any) => (
                                        <Geography
                                            key={geo.rsmKey}
                                            geography={geo}
                                            fill="#e8e8ed"
                                            stroke="#ffffff"
                                            strokeWidth={1}
                                            style={{
                                                default: { outline: 'none' },
                                                hover: { outline: 'none' },
                                                pressed: { outline: 'none' }
                                            }}
                                        />
                                    ))
                                }
                            </Geographies>

                            {selectedOPO && connections.map((conn, i) => (
                                <Line
                                    key={`line-${i}`}
                                    from={[conn.OPO_Lon, conn.OPO_Lat]}
                                    to={[conn.Center_Lon, conn.Center_Lat]}
                                    stroke="#0071e3"
                                    strokeWidth={Math.max(1, Math.log(conn.Transplants + 1) / 2)}
                                    strokeOpacity={0.4}
                                />
                            ))}

                            {selectedOPO && connections.map((conn, i) => (
                                <Marker key={`center-${i}`} coordinates={[conn.Center_Lon, conn.Center_Lat]}>
                                    <circle r={4} fill="#34c759" stroke="white" strokeWidth={1.5} />
                                </Marker>
                            ))}

                            {opos.map((opo, i) => {
                                const r = Math.sqrt(opo.Transplants) / 3 + 5;
                                const isSelected = selectedOPO === opo.OPO;
                                return (
                                    <Marker
                                        key={i}
                                        coordinates={[opo.OPO_Lon, opo.OPO_Lat]}
                                        onClick={() => setSelectedOPO(opo.OPO === selectedOPO ? null : opo.OPO)}
                                        onMouseEnter={() => setHoveredOPO(opo)}
                                        onMouseLeave={() => setHoveredOPO(null)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <circle
                                            r={r}
                                            fill={getDCUColor(opo.DCU_Rate)}
                                            stroke="white"
                                            strokeWidth={2}
                                            opacity={selectedOPO && !isSelected ? 0.15 : 0.85}
                                            style={{ transition: 'all 0.3s ease' }}
                                        />
                                    </Marker>
                                );
                            })}
                        </ComposableMap>

                        {/* Legend */}
                        <div className="absolute top-6 right-6 bg-white/95 backdrop-blur-sm p-4 rounded-2xl shadow-lg">
                            <p className="text-[11px] font-medium text-[#1d1d1f] mb-3">DCU Rate</p>
                            <div className="flex">
                                <div className="w-3 h-24 rounded-full" style={{
                                    background: 'linear-gradient(to bottom, #b2182b 0%, #9970ab 50%, #2166ac 100%)'
                                }} />
                                <div className="flex flex-col justify-between ml-2 text-[10px] text-[#86868b] h-24">
                                    <span>100%</span>
                                    <span>50%</span>
                                    <span>0%</span>
                                </div>
                            </div>
                        </div>

                        {/* Tooltip */}
                        {hoveredOPO && (
                            <div className="absolute bottom-6 left-6 bg-white/95 backdrop-blur-sm px-5 py-4 rounded-2xl shadow-lg">
                                <p className="text-[15px] font-semibold text-[#1d1d1f]">{hoveredOPO.OPO}</p>
                                <p className="text-[13px] text-[#86868b] mt-1">
                                    {hoveredOPO.Transplants.toLocaleString()} transplants
                                </p>
                                <p className="text-[13px] text-[#86868b]">
                                    {(hoveredOPO.DCU_Rate * 100).toFixed(1)}% DCU rate
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Connections List */}
            {selectedOPO && connections.length > 0 && (
                <div className="apple-card p-8 mb-8">
                    <h3 className="text-[17px] font-semibold text-[#1d1d1f] mb-6">
                        {connections.length} Connected Centers
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {connections
                            .sort((a, b) => b.Transplants - a.Transplants)
                            .slice(0, 12)
                            .map((conn, i) => (
                                <div key={i} className="bg-[#f5f5f7] rounded-xl p-4">
                                    <p className="text-[14px] font-medium text-[#1d1d1f] truncate">{conn.Center}</p>
                                    <p className="text-[12px] text-[#86868b] mt-1">{conn.Transplants} transplants</p>
                                </div>
                            ))}
                    </div>
                </div>
            )}
        </div>
    );
}
