"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import VoiceRecorder from "@/components/VoiceRecorder";
import { api, VoiceProfile } from "@/lib/api";

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
    setAudioFile(new File([blob], "recording.webm", { type: blob.type }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!audioFile) return setError("Please provide a voice recording or upload an audio file.");
    if (!consent) return setError("You must confirm you own or have permission to clone this voice.");
    if (!name.trim()) return setError("Please enter a name for this voice profile.");

    const form = new FormData();
    form.append("file", audioFile);
    form.append("name", name.trim());
    form.append("consent", "true");

    setSubmitting(true);
    try {
      const profile = await api.voices.create(form);
      setSuccess(`"${profile.name}" saved. ${profile.duration_s.toFixed(1)}s sample.`);
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
        <h1 className="section-title text-2xl font-bold mb-1">Voices</h1>
        <p className="section-copy text-sm">
          Manage your voice profiles. Each profile uses a 5-30 second reference sample.
        </p>
      </div>

      <section className="panel rounded-2xl p-6">
        <h2 className="section-title text-sm font-semibold mb-4">Add a voice</h2>

        <div className="segmented inline-flex rounded-xl p-0.5 gap-0.5 mb-6" role="tablist" aria-label="Input method">
          {(["upload", "record"] as InputMode[]).map((value) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={mode === value}
              onClick={() => {
                setMode(value);
                setAudioFile(null);
              }}
              className={`segmented-tab px-4 py-1.5 rounded-lg text-sm font-medium ${mode === value ? "segmented-tab-active" : ""}`}
            >
              {value === "upload" ? "Upload file" : "Record mic"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {mode === "upload" ? (
            <div>
              <label htmlFor="audio-file-input" className="label block text-sm font-medium mb-1.5">
                Audio file
                <span className="hint font-normal ml-1.5">
                  WAV, MP3, OGG, WebM, M4A, FLAC. Max 50 MB
                </span>
              </label>
              <input
                ref={fileInputRef}
                id="audio-file-input"
                type="file"
                accept="audio/*,.flac,.wav,.mp3,.ogg,.webm,.m4a"
                onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                className="field-file block w-full rounded-xl px-3 py-2 text-sm"
              />
              {audioFile && (
                <p className="hint mt-1.5 text-xs">
                  {audioFile.name} · {(audioFile.size / 1024 / 1024).toFixed(1)} MB
                </p>
              )}
            </div>
          ) : (
            <div>
              <p className="label text-sm font-medium mb-2">
                Record from microphone
                <span className="hint font-normal ml-1.5">minimum 5 seconds</span>
              </p>
              <VoiceRecorder onRecordingComplete={handleRecordingComplete} />
              {audioFile && <p className="mt-2 text-xs font-medium badge-success inline-flex px-2 py-1 rounded-full">Recording ready</p>}
            </div>
          )}

          <div>
            <label htmlFor="voice-name" className="label block text-sm font-medium mb-1.5">
              Profile name
            </label>
            <input
              id="voice-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. My Voice, John Narration"
              maxLength={80}
              className="field w-full rounded-xl px-3 py-2 text-sm"
            />
          </div>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="field-checkbox mt-0.5 h-4 w-4 rounded"
            />
            <span className="section-copy text-sm">
              I own this voice or have explicit permission to clone it. I understand I am
              responsible for how generated audio is used.
            </span>
          </label>

          {error && (
            <div role="alert" className="banner-error rounded-xl px-3 py-2.5">
              <p className="text-sm">{error}</p>
            </div>
          )}

          {success && (
            <div role="status" className="banner-success flex items-center justify-between rounded-xl px-3 py-2.5 gap-3">
              <p className="text-sm">{success}</p>
              <Link href="/studio" className="link-accent text-sm font-semibold shrink-0 whitespace-nowrap">
                Open Studio →
              </Link>
            </div>
          )}

          <button type="submit" disabled={submitting} className="btn-primary w-full rounded-xl py-2.5 text-sm font-semibold disabled:opacity-50">
            {submitting ? "Saving..." : "Save profile"}
          </button>
        </form>
      </section>

      <section>
        <h2 className="section-title text-sm font-semibold mb-3">Your voices</h2>
        {!voices ? (
          <p className="section-copy text-sm animate-pulse">Loading...</p>
        ) : voices.length === 0 ? (
          <p className="section-copy text-sm">No voices yet. Add one above to get started.</p>
        ) : (
          <ul className="space-y-2" aria-label="Voice profiles">
            {voices.map((voice) => (
              <li key={voice.voice_id} className="panel flex items-center justify-between rounded-2xl px-4 py-3">
                <div>
                  <p className="section-title font-medium text-sm">{voice.name}</p>
                  <p className="hint text-xs mt-0.5">
                    {voice.duration_s.toFixed(1)}s · {new Date(voice.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="badge text-xs px-2 py-0.5 rounded-full font-medium">
                    {voice.engine}
                  </span>
                  {pendingDeleteId === voice.voice_id ? (
                    <span className="flex items-center gap-1">
                      <span className="hint text-xs">Delete?</span>
                      <button
                        type="button"
                        onClick={() => handleDelete(voice.voice_id)}
                        aria-label={`Confirm delete ${voice.name}`}
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
                      onClick={() => setPendingDeleteId(voice.voice_id)}
                      className="btn-danger text-xs font-medium px-2 py-1.5 rounded-lg"
                      aria-label={`Delete voice profile ${voice.name}`}
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
