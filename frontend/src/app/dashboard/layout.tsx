"use client";
import { useRouter, usePathname } from "next/navigation";
import Cookies from "js-cookie";
import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, BarChart2, Bell, MessageSquare,
  Users, AlertTriangle, Shield, LogOut, ChevronRight, Menu, X
} from "lucide-react";

const nav = [
  { href: "/dashboard/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/dashboard/alerts", label: "Alerts", icon: Bell },
  { href: "/dashboard/conversations", label: "Messages", icon: MessageSquare },
  { href: "/dashboard/comments", label: "Comments", icon: MessageSquare },
  { href: "/dashboard/offenders", label: "Offenders", icon: Users },
  { href: "/dashboard/emergency", label: "Emergency", icon: AlertTriangle },
];

// Show only the most important items in mobile bottom bar
const mobileNav = [
  { href: "/dashboard/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/conversations", label: "Messages", icon: MessageSquare },
  { href: "/dashboard/comments", label: "Comments", icon: MessageSquare },
  { href: "/dashboard/offenders", label: "Offenders", icon: Users },
  { href: "/dashboard/emergency", label: "Emergency", icon: AlertTriangle },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!Cookies.get("token")) router.replace("/auth/login");
  }, [router]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  const logout = () => { Cookies.remove("token"); router.replace("/auth/login"); };

  return (
    <div className="flex h-screen overflow-hidden bg-[hsl(var(--background))] selection:bg-cyan-500/30 selection:text-cyan-200">
      
      {/* ─── DESKTOP SIDEBAR ─── */}
      <motion.aside
        initial={{ x: -250 }} animate={{ x: 0 }}
        className="hidden md:flex w-64 flex-col border-r border-[hsl(var(--border))] bg-white/[0.01] backdrop-blur-xl relative z-10 shrink-0"
      >
        <div className="p-6 flex items-center gap-3 border-b border-[hsl(var(--border))]">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.3)]">
            <Shield className="text-cyan-400 w-6 h-6" />
          </div>
          <span className="text-white font-bold text-xl tracking-tight glow-text-cyan">CyberShield</span>
        </div>
        
        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          {nav.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href;
            return (
              <Link key={href} href={href} className="block outline-none relative group">
                {isActive && (
                  <motion.div
                    layoutId="activeNavIndicator"
                    className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-transparent border-l-2 border-cyan-400 rounded-r-lg"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <div className={`flex items-center justify-between px-3 py-3 rounded-lg text-sm transition-all relative z-10
                  ${isActive 
                    ? "text-cyan-300 font-semibold" 
                    : "text-[hsl(var(--muted-foreground))] group-hover:text-white group-hover:bg-white/[0.03]"}`}>
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : ""}`} />
                    {label}
                  </div>
                  {isActive && <ChevronRight className="w-4 h-4 text-cyan-500/50" />}
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-[hsl(var(--border))]">
          <button onClick={logout}
            className="flex items-center justify-center gap-3 px-4 py-3 w-full rounded-xl text-sm font-medium text-[hsl(var(--muted-foreground))] border border-transparent hover:border-red-500/30 hover:text-red-400 hover:bg-red-500/10 hover:shadow-[0_0_15px_rgba(239,68,68,0.2)] transition-all">
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </motion.aside>

      {/* ─── MOBILE TOP BAR ─── */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--background))]/90 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
            <Shield className="text-cyan-400 w-5 h-5" />
          </div>
          <span className="text-white font-bold text-lg tracking-tight">CyberShield</span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg text-[hsl(var(--muted-foreground))] hover:text-white hover:bg-white/5 transition-all"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* ─── MOBILE FULL MENU OVERLAY ─── */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="md:hidden fixed top-[57px] left-0 right-0 z-40 bg-[hsl(var(--background))]/95 backdrop-blur-xl border-b border-[hsl(var(--border))] p-4 space-y-1"
          >
            {nav.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href;
              return (
                <Link key={href} href={href} className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-all"
                  style={{ color: isActive ? 'rgb(103,232,249)' : 'hsl(var(--muted-foreground))' }}>
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              );
            })}
            <div className="pt-2 border-t border-[hsl(var(--border))]">
              <button onClick={logout}
                className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-sm text-red-400 hover:bg-red-500/10 transition-all">
                <LogOut className="w-4 h-4" /> Sign Out
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── MAIN CONTENT ─── */}
      <main className="flex-1 overflow-auto bg-[url('/grid-pattern.svg')] bg-fixed relative md:mt-0 mt-[57px] mb-[64px] md:mb-0">
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/[0.02] via-transparent to-purple-500/[0.02] pointer-events-none" />
        
        <AnimatePresence mode="wait">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="p-4 md:p-8 max-w-7xl mx-auto relative z-10"
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* ─── MOBILE BOTTOM TAB BAR ─── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around px-2 py-2 border-t border-[hsl(var(--border))] bg-[hsl(var(--background))]/95 backdrop-blur-xl">
        {mobileNav.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <Link key={href} href={href}
              className={`flex flex-col items-center gap-0.5 px-2 py-1 rounded-xl transition-all min-w-[52px]
                ${isActive ? "text-cyan-400" : "text-[hsl(var(--muted-foreground))]"}`}>
              <Icon className="w-5 h-5" />
              <span className="text-[9px] font-medium leading-tight">{label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
