"use client";

import { api } from "@/lib/api";

type Props = {
  outputId: string;
};

export default function AudioPlayer({ outputId }: Props) {
  const wavUrl = api.outputs.downloadUrl(outputId, "wav");
  const mp3Url = api.outputs.downloadUrl(outputId, "mp3");

  return (
    <div className="panel rounded-2xl p-4 space-y-3">
      <audio src={wavUrl} controls className="w-full" aria-label="Generated audio" />

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
