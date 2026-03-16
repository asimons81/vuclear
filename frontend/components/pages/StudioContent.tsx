"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { api, VoiceProfile, Job } from "@/lib/api";
import ScriptEditor from "@/components/ScriptEditor";
import JobProgress from "@/components/JobProgress";
import AudioPlayer from "@/components/AudioPlayer";

export default function StudioContent() {
  const { data: voices } = useSWR<VoiceProfile[]>("/voices", api.voices.list);

  const [voiceId, setVoiceId] = useState("");
  const [script, setScript] = useState("");
  const [speed, setSpeed] = useState(1.0);
  const [pauseMs, setPauseMs] = useState(300);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [completedJob, setCompletedJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setJobId(null);
    setCompletedJob(null);

    if (!voiceId) {
      setError("Select a voice profile to continue.");
      return;
    }
    if (!script.trim()) {
      setError("Enter a script before generating.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.synthesize({
        voice_id: voiceId,
        script: script.trim(),
        speed,
        pause_ms: pauseMs,
      });
      setJobId(res.job_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to queue job. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleJobComplete(job: Job) {
    setCompletedJob(job);
  }

  const isGenerating =
    !!jobId &&
    (!completedJob ||
      completedJob.status === "processing" ||
      completedJob.status === "queued");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Studio</h1>
        <p className="text-sm text-slate-500">
          Choose a voice, write your script, and generate.
        </p>
      </div>

      <form onSubmit={handleGenerate} className="space-y-6">
        {/* Voice selector */}
        <div>
          <label
            htmlFor="voice-select"
            className="block text-sm font-medium text-slate-700 mb-1.5"
          >
            Voice profile
          </label>
          {!voices ? (
            <p className="text-sm text-slate-500 animate-pulse">Loading voices…</p>
          ) : voices.length === 0 ? (
            <p className="text-sm text-slate-500">
              No voice profiles found.{" "}
              <Link href="/" className="text-indigo-600 hover:text-indigo-800 font-medium">
                Add a voice first.
              </Link>
            </p>
          ) : (
            <select
              id="voice-select"
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
            >
              <option value="">Select a voice…</option>
              {voices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name} — {v.duration_s.toFixed(1)}s · {v.engine}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Script editor */}
        <ScriptEditor value={script} onChange={setScript} />

        {/* Advanced settings — collapsed by default */}
        <div>
          <button
            type="button"
            id="advanced-settings-toggle"
            onClick={() => setShowAdvanced((v) => !v)}
            aria-expanded={showAdvanced}
            aria-controls="advanced-settings-panel"
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
          >
            <svg
              className={`w-3 h-3 transition-transform duration-150 ${showAdvanced ? "rotate-90" : ""}`}
              viewBox="0 0 12 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M4 2L8 6L4 10"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Advanced settings
          </button>

          {showAdvanced && (
            <div
              id="advanced-settings-panel"
              className="mt-3 pt-4 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-6"
            >
              <div>
                <label
                  htmlFor="speed-slider"
                  className="block text-sm font-medium text-slate-700 mb-1.5"
                >
                  Speed{" "}
                  <span className="font-mono text-slate-500">{speed.toFixed(2)}x</span>
                </label>
                <input
                  id="speed-slider"
                  type="range"
                  min={0.7}
                  max={1.3}
                  step={0.05}
                  value={speed}
                  onChange={(e) => setSpeed(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600"
                  aria-label="Playback speed"
                  aria-valuetext={`${speed.toFixed(2)}x speed`}
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>0.7×</span>
                  <span>1.0×</span>
                  <span>1.3×</span>
                </div>
              </div>

              <div>
                <label
                  htmlFor="pause-slider"
                  className="block text-sm font-medium text-slate-700 mb-1.5"
                >
                  Sentence pause{" "}
                  <span className="font-mono text-slate-500">{pauseMs}ms</span>
                </label>
                <input
                  id="pause-slider"
                  type="range"
                  min={0}
                  max={1000}
                  step={50}
                  value={pauseMs}
                  onChange={(e) => setPauseMs(parseInt(e.target.value))}
                  className="w-full accent-indigo-600"
                  aria-label="Pause between sentences in milliseconds"
                  aria-valuetext={`${pauseMs} milliseconds`}
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>0ms</span>
                  <span>500ms</span>
                  <span>1s</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div
            role="alert"
            className="bg-red-50 border border-red-200 rounded-lg px-3 py-2.5"
          >
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={submitting || isGenerating}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          {submitting ? "Queuing…" : isGenerating ? "Generating…" : "Generate audio"}
        </button>
      </form>

      {/* Job progress */}
      {jobId && !completedJob && (
        <section aria-label="Generation progress">
          <JobProgress jobId={jobId} onComplete={handleJobComplete} />
        </section>
      )}

      {/* Result */}
      {completedJob && completedJob.status === "completed" && completedJob.output_id && (
        <section aria-label="Generated audio" aria-live="polite">
          <div className="flex items-center gap-2.5 mb-3">
            <h2 className="text-sm font-semibold text-slate-900">Generated audio</h2>
            <span className="text-xs font-medium text-green-700 bg-green-100 px-1.5 py-0.5 rounded-full">
              Ready
            </span>
          </div>
          <AudioPlayer outputId={completedJob.output_id} />
        </section>
      )}

      {completedJob && completedJob.status === "failed" && (
        <div role="alert" className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm font-medium text-red-700 mb-0.5">Generation failed</p>
          <p className="text-sm text-red-600">{completedJob.error}</p>
        </div>
      )}
    </div>
  );
}
