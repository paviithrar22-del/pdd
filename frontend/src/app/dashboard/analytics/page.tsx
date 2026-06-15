"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { analyticsApi } from "@/services/api";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, Legend
} from "recharts";

const COLORS = ["#06b6d4", "#ef4444", "#f59e0b", "#8b5cf6", "#10b981", "#f97316"];

const SEVERITY_COLORS: Record<string, string> = {
  Safe: "#10b981",
  Moderate: "#f59e0b",
  High: "#f97316",
  Critical: "#ef4444",
};

const CustomTooltipStyle = {
  background: "#0f1117",
  border: "1px solid #1e2a3a",
  borderRadius: 8,
  color: "#fff",
};

export default function AnalyticsPage() {
  const [trends, setTrends] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsApi.trends()
      .then(r => { setTrends(r.data.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const categoryData = trends?.category_distribution?.filter((d: any) => d.category !== "safe") || [];
  const severityData = (trends?.severity_distribution || []).map((d: any) => ({
    ...d,
    fill: SEVERITY_COLORS[d.severity] || "#06b6d4",
  }));
  const offenderData = trends?.top_offenders?.slice(0, 8) || [];
  const dailyData = trends?.daily_violations || [];

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight">Analytics Intelligence</h1>
          <p className="text-[hsl(var(--muted-foreground))] text-sm mt-1.5 font-medium">Toxicity trends and threat vectors</p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-2xl glass-panel p-6 h-72 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0, x: -15 }} animate={{ opacity: 1, x: 0 }}>
        <h1 className="text-3xl font-black text-white tracking-tight drop-shadow-md">Analytics Intelligence</h1>
        <p className="text-[hsl(var(--muted-foreground))] text-sm mt-1.5 font-medium">Toxicity trends and threat vectors</p>
      </motion.div>

      {/* Daily Violations Trend — full width, most important signal */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="glass-panel rounded-2xl p-7 relative overflow-hidden"
      >
        <div className="absolute -top-20 -left-20 w-64 h-64 bg-cyan-500 opacity-5 rounded-full blur-3xl pointer-events-none" />
        <h2 className="text-white font-bold text-lg mb-6 relative z-10 flex items-center gap-2">
          <div className="w-1.5 h-6 bg-cyan-500 rounded-full" /> Daily Violations (14d Trend)
        </h2>
        {dailyData.length === 0 || dailyData.every((d: any) => d.count === 0) ? (
          <p className="text-[hsl(var(--muted-foreground))] text-sm">No violations recorded yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={dailyData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickFormatter={(v) => v.slice(5)} // MM-DD
              />
              <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={CustomTooltipStyle}
                labelFormatter={(l) => `Date: ${l}`}
                formatter={(v: any) => [v, "Violations"]}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#06b6d4"
                strokeWidth={2}
                dot={{ r: 3, fill: "#06b6d4" }}
                activeDot={{ r: 5, fill: "#22d3ee" }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Distribution */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass-panel rounded-2xl p-7">
          <h2 className="text-white font-bold text-lg mb-6 flex items-center gap-2"><div className="w-1.5 h-6 bg-purple-500 rounded-full" /> Category Distribution</h2>
          {categoryData.length === 0 ? (
            <p className="text-[hsl(var(--muted-foreground))] text-sm">No flagged content yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={categoryData} dataKey="count" nameKey="category" cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={5} label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}>
                  {categoryData.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="rgba(0,0,0,0.2)" />)}
                </Pie>
                <Tooltip contentStyle={CustomTooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Severity Distribution */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass-panel rounded-2xl p-7">
          <h2 className="text-white font-bold text-lg mb-6 flex items-center gap-2"><div className="w-1.5 h-6 bg-amber-500 rounded-full" /> Severity Vectors</h2>
          {severityData.length === 0 ? (
            <p className="text-[hsl(var(--muted-foreground))] text-sm">No data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={severityData}>
                <XAxis dataKey="severity" tick={{ fill: "#6b7280", fontSize: 12, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={CustomTooltipStyle} cursor={{ fill: "rgba(255,255,255,0.02)" }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {severityData.map((entry: any, i: number) => <Cell key={i} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Top Offenders Chart */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="glass-panel rounded-2xl p-5 md:p-7 lg:col-span-2">
          <h2 className="text-white font-bold text-lg mb-6 flex items-center gap-2"><div className="w-1.5 h-6 bg-red-500 rounded-full shadow-[0_0_8px_rgba(239,68,68,0.6)]" /> Top Risk Entities</h2>
          {offenderData.length === 0 ? (
            <p className="text-[hsl(var(--muted-foreground))] text-sm">No violations detected yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(220, offenderData.length * 42)}>
              <BarChart data={offenderData} layout="vertical" margin={{ left: 0, right: 16 }}>
                <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  dataKey="username"
                  type="category"
                  tick={{ fill: "#9ca3af", fontSize: 11, fontWeight: 500 }}
                  width={90}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => v.length > 12 ? v.slice(0, 12) + '…' : v}
                />
                <Tooltip contentStyle={CustomTooltipStyle} cursor={{ fill: "rgba(255,255,255,0.02)" }} />
                <Bar dataKey="violations" fill="url(#colorRed)" radius={[0, 6, 6, 0]} />
                <defs>
                  <linearGradient id="colorRed" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity={0.6}/>
                    <stop offset="100%" stopColor="#ef4444" stopOpacity={1}/>
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>
      </div>
    </div>
  );
}
