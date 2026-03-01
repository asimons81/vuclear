"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  onRecordingComplete: (blob: Blob) => void;
};

type RecordState = "idle" | "recording" | "done";

export default function VoiceRecorder({ onRecordingComplete }: Props) {
  const [state, setState] = useState<RecordState>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  function clearTimer() {
    if (timerRef.current) clearInterval(timerRef.current);
  }

  async function startRecording() {
    setError(null);
    chunksRef.current = [];
    setElapsed(0);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: getPreferredMime() });
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        cancelAnimationFrame(animRef.current!);
        const blob = new Blob(chunksRef.current, { type: mr.mimeType });
        onRecordingComplete(blob);
        setState("done");
      };

      // Waveform visualizer
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      drawWaveform();

      mr.start(100);
      setState("recording");

      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Microphone access denied";
      setError(msg);
    }
  }

  function stopRecording() {
    clearTimer();
    mediaRecorderRef.current?.stop();
  }

  function drawWaveform() {
    const canvas = canvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext("2d")!;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
      animRef.current = requestAnimationFrame(draw);
      analyser!.getByteTimeDomainData(dataArray);

      ctx.fillStyle = "#f1f5f9";
      ctx.fillRect(0, 0, canvas!.width, canvas!.height);

      ctx.lineWidth = 2;
      ctx.strokeStyle = "#6366f1";
      ctx.beginPath();

      const sliceWidth = canvas!.width / bufferLength;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128;
        const y = (v * canvas!.height) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }
      ctx.lineTo(canvas!.width, canvas!.height / 2);
      ctx.stroke();
    }
    draw();
  }

  useEffect(() => () => clearTimer(), []);

  const fmtTime = (s: number) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="space-y-3">
      <canvas
        ref={canvasRef}
        width={400}
        height={60}
        className="w-full rounded-lg bg-slate-100"
        aria-label="Audio waveform visualizer"
      />

      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}

      <div className="flex items-center gap-3">
        {state === "idle" && (
          <button
            onClick={startRecording}
            className="flex items-center gap-2 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
            aria-label="Start recording"
          >
            <span className="w-3 h-3 rounded-full bg-white" />
            Record
          </button>
        )}

        {state === "recording" && (
          <>
            <span className="flex items-center gap-2 text-red-600 font-mono font-semibold">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              {fmtTime(elapsed)}
            </span>
            <button
              onClick={stopRecording}
              disabled={elapsed < 5}
              className="bg-gray-700 hover:bg-gray-800 disabled:opacity-40 text-white px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500"
              aria-label="Stop recording (minimum 5 seconds)"
            >
              Stop {elapsed < 5 ? `(${5 - elapsed}s)` : ""}
            </button>
          </>
        )}

        {state === "done" && (
          <span className="text-green-600 font-medium">
            Recording captured ({fmtTime(elapsed)})
          </span>
        )}
      </div>
    </div>
  );
}

function getPreferredMime(): string {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  return types.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
}
