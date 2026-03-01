const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type VoiceProfile = {
  voice_id: string;
  name: string;
  duration_s: number;
  created_at: string;
  engine: string;
};

export type Job = {
  job_id: string;
  voice_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress_pct: number;
  output_id: string | null;
  error: string | null;
  created_at: string;
};

export type Output = {
  output_id: string;
  job_id: string;
  voice_id: string;
  script: string;
  duration_s: number;
  created_at: string;
};

export type HealthResponse = {
  status: string;
  engine: string;
  engine_loaded: boolean;
  engine_license: string;
  commercial_ok: boolean;
  gpu: boolean;
  gpu_name: string | null;
  denoise: boolean;
};

async function req<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Accept": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// Voices
export const api = {
  voices: {
    list: () => req<VoiceProfile[]>("/api/v1/voices"),
    create: (form: FormData) =>
      req<VoiceProfile>("/api/v1/voices", { method: "POST", body: form }),
    delete: (voiceId: string) =>
      fetch(`${API_BASE}/api/v1/voices/${voiceId}`, { method: "DELETE" }),
  },

  synthesize: (body: {
    voice_id: string;
    script: string;
    speed: number;
    pause_ms: number;
  }) =>
    req<{ job_id: string; status: string }>("/api/v1/synthesize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  jobs: {
    get: (jobId: string) => req<Job>(`/api/v1/jobs/${jobId}`),
    list: () => req<Job[]>("/api/v1/jobs"),
  },

  outputs: {
    list: () => req<Output[]>("/api/v1/outputs"),
    downloadUrl: (outputId: string, format: "wav" | "mp3") =>
      `${API_BASE}/api/v1/outputs/${outputId}/download?format=${format}`,
    delete: (outputId: string) =>
      fetch(`${API_BASE}/api/v1/outputs/${outputId}`, { method: "DELETE" }),
  },

  health: () => req<HealthResponse>("/api/v1/health"),
};
