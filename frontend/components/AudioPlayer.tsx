"use client";

import { api } from "@/lib/api";

type Props = {
  outputId: string;
};

export default function AudioPlayer({ outputId }: Props) {
  const wavUrl = api.outputs.downloadUrl(outputId, "wav");
  const mp3Url = api.outputs.downloadUrl(outputId, "mp3");

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
      <audio
        src={wavUrl}
        controls
        className="w-full"
        aria-label="Generated audio"
      />

      <div className="flex gap-2">
        <a
          href={wavUrl}
          download={`output-${outputId.slice(0, 8)}.wav`}
          className="flex-1 text-center bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          aria-label="Download WAV file"
        >
          Download WAV
        </a>
        <a
          href={mp3Url}
          download={`output-${outputId.slice(0, 8)}.mp3`}
          className="flex-1 text-center bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium py-2 px-4 rounded-lg transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
          aria-label="Download MP3 file"
        >
          Download MP3
        </a>
      </div>
    </div>
  );
}
