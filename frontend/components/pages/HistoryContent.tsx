"use client";

import useSWR from "swr";
import Link from "next/link";
import { api, Output } from "@/lib/api";
import { useState } from "react";

export default function HistoryContent() {
  const { data: outputs, mutate, isLoading } = useSWR<Output[]>(
    "/outputs",
    api.outputs.list,
    { refreshInterval: 5000 }
  );
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  async function handleDelete(outputId: string) {
    setPendingDeleteId(null);
    await api.outputs.delete(outputId);
    mutate();
  }

  const fmtDate = (iso: string) =>
    new Intl.DateTimeFormat(undefined, {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));

  const fmtDuration = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">History</h1>
        <p className="text-sm text-slate-500">
          Past generated outputs. Files are stored locally and cleared when the server
          restarts.
        </p>
      </div>

      {isLoading && (
        <p className="text-sm text-slate-500 animate-pulse">Loading…</p>
      )}

      {!isLoading && (!outputs || outputs.length === 0) && (
        <div className="bg-white rounded-xl border border-slate-200 py-16 text-center">
          <p className="text-slate-900 font-medium mb-1">No outputs yet</p>
          <p className="text-sm text-slate-500 mb-5">
            Generated audio will appear here after you synthesize from the Studio.
          </p>
          <Link
            href="/studio"
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Open Studio
          </Link>
        </div>
      )}

      {outputs && outputs.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" aria-label="Output history">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">
                    Date
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">
                    Script
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide whitespace-nowrap">
                    Duration
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">
                    Download
                  </th>
                  <th className="px-4 py-3" aria-label="Actions" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {outputs.map((o) => (
                  <tr key={o.output_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 text-slate-500 whitespace-nowrap text-xs">
                      {fmtDate(o.created_at)}
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <span
                        className="block truncate text-slate-800"
                        title={o.script}
                      >
                        {o.script}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 whitespace-nowrap font-mono text-xs">
                      {fmtDuration(o.duration_s)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5">
                        <a
                          href={api.outputs.downloadUrl(o.output_id, "wav")}
                          download={`output-${o.output_id.slice(0, 8)}.wav`}
                          className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
                          aria-label={`Download WAV for output ${o.output_id.slice(0, 8)}`}
                        >
                          WAV
                        </a>
                        <a
                          href={api.outputs.downloadUrl(o.output_id, "mp3")}
                          download={`output-${o.output_id.slice(0, 8)}.mp3`}
                          className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
                          aria-label={`Download MP3 for output ${o.output_id.slice(0, 8)}`}
                        >
                          MP3
                        </a>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {pendingDeleteId === o.output_id ? (
                        <span className="flex items-center gap-1 whitespace-nowrap">
                          <span className="text-xs text-slate-500">Delete?</span>
                          <button
                            onClick={() => handleDelete(o.output_id)}
                            aria-label={`Confirm delete output ${o.output_id.slice(0, 8)}`}
                            className="text-xs text-red-600 font-medium px-2 py-1.5 rounded hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
                          >
                            Yes
                          </button>
                          <button
                            onClick={() => setPendingDeleteId(null)}
                            aria-label="Cancel delete"
                            className="text-xs text-slate-500 px-2 py-1.5 rounded hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-300"
                          >
                            Cancel
                          </button>
                        </span>
                      ) : (
                        <button
                          onClick={() => setPendingDeleteId(o.output_id)}
                          className="text-xs text-slate-500 hover:text-red-600 font-medium px-2 py-1.5 rounded hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
                          aria-label={`Delete output ${o.output_id.slice(0, 8)}`}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
