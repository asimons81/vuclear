"use client";

import useSWR from "swr";
import { api, Output } from "@/lib/api";

export default function HistoryPage() {
  const { data: outputs, mutate, isLoading } = useSWR<Output[]>("/outputs", api.outputs.list, {
    refreshInterval: 5000,
  });

  async function handleDelete(outputId: string) {
    if (!confirm("Delete this output? This cannot be undone.")) return;
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
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-1">History</h1>
        <p className="text-gray-500 text-sm">Past generated outputs. Downloads expire when server data is cleared.</p>
      </div>

      {isLoading && <p className="text-gray-400 animate-pulse">Loading…</p>}

      {!isLoading && (!outputs || outputs.length === 0) && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-2">No outputs yet.</p>
          <p className="text-sm">
            Go to{" "}
            <a href="/studio" className="text-indigo-600 underline">
              Studio
            </a>{" "}
            to generate your first audio.
          </p>
        </div>
      )}

      {outputs && outputs.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" aria-label="Output history">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500 text-xs uppercase tracking-wide">
                <th className="py-3 pr-4 font-medium">Date</th>
                <th className="py-3 pr-4 font-medium">Script preview</th>
                <th className="py-3 pr-4 font-medium">Duration</th>
                <th className="py-3 pr-4 font-medium">Download</th>
                <th className="py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {outputs.map((o) => (
                <tr key={o.output_id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 pr-4 text-gray-500 whitespace-nowrap">
                    {fmtDate(o.created_at)}
                  </td>
                  <td className="py-3 pr-4 max-w-xs">
                    <span
                      className="block truncate text-gray-800"
                      title={o.script}
                    >
                      {o.script}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-gray-500 whitespace-nowrap font-mono text-xs">
                    {fmtDuration(o.duration_s)}
                  </td>
                  <td className="py-3 pr-4">
                    <div className="flex gap-2 flex-wrap">
                      <a
                        href={api.outputs.downloadUrl(o.output_id, "wav")}
                        download={`voice-clone-${o.output_id.slice(0, 8)}.wav`}
                        className="text-indigo-600 hover:text-indigo-800 font-medium underline text-xs focus:outline-none focus:ring-2 focus:ring-indigo-400 rounded"
                        aria-label={`Download WAV for output ${o.output_id.slice(0, 8)}`}
                      >
                        WAV
                      </a>
                      <a
                        href={api.outputs.downloadUrl(o.output_id, "mp3")}
                        download={`voice-clone-${o.output_id.slice(0, 8)}.mp3`}
                        className="text-indigo-600 hover:text-indigo-800 font-medium underline text-xs focus:outline-none focus:ring-2 focus:ring-indigo-400 rounded"
                        aria-label={`Download MP3 for output ${o.output_id.slice(0, 8)}`}
                      >
                        MP3
                      </a>
                    </div>
                  </td>
                  <td className="py-3">
                    <button
                      onClick={() => handleDelete(o.output_id)}
                      className="text-xs text-red-500 hover:text-red-700 font-medium focus:outline-none focus:ring-2 focus:ring-red-400 rounded px-2 py-1"
                      aria-label={`Delete output ${o.output_id.slice(0, 8)}`}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
