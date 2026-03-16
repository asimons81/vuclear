"use client";

import useSWR from "swr";
import { api, Job } from "@/lib/api";

type Props = {
  jobId: string;
  onComplete: (job: Job) => void;
};

const STATUS_LABELS: Record<string, string> = {
  queued: "Waiting in queue",
  processing: "Synthesizing audio",
  completed: "Complete",
  failed: "Failed",
};

export default function JobProgress({ jobId, onComplete }: Props) {
  const { data: job, error } = useSWR<Job>(
    jobId ? `/jobs/${jobId}` : null,
    () => api.jobs.get(jobId),
    {
      refreshInterval: (j) =>
        j?.status === "queued" || j?.status === "processing" ? 1500 : 0,
      onSuccess: (j) => {
        if (j.status === "completed" || j.status === "failed") {
          onComplete(j);
        }
      },
    }
  );

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-600">
        Could not fetch job status.
      </p>
    );
  }

  if (!job) {
    return (
      <p className="text-sm text-slate-500 animate-pulse">Loading job status…</p>
    );
  }

  const label = STATUS_LABELS[job.status] ?? job.status;
  const pct = job.progress_pct;

  const statusColor =
    job.status === "failed"
      ? "text-red-600"
      : job.status === "completed"
        ? "text-green-600"
        : "text-slate-600";

  const barColor =
    job.status === "failed"
      ? "bg-red-500"
      : job.status === "completed"
        ? "bg-green-500"
        : "bg-indigo-500";

  return (
    <div
      className="bg-white border border-slate-200 rounded-xl p-4 space-y-3"
      aria-live="polite"
      aria-atomic="false"
    >
      <div className="flex items-center justify-between text-sm">
        <span className={`font-medium ${statusColor}`}>{label}</span>
        <span className="text-slate-400 font-mono text-xs">{pct}%</span>
      </div>

      <div
        className={`h-1.5 rounded-full overflow-hidden ${job.status === "queued" ? "bg-slate-200 animate-pulse" : "bg-slate-100"}`}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} — ${pct}%`}
      >
        <div
          className={`h-full transition-all duration-500 rounded-full ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {job.status === "processing" && (
        <p className="text-xs text-slate-400">
          This may take 30–60 seconds depending on script length.
        </p>
      )}

      {job.error && (
        <p role="alert" className="text-sm text-red-600">
          {job.error}
        </p>
      )}
    </div>
  );
}
