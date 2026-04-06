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
  cancelled: "Cancelled",
};

export default function JobProgress({ jobId, onComplete }: Props) {
  const { data: job, error } = useSWR<Job>(jobId ? `/jobs/${jobId}` : null, () => api.jobs.get(jobId), {
    refreshInterval: (value) =>
      value?.status === "queued" || value?.status === "processing" ? 1500 : 0,
    onSuccess: (value) => {
      if (value.status === "completed" || value.status === "failed" || value.status === "cancelled") {
        onComplete(value);
      }
    },
  });

  if (error) {
    return <p role="alert" className="text-sm" style={{ color: "var(--danger-text)" }}>Could not fetch job status.</p>;
  }

  if (!job) {
    return <p className="section-copy text-sm animate-pulse">Loading job status...</p>;
  }

  const label = STATUS_LABELS[job.status] ?? job.status;
  const pct = job.progress_pct;

  return (
    <div className="panel rounded-2xl p-4 space-y-3" aria-live="polite" aria-atomic="false">
      <div className="flex items-center justify-between text-sm">
        <span
          className="font-semibold"
          style={{
            color:
              job.status === "failed"
                ? "var(--danger-text)"
                : job.status === "cancelled"
                  ? "var(--text-muted)"
                  : job.status === "completed"
                    ? "var(--success-text)"
                    : "var(--text)",
          }}
        >
          {label}
        </span>
        <span className="hint font-mono text-xs">{pct}%</span>
      </div>

      <div
        className="progress-track h-2 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} - ${pct}%`}
      >
        <div
          className="h-full transition-all duration-500 rounded-full"
          style={{
            width: `${pct}%`,
            background:
              job.status === "failed"
                ? "var(--danger-text)"
                : job.status === "completed"
                  ? "var(--success-text)"
                  : "linear-gradient(90deg, var(--accent-strong), var(--accent))",
          }}
        />
      </div>

      {job.status === "processing" && (
        <p className="hint text-xs">This may take 30-60 seconds depending on script length.</p>
      )}

      {job.error && (
        <p role="alert" className="text-sm" style={{ color: "var(--danger-text)" }}>
          {job.error}
        </p>
      )}
    </div>
  );
}
