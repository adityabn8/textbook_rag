import { FileText, Sparkles } from 'lucide-react';
import type { SourceChunk } from '../api/ragClient';

interface SourcesDrawerProps {
  sources: SourceChunk[];
  loading: boolean;
}

export function SourcesDrawer({ sources, loading }: SourcesDrawerProps) {
  return (
    <aside className="bg-slate-50 border-t lg:border-t-0 lg:border-l border-slate-200 p-4 sm:p-6 lg:w-96 shrink-0">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          <FileText className="w-4 h-4 text-indigo-600" />
          Textbook Proof & Citations
        </h2>
        {sources.length > 0 && (
          <span className="text-xs font-medium bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
            {sources.length} chunks
          </span>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-24 rounded-xl bg-slate-200/70 animate-pulse" />
          ))}
        </div>
      ) : sources.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
          Ask an exam question to inspect the exact textbook excerpts used to verify the answer.
        </div>
      ) : (
        <div className="space-y-3">
          {sources.map((src, idx) => (
            <div
              key={idx}
              className="rounded-xl bg-white p-3.5 border border-slate-200 shadow-2xs hover:border-indigo-300 transition"
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md">
                  {src.file_name}
                </span>
                <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  RRF {src.score.toFixed(4)}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-slate-600">
                {src.text_preview}
              </p>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}