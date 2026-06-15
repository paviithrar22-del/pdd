"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import api from "@/services/api";
import { MessageSquare, ExternalLink, ShieldAlert, ShieldCheck, Shield } from "lucide-react";
// Removed Badge import as it's not installed

interface Moderation {
  toxicity_score: number;
  category: string;
  severity: string;
}

interface CommentData {
  id: number;
  post_id: number;
  post_url: string;
  author: string;
  content: string;
  moderation: Moderation | null;
}

export default function CommentsPage() {
  const [comments, setComments] = useState<CommentData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchComments();
  }, []);

  const fetchComments = async () => {
    try {
      setLoading(true);
      const res = await api.get("/comments/?limit=50");
      setComments(res.data.comments || []);
    } catch (error) {
      console.error("Failed to fetch comments", error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityBadge = (mod: Moderation | null) => {
    const baseClasses = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border";
    if (!mod) return <span className={`${baseClasses} bg-gray-500/20 text-gray-400 border-gray-500/30`}>Unanalyzed</span>;
    if (mod.severity === "Safe") return <span className={`${baseClasses} bg-green-500/20 text-green-400 border-green-500/30`}><ShieldCheck className="w-3 h-3 mr-1" /> Safe</span>;
    if (mod.severity === "Moderate") return <span className={`${baseClasses} bg-yellow-500/20 text-yellow-400 border-yellow-500/30`}><Shield className="w-3 h-3 mr-1" /> Moderate</span>;
    if (mod.severity === "High") return <span className={`${baseClasses} bg-orange-500/20 text-orange-400 border-orange-500/30`}><ShieldAlert className="w-3 h-3 mr-1" /> High Risk</span>;
    if (mod.severity === "Critical") return <span className={`${baseClasses} bg-red-500/20 text-red-400 border-red-500/30`}><ShieldAlert className="w-3 h-3 mr-1" /> Critical</span>;
    return <span className={`${baseClasses} bg-gray-500/20 text-gray-400 border-gray-500/30`}>{mod.severity}</span>;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-bold text-white tracking-tight flex items-center gap-3">
            <MessageSquare className="w-10 h-10 text-cyan-400" />
            Comments
          </h1>
          <p className="text-[hsl(var(--muted-foreground))] mt-2 text-lg">
            Monitor and moderate post comments.
          </p>
        </div>
      </div>

      <div className="bg-white/[0.02] border border-[hsl(var(--border))] rounded-2xl p-6 backdrop-blur-xl">
        <div className="space-y-4">
          <AnimatePresence>
            {loading ? (
              <div className="text-center py-10 text-[hsl(var(--muted-foreground))]">Loading comments...</div>
            ) : comments.length === 0 ? (
              <div className="text-center py-10 text-[hsl(var(--muted-foreground))]">No comments found. Start monitoring an account to collect comments.</div>
            ) : (
              comments.map((comment) => (
                <motion.div
                  key={comment.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="bg-white/[0.03] border border-[hsl(var(--border))] p-5 rounded-xl hover:bg-white/[0.05] transition-all"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400 font-bold border border-cyan-500/30">
                        {comment.author.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-white font-medium">@{comment.author}</p>
                        {comment.post_url && (
                          <a href={comment.post_url} target="_blank" rel="noopener noreferrer" className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 mt-0.5 transition-colors">
                            View original post <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      {getSeverityBadge(comment.moderation)}
                      {comment.moderation && comment.moderation.category !== "safe" && (
                        <span className="text-xs text-red-400/80 bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20 capitalize">
                          {comment.moderation.category}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className={`p-4 rounded-lg bg-black/40 border-l-2 ${
                    comment.moderation?.severity === 'Critical' ? 'border-l-red-500' :
                    comment.moderation?.severity === 'High' ? 'border-l-orange-500' :
                    comment.moderation?.severity === 'Moderate' ? 'border-l-yellow-500' :
                    comment.moderation?.severity === 'Safe' ? 'border-l-green-500' : 'border-l-gray-500'
                  }`}>
                    <p className="text-gray-200">{comment.content}</p>
                  </div>
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
