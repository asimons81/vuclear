"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { api, Job, VoiceProfile } from "@/lib/api";
import AudioPlayer from "@/components/AudioPlayer";
import JobProgress from "@/components/JobProgress";
import ScriptEditor from "@/components/ScriptEditor";

export default function StudioContent() {
  const { data: voices } = useSWR<VoiceProfile[]>("/voices", api.voices.list);

  const [voiceId, setVoiceId] = useState("");
  const [script, setScript] = useState("");
  const [speed, setSpeed] = useState(1.0);
  const [pauseMs, setPauseMs] = useState(300);
  const [chunkSize, setChunkSize] = useState(800);
  const [crossfadeMs, setCrossfadeMs] = useState(120);
  const [effectsPreset, setEffectsPreset] = useState("dry");
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
        chunk_size: chunkSize,
        crossfade_ms: crossfadeMs,
        effects_preset: effectsPreset === "dry" ? null : effectsPreset,
      });
      setJobId(res.job_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to queue job. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const isGenerating =
    !!jobId &&
    (!completedJob ||
      completedJob.status === "processing" ||
      completedJob.status === "queued");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="section-title text-2xl font-bold mb-1">Studio</h1>
        <p className="section-copy text-sm">
          Choose a voice, write your script, and generate.
        </p>
      </div>

      <form onSubmit={handleGenerate} className="panel rounded-2xl p-6 space-y-6">
        <div>
          <label htmlFor="voice-select" className="label block text-sm font-medium mb-1.5">
            Voice profile
          </label>
          {!voices ? (
            <p className="section-copy text-sm animate-pulse">Loading voices...</p>
          ) : voices.length === 0 ? (
            <p className="section-copy text-sm">
              No voice profiles found.{" "}
              <Link href="/" className="link-accent font-medium">
                Add a voice first.
              </Link>
            </p>
          ) : (
            <select
              id="voice-select"
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              className="select-field rounded-xl px-3 py-2 text-sm"
            >
              <option value="">Select a voice...</option>
              {voices.map((voice) => (
                <option key={voice.voice_id} value={voice.voice_id}>
                  {voice.name} - {voice.duration_s.toFixed(1)}s · {voice.engine}
                </option>
              ))}
            </select>
          )}
        </div>

        <ScriptEditor value={script} onChange={setScript} />

        <div>
          <button
            type="button"
            id="advanced-settings-toggle"
            onClick={() => setShowAdvanced((value) => !value)}
            aria-expanded={showAdvanced}
            aria-controls="advanced-settings-panel"
            className="button-ghost inline-flex items-center gap-1.5 text-sm"
          >
            <svg
              className={`h-3 w-3 transition-transform duration-150 ${showAdvanced ? "rotate-90" : ""}`}
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
              className="mt-3 grid grid-cols-1 gap-6 border-t pt-4 sm:grid-cols-4"
            >
              <div>
                <label htmlFor="speed-slider" className="label block text-sm font-medium mb-1.5">
                  Speed <span className="hint font-mono">{speed.toFixed(2)}x</span>
                </label>
                <input
                  id="speed-slider"
                  type="range"
                  min={0.7}
                  max={1.3}
                  step={0.05}
                  value={speed}
                  onChange={(e) => setSpeed(parseFloat(e.target.value))}
                  className="w-full"
                  aria-label="Playback speed"
                  aria-valuetext={`${speed.toFixed(2)}x speed`}
                />
                <div className="hint mt-1 flex justify-between text-xs">
                  <span>0.7x</span>
                  <span>1.0x</span>
                  <span>1.3x</span>
                </div>
              </div>

              <div>
                <label htmlFor="pause-slider" className="label block text-sm font-medium mb-1.5">
                  Sentence pause <span className="hint font-mono">{pauseMs}ms</span>
                </label>
                <input
                  id="pause-slider"
                  type="range"
                  min={0}
                  max={1000}
                  step={50}
                  value={pauseMs}
                  onChange={(e) => setPauseMs(Number.parseInt(e.target.value, 10))}
                  className="w-full"
                  aria-label="Pause between sentences in milliseconds"
                  aria-valuetext={`${pauseMs} milliseconds`}
                />
                <div className="hint mt-1 flex justify-between text-xs">
                  <span>0ms</span>
                  <span>500ms</span>
                  <span>1s</span>
                </div>
              </div>

              <div>
                <label htmlFor="chunk-size-slider" className="label block text-sm font-medium mb-1.5">
                  Chunk size <span className="hint font-mono">{chunkSize} chars</span>
                </label>
                <input
                  id="chunk-size-slider"
                  type="range"
                  min={100}
                  max={5000}
                  step={100}
                  value={chunkSize}
                  onChange={(e) => setChunkSize(Number.parseInt(e.target.value, 10))}
                  className="w-full"
                  aria-label="Chunk size in characters"
                  aria-valuetext={`${chunkSize} characters`}
                />
                <div className="hint mt-1 flex justify-between text-xs">
                  <span>100</span>
                  <span>800</span>
                  <span>5k</span>
                </div>
              </div>

              <div>
                <label htmlFor="crossfade-slider" className="label block text-sm font-medium mb-1.5">
                  Crossfade <span className="hint font-mono">{crossfadeMs}ms</span>
                </label>
                <input
                  id="crossfade-slider"
                  type="range"
                  min={0}
                  max={200}
                  step={10}
                  value={crossfadeMs}
                  onChange={(e) => setCrossfadeMs(Number.parseInt(e.target.value, 10))}
                  className="w-full"
                  aria-label="Crossfade duration in milliseconds"
                  aria-valuetext={`${crossfadeMs} milliseconds`}
                />
                <div className="hint mt-1 flex justify-between text-xs">
                  <span>0ms</span>
                  <span>120ms</span>
                  <span>200ms</span>
                </div>
              </div>

              <div>
                <label htmlFor="effects-select" className="label block text-sm font-medium mb-1.5">
                  Effects preset
                </label>
                <select
                  id="effects-select"
                  value={effectsPreset}
                  onChange={(e) => setEffectsPreset(e.target.value)}
                  className="select-field rounded-xl px-3 py-2 text-sm"
                >
                  <option value="dry">Dry</option>
                  <option value="warm">Warm</option>
                  <option value="broadcast">Broadcast</option>
                  <option value="telephone">Telephone</option>
                  <option value="cinematic">Cinematic</option>
                </select>
                <p className="hint mt-1 text-xs">
                  Shapes the final voice tone before export.
                </p>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div role="alert" className="banner-error rounded-xl px-3 py-2.5">
            <p className="text-sm">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={submitting || isGenerating}
          className="btn-primary w-full rounded-xl py-2.5 text-sm font-semibold disabled:opacity-50"
        >
          {submitting ? "Queuing..." : isGenerating ? "Generating..." : "Generate audio"}
        </button>
      </form>

      {jobId && !completedJob && (
        <section aria-label="Generation progress">
          <JobProgress jobId={jobId} onComplete={setCompletedJob} />
        </section>
      )}

      {completedJob && completedJob.status === "completed" && completedJob.output_id && (
        <section aria-label="Generated audio" aria-live="polite">
          <div className="mb-3 flex items-center gap-2.5">
            <h2 className="section-title text-sm font-semibold">Generated audio</h2>
            <span className="badge badge-success rounded-full px-2 py-0.5 text-xs font-medium">
              Ready
            </span>
          </div>
          <AudioPlayer outputId={completedJob.output_id} />
        </section>
      )}

      {completedJob && completedJob.status === "failed" && (
        <div role="alert" className="banner-error rounded-xl p-4">
          <p className="text-sm font-medium mb-0.5">Generation failed</p>
          <p className="text-sm">{completedJob.error}</p>
        </div>
      )}

      {completedJob && completedJob.status === "cancelled" && (
        <div role="status" className="panel rounded-xl p-4">
          <p className="text-sm font-medium mb-0.5">Generation cancelled</p>
          <p className="text-sm">The job was cancelled before completion.</p>
        </div>
      )}
    </div>
  );
}
