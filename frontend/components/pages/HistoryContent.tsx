"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { api, Output } from "@/lib/api";

export default function HistoryContent() {
  const { data: outputs, mutate, isLoading } = useSWR<Output[]>("/outputs", api.outputs.list, {
    refreshInterval: 5000,
  });
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  async function handleDelete(outputId: string) {
    setPendingDeleteId(null);
    await api.outputs.delete(outputId);
    mutate();
  }

  const fmtDate = (iso: string) =>
    new Intl.DateTimeFormat(undefined, { dateStyle: "short", timeStyle: "short" }).format(new Date(iso));

  const fmtDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.round(seconds % 60);
    return minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`;
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="section-title text-2xl font-bold mb-1">History</h1>
        <p className="section-copy text-sm">
          Past generated outputs. Files are stored locally and cleared when the server restarts.
        </p>
      </div>

      {isLoading && <p className="section-copy text-sm animate-pulse">Loading...</p>}

      {!isLoading && (!outputs || outputs.length === 0) && (
        <div className="panel rounded-2xl py-16 text-center">
          <p className="section-title font-semibold mb-1">No outputs yet</p>
          <p className="section-copy text-sm mb-5">
            Generated audio will appear here after you synthesize from the Studio.
          </p>
          <Link href="/studio" className="btn-primary inline-flex items-center px-4 py-2 rounded-xl text-sm font-semibold">
            Open Studio
          </Link>
        </div>
      )}

      {outputs && outputs.length > 0 && (
        <div className="panel rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table w-full text-sm" aria-label="Output history">
              <thead>
                <tr className="text-left border-b" style={{ borderColor: "var(--border)" }}>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em]">Date</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em]">Script</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] whitespace-nowrap">Duration</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] whitespace-nowrap">Take</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em]">Download</th>
                  <th className="px-4 py-3" aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {outputs.map((output) => (
                  <tr key={output.output_id}>
                    <td className="px-4 py-3 hint whitespace-nowrap text-xs">{fmtDate(output.created_at)}</td>
                    <td className="px-4 py-3 max-w-xs">
                      <span className="block truncate section-title" title={output.script}>
                        {output.script}
                      </span>
                    </td>
                    <td className="px-4 py-3 hint whitespace-nowrap font-mono text-xs">
                      {fmtDuration(output.duration_s)}
                    </td>
                    <td className="px-4 py-3 hint whitespace-nowrap font-mono text-xs">
                      Take {output.take_number ?? 1}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5">
                        <a
                          href={api.outputs.downloadUrl(output.output_id, "wav")}
                          download={`output-${output.output_id.slice(0, 8)}.wav`}
                          className="btn-secondary inline-flex items-center px-2.5 py-1.5 rounded-lg text-xs font-semibold"
                        >
                          WAV
                        </a>
                        <a
                          href={api.outputs.downloadUrl(output.output_id, "mp3")}
                          download={`output-${output.output_id.slice(0, 8)}.mp3`}
                          className="btn-secondary inline-flex items-center px-2.5 py-1.5 rounded-lg text-xs font-semibold"
                        >
                          MP3
                        </a>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {pendingDeleteId === output.output_id ? (
                        <span className="flex items-center gap-1 whitespace-nowrap">
                          <span className="hint text-xs">Delete?</span>
                          <button
                            type="button"
                            onClick={() => handleDelete(output.output_id)}
                            aria-label={`Confirm delete output ${output.output_id.slice(0, 8)}`}
                            className="btn-danger text-xs font-medium px-2 py-1.5 rounded-lg"
                          >
                            Yes
                          </button>
                          <button
                            type="button"
                            onClick={() => setPendingDeleteId(null)}
                            aria-label="Cancel delete"
                            className="btn-secondary text-xs px-2 py-1.5 rounded-lg"
                          >
                            Cancel
                          </button>
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setPendingDeleteId(output.output_id)}
                          className="btn-danger text-xs font-medium px-2 py-1.5 rounded-lg"
                          aria-label={`Delete output ${output.output_id.slice(0, 8)}`}
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
