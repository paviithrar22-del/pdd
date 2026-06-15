"use client";
import { useEffect, useState, useCallback } from "react";
import { motion, Variants } from "framer-motion";
import { analyticsApi, monitorApi } from "@/services/api";
import { StatCard } from "@/components/ui/StatCard";
import { useWebSocket } from "@/hooks/useWebSocket";
import {
  MessageSquare, AlertTriangle, FileText, ShieldAlert,
  Activity, Bell, TrendingUp, TrendingDown, Minus,
  FlaskConical, Send, Loader2
} from "lucide-react";

interface Overview {
  total_posts: number; total_comments: number; total_messages: number;
  flagged_content: number; critical_alerts: number; unread_alerts: number;
  flagged_today: number; flagged_yesterday: number; percent_change: number;
}

interface IngestResult {
  toxicity_score: number; category: string; severity: string; severity_score?: number;
}

const severityColor: Record<string, string> = {
  Safe: "text-green-400",
  Moderate: "text-yellow-400",
  High: "text-orange-400",
  Critical: "text-red-400",
};

export default function OverviewPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [status, setStatus] = useState<any[]>([]);
  const [monForm, setMonForm] = useState({ instagram_username: "", instagram_password: "", target_profile_url: "" });
  const [monLoading, setMonLoading] = useState(false);
  const [liveEvents, setLiveEvents] = useState<string[]>([]);

  // Manual ingest state
  const [ingestForm, setIngestForm] = useState({ text: "", author: "", content_type: "comment" });
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null);
  const [ingestError, setIngestError] = useState("");

  const load = async () => {
    try {
      const [ov, st] = await Promise.all([analyticsApi.overview(), monitorApi.status()]);
      setOverview(ov.data.data);
      setStatus(st.data.data);
    } catch {}
  };

  useEffect(() => { load(); }, []);

  const onWsMessage = useCallback((data: any) => {
    setLiveEvents(prev => [
      `[${new Date().toLocaleTimeString()}] ${data.event} — ${data.severity || ""}`,
      ...prev.slice(0, 19)
    ]);
    load();
  }, []);
  useWebSocket(onWsMessage);

  const startMonitor = async (e: React.FormEvent) => {
    e.preventDefault(); setMonLoading(true);
    try {
      await monitorApi.start(monForm);
      setMonForm({ instagram_username: "", instagram_password: "" });
      load();
    } catch {}
    setMonLoading(false);
  };

  const stopMonitor = async () => { await monitorApi.stop({}); load(); };
  const running = status.find(s => s.status === "running");

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIngestLoading(true);
    setIngestResult(null);
    setIngestError("");
    try {
      const r = await monitorApi.ingest(ingestForm);
      if (r.data.success) {
        setIngestResult(r.data.data);
        load(); // refresh stats
      } else {
        setIngestError(r.data.message || "Analysis failed");
      }
    } catch (err: any) {
      setIngestError(err?.response?.data?.message || "Request failed");
    }
    setIngestLoading(false);
  };

  const changeBadge = () => {
    if (!overview) return null;
    const p = overview.percent_change;
    if (p > 0) return (
      <span className="flex items-center gap-1 text-xs text-red-400 font-medium">
        <TrendingUp className="w-3 h-3" />{p}% vs yesterday
      </span>
    );
    if (p < 0) return (
      <span className="flex items-center gap-1 text-xs text-green-400 font-medium">
        <TrendingDown className="w-3 h-3" />{Math.abs(p)}% vs yesterday
      </span>
    );
    return (
      <span className="flex items-center gap-1 text-xs text-zinc-400 font-medium">
        <Minus className="w-3 h-3" />No change
      </span>
    );
  };

  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.05 } }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0, x: -15 }} animate={{ opacity: 1, x: 0 }}>
        <h1 className="text-3xl font-black text-white tracking-tight drop-shadow-md">Command Center</h1>
        <p className="text-[hsl(var(--muted-foreground))] text-sm mt-1.5 font-medium">Real-time cyberbullying threat detection & response</p>
      </motion.div>

      {/* Primary stat cards */}
      <motion.div 
        variants={containerVariants} initial="hidden" animate="show"
        className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4"
      >
        <motion.div variants={itemVariants}><StatCard label="Posts" value={overview?.total_posts ?? "—"} icon={FileText} /></motion.div>
        <motion.div variants={itemVariants}><StatCard label="Comments" value={overview?.total_comments ?? "—"} icon={MessageSquare} /></motion.div>
        <motion.div variants={itemVariants}><StatCard label="Messages" value={overview?.total_messages ?? "—"} icon={MessageSquare} color="text-purple-400" /></motion.div>
        <motion.div variants={itemVariants}><StatCard label="Flagged" value={overview?.flagged_content ?? "—"} icon={ShieldAlert} color="text-amber-400" /></motion.div>
        <motion.div variants={itemVariants}><StatCard label="Critical" value={overview?.critical_alerts ?? "—"} icon={AlertTriangle} color="text-red-400" /></motion.div>
        <motion.div variants={itemVariants}><StatCard label="Unread" value={overview?.unread_alerts ?? "—"} icon={Bell} color="text-orange-400" /></motion.div>
      </motion.div>

      {/* Today vs Yesterday delta cards */}
      {overview && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-5"
        >
          <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)]" />
            <p className="text-xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-widest mb-2">Flagged Today</p>
            <p className="text-4xl font-black text-white">{overview.flagged_today}</p>
            <div className="mt-3">{changeBadge()}</div>
          </div>
          <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.5)]" />
            <p className="text-xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-widest mb-2">Flagged Yesterday</p>
            <p className="text-4xl font-black text-white">{overview.flagged_yesterday}</p>
          </div>
          <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-[hsl(var(--muted-foreground))]" />
            <p className="text-xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-widest mb-2">24h Trend</p>
            <p className={`text-4xl font-black ${overview.percent_change > 0 ? "text-red-400 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" : overview.percent_change < 0 ? "text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]" : "text-zinc-400"}`}>
              {overview.percent_change > 0 ? "+" : ""}{overview.percent_change}%
            </p>
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monitor control */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} className="glass-panel rounded-2xl p-7">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20"><Activity className="w-5 h-5 text-cyan-400" /></div>
            <h2 className="text-white font-bold text-lg">Instagram Monitor</h2>
          </div>
          {running ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                <span className="text-green-400 text-sm font-medium">Monitoring @{running.username}</span>
              </div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Session expires 15 min after start.</p>
              <button onClick={stopMonitor} className="px-4 py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 text-sm hover:bg-red-500/20 transition-colors">Stop Monitoring</button>
            </div>
          ) : (
            <form onSubmit={startMonitor} className="space-y-3">
              <input value={monForm.instagram_username} onChange={e => setMonForm({ ...monForm, instagram_username: e.target.value })} placeholder="Instagram username" required className="w-full bg-[hsl(var(--muted))] border border-[hsl(var(--border))] text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500" />
              <input type="password" value={monForm.instagram_password} onChange={e => setMonForm({ ...monForm, instagram_password: e.target.value })} placeholder="Instagram password" required className="w-full bg-[hsl(var(--muted))] border border-[hsl(var(--border))] text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500" />
              <input value={monForm.target_profile_url} onChange={e => setMonForm({ ...monForm, target_profile_url: e.target.value })} placeholder="Target profile URL (optional)" className="w-full bg-[hsl(var(--muted))] border border-[hsl(var(--border))] text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500" />
              <button type="submit" disabled={monLoading} className="w-full py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-semibold text-sm disabled:opacity-50 transition-colors">{monLoading ? "Starting..." : "Start Monitoring"}</button>
            </form>
          )}
        </motion.div>

        {/* Live events */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} className="glass-panel rounded-2xl p-7 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-cyan-500 opacity-5 rounded-full blur-3xl" />
          <div className="flex items-center gap-3 mb-6 relative z-10">
            <span className="w-2.5 h-2.5 bg-cyan-400 rounded-full animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
            <h2 className="text-white font-bold text-lg">Live Event Stream</h2>
          </div>
          {liveEvents.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">Listening for network events...</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar relative z-10">
              {liveEvents.map((ev, i) => (
                <motion.div initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} key={i} className="text-xs text-[hsl(var(--muted-foreground))] font-mono bg-white/[0.02] p-2 rounded-md border border-white/[0.02]">
                  {ev}
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Manual Testing / Ingest Panel */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="glass-panel rounded-2xl p-8 border-cyan-500/30 glow-border-cyan relative overflow-hidden">
        <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500/10 to-purple-500/10 blur-xl z-0 pointer-events-none" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20"><FlaskConical className="w-5 h-5 text-cyan-400" /></div>
            <h2 className="text-white font-bold text-xl drop-shadow-sm">Manual Content Analysis</h2>
            <span className="ml-2 text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-[0_0_10px_rgba(6,182,212,0.2)]">Mode 3 — Safe</span>
          </div>
        <p className="text-xs text-[hsl(var(--muted-foreground))] mb-5">
          Submit any text directly into the AI pipeline — no Instagram required. Runs the full stack: NLP classification → severity → violation tracking → alerts.
        </p>
        <form onSubmit={handleIngest} className="space-y-3">
          <textarea
            value={ingestForm.text}
            onChange={e => setIngestForm({ ...ingestForm, text: e.target.value })}
            placeholder='e.g. "Nobody wants you here. You should just disappear."'
            required
            rows={3}
            className="w-full bg-[hsl(var(--muted))] border border-[hsl(var(--border))] text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500 resize-none"
          />
          <div className="flex gap-3">
            <input
              value={ingestForm.author}
              onChange={e => setIngestForm({ ...ingestForm, author: e.target.value })}
              placeholder="Author / username"
              required
              className="flex-1 bg-[hsl(var(--muted))] border border-[hsl(var(--border))] text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
            />
            <select
              value={ingestForm.content_type}
              onChange={e => setIngestForm({ ...ingestForm, content_type: e.target.value })}
              className="bg-[hsl(var(--muted))] border border-[hsl(var(--border))] text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
            >
              <option value="comment">Comment</option>
              <option value="message">DM</option>
            </select>
            <button
              type="submit"
              disabled={ingestLoading}
              className="px-5 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-semibold text-sm disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {ingestLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Analyze
            </button>
          </div>
        </form>

        {/* Result panel */}
        {ingestError && (
          <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{ingestError}</div>
        )}
        {ingestResult && (
          <div className="mt-4 rounded-lg bg-[hsl(var(--muted))] border border-[hsl(var(--border))] p-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-1">Toxicity</p>
              <p className="text-xl font-bold text-white">{(ingestResult.toxicity_score * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-1">Category</p>
              <p className="text-sm font-semibold text-white capitalize">{ingestResult.category?.replace("_", " ")}</p>
            </div>
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-1">Severity</p>
              <p className={`text-sm font-bold ${severityColor[ingestResult.severity] ?? "text-white"}`}>{ingestResult.severity}</p>
            </div>
            {ingestResult.severity_score !== undefined && (
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-1">Severity Score</p>
                <p className="text-xl font-bold text-white">{ingestResult.severity_score}/100</p>
              </div>
            )}
          </div>
        )}
        </div>
      </motion.div>
    </div>
  );
}
