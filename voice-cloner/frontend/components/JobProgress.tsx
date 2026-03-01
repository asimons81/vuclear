"use client";

import useSWR from "swr";
import { api, Job } from "@/lib/api";

type Props = {
  jobId: string;
  onComplete: (job: Job) => void;
};

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued…",
  processing: "Generating audio…",
  completed: "Done!",
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
    },
  );

  if (error) {
    return (
      <p role="alert" className="text-red-600 text-sm">
        Failed to fetch job status.
      </p>
    );
  }

  if (!job) {
    return <p className="text-gray-500 text-sm animate-pulse">Loading job status…</p>;
  }

  const label = STATUS_LABELS[job.status] ?? job.status;
  const pct = job.progress_pct;

  return (
    <div className="space-y-2" aria-live="polite" aria-atomic="false">
      <div className="flex justify-between text-sm">
        <span
          className={
            job.status === "failed"
              ? "text-red-600 font-medium"
              : job.status === "completed"
                ? "text-green-600 font-medium"
                : "text-indigo-600"
          }
        >
          {label}
        </span>
        <span className="text-gray-500 font-mono">{pct}%</span>
      </div>

      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            job.status === "failed"
              ? "bg-red-500"
              : job.status === "completed"
                ? "bg-green-500"
                : "bg-indigo-500"
          }`}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {job.error && (
        <p role="alert" className="text-red-600 text-sm">
          {job.error}
        </p>
      )}
    </div>
  );
}
