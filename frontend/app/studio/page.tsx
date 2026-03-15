"use client";

import { useState } from "react";
import useSWR from "swr";
import { api, VoiceProfile, Job } from "@/lib/api";
import ScriptEditor from "@/components/ScriptEditor";
import JobProgress from "@/components/JobProgress";
import AudioPlayer from "@/components/AudioPlayer";

export default function StudioPage() {
  const { data: voices } = useSWR<VoiceProfile[]>("/voices", api.voices.list);

  const [voiceId, setVoiceId] = useState("");
  const [script, setScript] = useState("");
  const [speed, setSpeed] = useState(1.0);
  const [pauseMs, setPauseMs] = useState(300);
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
      setError("Please select a voice profile.");
      return;
    }
    if (!script.trim()) {
      setError("Please enter a script.");
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
      setError(e instanceof Error ? e.message : "Failed to queue job");
    } finally {
      setSubmitting(false);
    }
  }

  function handleJobComplete(job: Job) {
    setCompletedJob(job);
  }

  const isGenerating = !!jobId && (!completedJob || completedJob.status === "processing" || completedJob.status === "queued");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-1">Studio</h1>
        <p className="text-gray-500 text-sm">Select a voice, write your script, and generate.</p>
      </div>

      <form onSubmit={handleGenerate} className="space-y-6">
        {/* Voice selector */}
        <div>
          <label htmlFor="voice-select" className="block text-sm font-medium text-gray-700 mb-1">
            Voice Profile
          </label>
          {!voices ? (
            <p className="text-gray-400 text-sm animate-pulse">Loading voices…</p>
          ) : voices.length === 0 ? (
            <p className="text-sm text-gray-500">
              No voice profiles found.{" "}
              <a href="/" className="text-indigo-600 underline">
                Create one first.
              </a>
            </p>
          ) : (
            <select
              id="voice-select"
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              aria-label="Select voice profile"
            >
              <option value="">— Select a voice —</option>
              {voices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name} ({v.duration_s.toFixed(1)}s · {v.engine})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Script editor */}
        <ScriptEditor value={script} onChange={setScript} />

        {/* Voice settings */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-gray-50 rounded-xl p-4">
          <div>
            <label htmlFor="speed-slider" className="block text-sm font-medium text-gray-700 mb-1">
              Speed: <span className="font-mono">{speed.toFixed(2)}x</span>
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
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>0.7x</span>
              <span>1.0x</span>
              <span>1.3x</span>
            </div>
          </div>

          <div>
            <label htmlFor="pause-slider" className="block text-sm font-medium text-gray-700 mb-1">
              Sentence pause: <span className="font-mono">{pauseMs}ms</span>
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
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>0ms</span>
              <span>500ms</span>
              <span>1s</span>
            </div>
          </div>
        </div>

        {error && (
          <p role="alert" className="text-red-600 text-sm">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting || isGenerating}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold py-3 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          aria-label="Generate audio"
        >
          {submitting ? "Queuing…" : isGenerating ? "Generating…" : "Generate Audio"}
        </button>
      </form>

      {/* Job progress */}
      {jobId && !completedJob && (
        <section aria-label="Generation progress">
          <JobProgress jobId={jobId} onComplete={handleJobComplete} />
        </section>
      )}

      {completedJob && completedJob.status === "completed" && completedJob.output_id && (
        <section aria-label="Generated audio" aria-live="polite">
          <h2 className="text-lg font-semibold mb-3">Generated Audio</h2>
          <AudioPlayer outputId={completedJob.output_id} />
        </section>
      )}

      {completedJob && completedJob.status === "failed" && (
        <p role="alert" className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg p-3">
          Generation failed: {completedJob.error}
        </p>
      )}
    </div>
  );
}
