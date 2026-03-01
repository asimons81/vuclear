"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";

type Props = {
  outputId: string;
};

export default function AudioPlayer({ outputId }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  const wavUrl = api.outputs.downloadUrl(outputId, "wav");
  const mp3Url = api.outputs.downloadUrl(outputId, "mp3");

  function togglePlay() {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
    } else {
      el.play();
    }
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
      <audio
        ref={audioRef}
        src={wavUrl}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        controls
        className="w-full"
        aria-label="Generated audio player"
      />

      <div className="flex gap-3 flex-wrap">
        <a
          href={wavUrl}
          download={`voice-clone-${outputId.slice(0, 8)}.wav`}
          className="flex-1 min-w-32 text-center bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          aria-label="Download WAV file"
        >
          Download WAV
        </a>
        <a
          href={mp3Url}
          download={`voice-clone-${outputId.slice(0, 8)}.mp3`}
          className="flex-1 min-w-32 text-center bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-gray-500"
          aria-label="Download MP3 file"
        >
          Download MP3
        </a>
      </div>
    </div>
  );
}
