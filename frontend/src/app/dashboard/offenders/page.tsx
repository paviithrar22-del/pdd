"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { analyticsApi } from "@/services/api";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { Users, ChevronRight, TrendingUp, TrendingDown, Minus, ArrowLeft, Clock } from "lucide-react";

const trendIcon: Record<string, JSX.Element> = {
  increasing: <TrendingUp className="w-4 h-4 text-red-400" />,
  decreasing: <TrendingDown className="w-4 h-4 text-green-400" />,
  stable: <Minus className="w-4 h-4 text-zinc-400" />,
};

const trendLabel: Record<string, string> = {
  increasing: "text-red-400",
  decreasing: "text-green-400",
  stable: "text-zinc-400",
};

const severityDot: Record<string, string> = {
  Safe: "bg-green-400",
  Moderate: "bg-yellow-400",
  High: "bg-orange-400",
  Critical: "bg-red-400",
};

export default function OffendersPage() {
  const [offenders, setOffenders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    analyticsApi.offenders()
      .then(r => { setOffenders(r.data.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const openDetail = async (username: string) => {
    setSelected(username);
    setDetail(null);
    setDetailLoading(true);
    try {
      const r = await analyticsApi.offenderDetail(username);
      setDetail(r.data.data);
    } catch {}
    setDetailLoading(false);
  };

  const maxViolations = offenders.length > 0 ? Math.max(...offenders.map((o: any) => o.violations)) : 1;

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, x: -15 }} animate={{ opacity: 1, x: 0 }}>
        <h1 className="text-3xl font-black text-white tracking-tight drop-shadow-md">Offenders Intelligence</h1>
        <p className="text-[hsl(var(--muted-foreground))] text-sm mt-1.5 font-medium">Deep-dive on repeat harassment sources and risk vectors</p>
      </motion.div>

      <AnimatePresence mode="wait">
      {selected ? (
        /* Detail View */
        <motion.div 
          key="detail" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
          className="space-y-6"
        >
          <button
            onClick={() => { setSelected(null); setDetail(null); }}
            className="flex items-center gap-2 text-sm font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Return to Leaderboard
          </button>

          {detailLoading ? (
            <div className="glass-panel rounded-2xl p-8 animate-pulse h-64" />
          ) : detail ? (
            <>
              {/* Header card */}
              <div className="glass-panel rounded-2xl p-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/10 blur-3xl pointer-events-none rounded-full" />
                <div className="flex flex-wrap items-start justify-between gap-4 relative z-10">
                  <div>
                    <p className="text-xs text-cyan-400 font-bold uppercase tracking-widest mb-1.5 drop-shadow-[0_0_8px_rgba(6,182,212,0.5)]">Target Identity</p>
                    <h2 className="text-3xl font-black text-white">@{detail.username}</h2>
                  </div>
                  <div className="scale-110 origin-top-right"><SeverityBadge level={detail.offender_level} /></div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-5 mt-8 relative z-10">
                  <div className="rounded-xl bg-black/40 border border-white/5 p-5 shadow-inner">
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-widest mb-1.5">Total Violations</p>
                    <p className="text-3xl font-black text-white">{detail.total_violations}</p>
                  </div>
                  <div className="rounded-xl bg-black/40 border border-white/5 p-5 shadow-inner">
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-widest mb-1.5">Offender Score</p>
                    <p className="text-3xl font-black text-white">{detail.offender_score}<span className="text-sm text-[hsl(var(--muted-foreground))] font-medium">/100</span></p>
                  </div>
                  <div className="rounded-xl bg-black/40 border border-white/5 p-5 shadow-inner">
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-widest mb-1.5">Risk Level</p>
                    <p className={`text-lg font-bold mt-1 ${detail.offender_level === 'Critical' ? 'text-red-400 glow-text-red' : 'text-white'}`}>{detail.offender_level}</p>
                  </div>
                  <div className="rounded-xl bg-black/40 border border-white/5 p-5 shadow-inner">
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-widest mb-1.5">7-Day Trend</p>
                    <div className="flex items-center gap-2 mt-2">
                      {trendIcon[detail.risk_trend] ?? <Minus className="w-5 h-5 text-zinc-400" />}
                      <span className={`text-base font-bold capitalize ${trendLabel[detail.risk_trend] ?? "text-zinc-400"}`}>
                        {detail.risk_trend}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Offense history */}
              <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-5 border-b border-white/[0.05] bg-white/[0.01]">
                  <h3 className="text-white font-bold tracking-wide">Historical Timeline</h3>
                </div>
                <div className="divide-y divide-white/[0.05] max-h-96 overflow-y-auto custom-scrollbar">
                  {detail.offense_history.map((v: any, idx: number) => (
                    <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.05 }} key={v.id} className="flex items-center justify-between px-6 py-4 hover:bg-white/[0.01] transition-colors">
                      <div className="flex items-center gap-4">
                        <span className={`w-3 h-3 rounded-full shrink-0 shadow-[0_0_10px_currentColor] ${severityDot[v.severity] ?? "bg-zinc-400"}`} />
                        <div>
                          <p className="text-sm font-bold text-white capitalize tracking-wide">{v.violation_type?.replace("_", " ")}</p>
                          <p className="text-xs text-[hsl(var(--muted-foreground))] flex items-center gap-1.5 mt-1 font-mono">
                            <Clock className="w-3.5 h-3.5 opacity-70" />
                            {v.created_at ? new Date(v.created_at).toLocaleString() : "—"}
                          </p>
                        </div>
                      </div>
                      <SeverityBadge level={v.severity} />
                    </motion.div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="text-[hsl(var(--muted-foreground))] text-sm">Could not load offender data.</p>
          )}
        </motion.div>
      ) : loading ? (
        <div className="space-y-3">
          {[...Array(8)].map((_, i) => <div key={i} className="h-16 rounded-2xl glass-panel animate-pulse" />)}
        </div>
      ) : offenders.length === 0 ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel rounded-2xl p-16 text-center border-dashed">
          <Users className="w-12 h-12 text-[hsl(var(--muted-foreground))] opacity-50 mx-auto mb-4" />
          <p className="text-[hsl(var(--muted-foreground))] font-medium text-lg">No threat entities tracked yet.</p>
        </motion.div>
      ) : (
        /* Leaderboard — card list (mobile friendly) */
        <motion.div 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
          className="glass-panel rounded-2xl overflow-hidden relative"
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/5 blur-3xl pointer-events-none" />
          {/* Desktop Table Header */}
          <div className="hidden md:grid md:grid-cols-[40px_1fr_100px_130px_1fr_40px] border-b border-white/[0.05] bg-white/[0.01] px-5 py-3">
            <span className="text-xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-wider">Rank</span>
            <span className="text-xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-wider">Identity</span>
            <span className="text-xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-wider">Violations</span>
            <span className="text-xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-wider">Risk Level</span>
            <span className="text-xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-wider">Threat Bar</span>
            <span />
          </div>

          <div className="divide-y divide-white/[0.05] relative z-10">
            {offenders.map((o, i) => (
              <motion.div
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                key={o.username}
                className="px-5 py-4 hover:bg-white/[0.03] cursor-pointer transition-colors group"
                onClick={() => openDetail(o.username)}
              >
                {/* Mobile layout */}
                <div className="md:hidden flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-[hsl(var(--muted-foreground))] font-mono text-sm shrink-0">{i + 1}</span>
                    <div className="min-w-0">
                      <p className="text-cyan-400 font-bold text-sm truncate drop-shadow-[0_0_8px_rgba(6,182,212,0.5)]">@{o.username}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-white text-xs font-bold">{o.violations} violations</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-black/40 overflow-hidden mt-2 w-32">
                        <motion.div
                          initial={{ width: 0 }} animate={{ width: `${Math.min((o.violations / maxViolations) * 100, 100)}%` }}
                          transition={{ duration: 1, ease: "easeOut" }}
                          className="h-full bg-gradient-to-r from-red-500/80 to-red-400 rounded-full"
                        />
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <SeverityBadge level={o.risk_level} />
                    <ChevronRight className="w-4 h-4 text-[hsl(var(--muted-foreground))] group-hover:text-cyan-400 transition-colors" />
                  </div>
                </div>

                {/* Desktop layout */}
                <div className="hidden md:grid md:grid-cols-[40px_1fr_100px_130px_1fr_40px] items-center">
                  <span className="text-sm text-[hsl(var(--muted-foreground))] font-mono">{i + 1}</span>
                  <span className="text-sm text-cyan-400 font-bold drop-shadow-[0_0_8px_rgba(6,182,212,0.5)]">@{o.username}</span>
                  <span className="text-sm text-white font-black">{o.violations}</span>
                  <span><SeverityBadge level={o.risk_level} /></span>
                  <div className="pr-8">
                    <div className="h-2 rounded-full bg-black/40 overflow-hidden shadow-inner border border-white/5">
                      <motion.div
                        initial={{ width: 0 }} animate={{ width: `${Math.min((o.violations / maxViolations) * 100, 100)}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        className="h-full bg-gradient-to-r from-red-500/80 to-red-400 rounded-full shadow-[0_0_10px_rgba(239,68,68,0.8)]"
                      />
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-[hsl(var(--muted-foreground))] group-hover:text-cyan-400 transition-colors justify-self-end" />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

      )}
      </AnimatePresence>
    </div>
  );
}
