"use client";

import { useState, useRef } from "react";
import { api, VoiceProfile } from "@/lib/api";
import VoiceRecorder from "@/components/VoiceRecorder";
import useSWR from "swr";
import Link from "next/link";

type InputMode = "upload" | "record";

export default function VoicesContent() {
  const [mode, setMode] = useState<InputMode>("upload");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: voices, mutate } = useSWR<VoiceProfile[]>("/voices", api.voices.list);

  function handleRecordingComplete(blob: Blob) {
    const file = new File([blob], "recording.webm", { type: blob.type });
    setAudioFile(file);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!audioFile) {
      setError("Please provide a voice recording or upload an audio file.");
      return;
    }
    if (!consent) {
      setError("You must confirm you own or have permission to clone this voice.");
      return;
    }
    if (!name.trim()) {
      setError("Please enter a name for this voice profile.");
      return;
    }

    const form = new FormData();
    form.append("file", audioFile);
    form.append("name", name.trim());
    form.append("consent", "true");

    setSubmitting(true);
    try {
      const profile = await api.voices.create(form);
      setSuccess(`"${profile.name}" saved — ${profile.duration_s.toFixed(1)}s sample.`);
      setAudioFile(null);
      setName("");
      setConsent(false);
      setMode("upload");
      if (fileInputRef.current) fileInputRef.current.value = "";
      mutate();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(voiceId: string) {
    setPendingDeleteId(null);
    await api.voices.delete(voiceId);
    mutate();
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Voices</h1>
        <p className="text-sm text-slate-500">
          Manage your voice profiles. Each profile uses a 5–30 second reference sample.
        </p>
      </div>

      {/* Create new voice */}
      <section className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-sm font-semibold text-slate-900 mb-4">Add a voice</h2>

        {/* Mode tabs — segmented control */}
        <div
          className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5 gap-0.5 mb-6"
          role="tablist"
          aria-label="Input method"
        >
          {(["upload", "record"] as InputMode[]).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              onClick={() => {
                setMode(m);
                setAudioFile(null);
              }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500 ${
                mode === m
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {m === "upload" ? "Upload file" : "Record mic"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {mode === "upload" ? (
            <div>
              <label
                htmlFor="audio-file-input"
                className="block text-sm font-medium text-slate-700 mb-1.5"
              >
                Audio file
                <span className="text-slate-400 font-normal ml-1.5">
                  WAV, MP3, OGG, WebM, M4A, FLAC — max 50 MB
                </span>
              </label>
              <input
                ref={fileInputRef}
                id="audio-file-input"
                type="file"
                accept="audio/*,.flac,.wav,.mp3,.ogg,.webm,.m4a"
                onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-600 file:font-medium file:text-sm hover:file:bg-indigo-100 file:transition-colors"
              />
              {audioFile && (
                <p className="mt-1.5 text-xs text-slate-500">
                  {audioFile.name} &middot; {(audioFile.size / 1024 / 1024).toFixed(1)} MB
                </p>
              )}
            </div>
          ) : (
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2">
                Record from microphone
                <span className="text-slate-400 font-normal ml-1.5">minimum 5 seconds</span>
              </p>
              <VoiceRecorder onRecordingComplete={handleRecordingComplete} />
              {audioFile && (
                <p className="mt-2 text-xs text-green-700 font-medium">Recording ready.</p>
              )}
            </div>
          )}

          <div>
            <label
              htmlFor="voice-name"
              className="block text-sm font-medium text-slate-700 mb-1.5"
            >
              Profile name
            </label>
            <input
              id="voice-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. My Voice, John Narration"
              maxLength={80}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-slate-700">
              I own this voice or have explicit permission to clone it. I understand I am
              responsible for how generated audio is used.
            </span>
          </label>

          {error && (
            <div
              role="alert"
              className="bg-red-50 border border-red-200 rounded-lg px-3 py-2.5"
            >
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {success && (
            <div
              role="status"
              className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-3 py-2.5"
            >
              <p className="text-sm text-green-700">{success}</p>
              <Link
                href="/studio"
                className="text-sm font-medium text-green-700 hover:text-green-900 shrink-0 ml-3 whitespace-nowrap"
              >
                Open Studio →
              </Link>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            {submitting ? "Saving…" : "Save profile"}
          </button>
        </form>
      </section>

      {/* Saved voices list */}
      <section>
        <h2 className="text-sm font-semibold text-slate-900 mb-3">Your voices</h2>
        {!voices ? (
          <p className="text-sm text-slate-500 animate-pulse">Loading…</p>
        ) : voices.length === 0 ? (
          <p className="text-sm text-slate-500">
            No voices yet. Add one above to get started.
          </p>
        ) : (
          <ul className="space-y-2" aria-label="Voice profiles">
            {voices.map((v) => (
              <li
                key={v.voice_id}
                className="flex items-center justify-between bg-white rounded-xl border border-slate-200 px-4 py-3"
              >
                <div>
                  <p className="font-medium text-sm text-slate-900">{v.name}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {v.duration_s.toFixed(1)}s &middot;{" "}
                    {new Date(v.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-medium">
                    {v.engine}
                  </span>
                  {pendingDeleteId === v.voice_id ? (
                    <span className="flex items-center gap-1">
                      <span className="text-xs text-slate-500">Delete?</span>
                      <button
                        onClick={() => handleDelete(v.voice_id)}
                        aria-label={`Confirm delete ${v.name}`}
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
                      onClick={() => setPendingDeleteId(v.voice_id)}
                      className="text-xs text-slate-500 hover:text-red-600 font-medium px-2 py-1.5 rounded hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
                      aria-label={`Delete voice profile ${v.name}`}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
