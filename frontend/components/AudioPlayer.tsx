"use client";

import { api } from "@/lib/api";

type Props = {
  outputId: string;
};

export default function AudioPlayer({ outputId }: Props) {
  const wavUrl = api.outputs.downloadUrl(outputId, "wav");
  const mp3Url = api.outputs.downloadUrl(outputId, "mp3");

  return (
    <div className="audio-panel rounded-2xl p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="section-title text-sm font-semibold">Playback</p>
          <p className="hint text-xs">Preview the generated file before downloading.</p>
        </div>
        <span className="badge text-xs px-2 py-0.5 rounded-full font-medium">WAV ready</span>
      </div>

      <audio src={wavUrl} controls className="audio-native" aria-label="Generated audio" />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <a
          href={wavUrl}
          download={`output-${outputId.slice(0, 8)}.wav`}
          className="btn-primary text-center rounded-xl py-2 px-4 text-sm font-semibold"
          aria-label="Download WAV file"
        >
          Download WAV
        </a>
        <a
          href={mp3Url}
          download={`output-${outputId.slice(0, 8)}.mp3`}
          className="btn-secondary text-center rounded-xl py-2 px-4 text-sm font-semibold"
          aria-label="Download MP3 file"
        >
          Download MP3
        </a>
      </div>
    </div>
  );
}
