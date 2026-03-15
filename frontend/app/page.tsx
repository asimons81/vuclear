"use client";

import { useState, useRef } from "react";
import { api, VoiceProfile } from "@/lib/api";
import VoiceRecorder from "@/components/VoiceRecorder";
import useSWR from "swr";
import Link from "next/link";

type InputMode = "upload" | "record";

export default function VoicesPage() {
  const [mode, setMode] = useState<InputMode>("upload");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
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
      setSuccess(`Voice profile "${profile.name}" saved (${profile.duration_s.toFixed(1)}s).`);
      setAudioFile(null);
      setName("");
      setConsent(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
      mutate();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(voiceId: string) {
    if (!confirm("Delete this voice profile? This cannot be undone.")) return;
    await api.voices.delete(voiceId);
    mutate();
  }

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl font-bold mb-1">Voice Setup</h1>
        <p className="text-gray-500 text-sm">
          Upload or record a 5–30 second voice sample to create a cloneable voice profile.
        </p>
      </div>

      {/* Create new voice */}
      <section className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Create Voice Profile</h2>

        {/* Mode tabs */}
        <div className="flex gap-2 mb-6" role="tablist" aria-label="Input method">
          {(["upload", "record"] as InputMode[]).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              onClick={() => { setMode(m); setAudioFile(null); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                mode === m
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {m === "upload" ? "Upload File" : "Record Mic"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {mode === "upload" ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Audio file (WAV, MP3, OGG, M4A, FLAC — max 50MB)
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,.flac,.wav,.mp3,.ogg,.m4a"
                onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-600 file:font-medium hover:file:bg-indigo-100"
                aria-label="Upload audio file"
              />
              {audioFile && (
                <p className="mt-1 text-xs text-gray-500">
                  Selected: {audioFile.name} ({(audioFile.size / 1024 / 1024).toFixed(1)} MB)
                </p>
              )}
            </div>
          ) : (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">
                Record from microphone (minimum 5 seconds)
              </p>
              <VoiceRecorder onRecordingComplete={handleRecordingComplete} />
              {audioFile && (
                <p className="mt-2 text-xs text-green-600">Recording ready to upload.</p>
              )}
            </div>
          )}

          <div>
            <label htmlFor="voice-name" className="block text-sm font-medium text-gray-700 mb-1">
              Profile name
            </label>
            <input
              id="voice-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. My Voice, John's Narration"
              maxLength={80}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              aria-label="Voice profile name"
            />
          </div>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              aria-required="true"
              aria-label="Consent to voice cloning"
            />
            <span className="text-sm text-gray-700">
              I own this voice or have explicit permission to clone it. I understand I am responsible
              for how generated audio is used.
            </span>
          </label>

          {error && (
            <p role="alert" className="text-red-600 text-sm">
              {error}
            </p>
          )}
          {success && (
            <p role="status" className="text-green-600 text-sm">
              {success}{" "}
              <Link href="/studio" className="underline font-medium">
                Go to Studio →
              </Link>
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold py-3 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            aria-label="Save voice profile"
          >
            {submitting ? "Processing…" : "Save Voice Profile"}
          </button>
        </form>
      </section>

      {/* Saved voices list */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Saved Voice Profiles</h2>
        {!voices ? (
          <p className="text-gray-400 animate-pulse">Loading…</p>
        ) : voices.length === 0 ? (
          <p className="text-gray-500 text-sm">No voice profiles yet. Create one above.</p>
        ) : (
          <ul className="space-y-2" aria-label="Voice profiles list">
            {voices.map((v) => (
              <li
                key={v.voice_id}
                className="flex items-center justify-between bg-white rounded-xl border border-gray-200 px-4 py-3"
              >
                <div>
                  <p className="font-medium text-sm">{v.name}</p>
                  <p className="text-xs text-gray-400">
                    {v.duration_s.toFixed(1)}s · {v.engine} ·{" "}
                    {new Date(v.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(v.voice_id)}
                  className="text-xs text-red-500 hover:text-red-700 font-medium focus:outline-none focus:ring-2 focus:ring-red-400 rounded px-2 py-1"
                  aria-label={`Delete voice profile ${v.name}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
