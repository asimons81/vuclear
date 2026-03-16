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
      const recorder = new MediaRecorder(stream, { mimeType: getPreferredMime() });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        if (animRef.current) cancelAnimationFrame(animRef.current);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        onRecordingComplete(blob);
        setState("done");
      };

      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      drawWaveform();

      recorder.start(100);
      setState("recording");
      timerRef.current = setInterval(() => setElapsed((seconds) => seconds + 1), 1000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Microphone access denied");
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

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animRef.current = requestAnimationFrame(draw);
      analyser.getByteTimeDomainData(dataArray);

      const styles = getComputedStyle(document.documentElement);
      const fill = styles.getPropertyValue("--surface-soft").trim() || "#edf4f2";
      const stroke = styles.getPropertyValue("--accent").trim() || "#4fb7a0";
      const width = canvas.width;
      const height = canvas.height;

      ctx.fillStyle = fill;
      ctx.fillRect(0, 0, width, height);
      ctx.lineWidth = 2;
      ctx.strokeStyle = stroke;
      ctx.beginPath();

      const sliceWidth = width / bufferLength;
      let x = 0;

      for (let i = 0; i < bufferLength; i += 1) {
        const value = dataArray[i] / 128;
        const y = (value * height) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }

      ctx.lineTo(width, height / 2);
      ctx.stroke();
    };

    draw();
  }

  useEffect(() => () => clearTimer(), []);

  const fmtTime = (seconds: number) =>
    `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

  return (
    <div className="space-y-3">
      <canvas
        ref={canvasRef}
        width={800}
        height={120}
        className="waveform w-full rounded-xl"
        style={{ height: "60px" }}
        aria-label="Audio waveform visualizer"
      />

      {error && (
        <div role="alert" className="banner-error rounded-xl px-3 py-2.5">
          <p className="text-sm">{error}</p>
        </div>
      )}

      <div className="flex items-center gap-3">
        {state === "idle" && (
          <button
            type="button"
            onClick={startRecording}
            className="button-record flex items-center gap-2 px-4 py-2 rounded-xl text-sm"
            aria-label="Start recording"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-white" aria-hidden="true" />
            Record
          </button>
        )}

        {state === "recording" && (
          <>
            <span className="flex items-center gap-2 font-mono font-semibold text-sm" style={{ color: "var(--danger)" }}>
              <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "var(--danger)" }} aria-hidden="true" />
              {fmtTime(elapsed)}
            </span>
            <button
              type="button"
              onClick={stopRecording}
              disabled={elapsed < 5}
              className="button-stop px-4 py-2 rounded-xl text-sm"
              aria-label="Stop recording (minimum 5 seconds)"
            >
              Stop {elapsed < 5 ? `(${5 - elapsed}s)` : ""}
            </button>
          </>
        )}

        {state === "done" && (
          <span className="text-sm font-medium" style={{ color: "var(--success)" }}>
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
  return types.find((type) => MediaRecorder.isTypeSupported(type)) ?? "";
}
