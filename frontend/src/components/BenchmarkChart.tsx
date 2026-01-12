'use client';

import React from 'react';
import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend
} from 'recharts';

interface ComparisonDataPoint {
    comparison_date: string;
    portfolio_return: number;
    index_return: number;
}

interface BenchmarkChartProps {
    data: ComparisonDataPoint[];
    indexName?: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-gray-800 border border-gray-700 p-3 rounded-lg shadow-lg">
                <p className="text-gray-400 text-xs mb-2">{label}</p>
                <div className="space-y-1">
                    {payload.map((entry: any, index: number) => (
                        <p key={index} className="text-sm font-medium" style={{ color: entry.color }}>
                            {entry.name}: {entry.value.toFixed(2)}%
                        </p>
                    ))}
                </div>
            </div>
        );
    }
    return null;
};

export default function BenchmarkChart({ data, indexName = 'Benchmark' }: BenchmarkChartProps) {
    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 bg-gray-900/50 rounded-lg border border-gray-800">
                <p className="text-gray-500 text-sm">No comparison history available</p>
            </div>
        );
    }

    return (
        <div className="w-full h-[300px] mb-6">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
                    <XAxis
                        dataKey="comparison_date"
                        stroke="#9CA3AF"
                        fontSize={11}
                        tickFormatter={(date) => {
                            const d = new Date(date);
                            return `${d.getDate()}/${d.getMonth() + 1}`;
                        }}
                        minTickGap={30}
                    />
                    <YAxis
                        stroke="#9CA3AF"
                        fontSize={11}
                        tickFormatter={(val) => `${val}%`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />

                    <Line
                        type="monotone"
                        dataKey="portfolio_return"
                        name="Portfolio"
                        stroke="#10B981" // Emerald-500
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 6 }}
                    />
                    <Line
                        type="monotone"
                        dataKey="index_return"
                        name={indexName}
                        stroke="#F59E0B" // Amber-500
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 6 }}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
