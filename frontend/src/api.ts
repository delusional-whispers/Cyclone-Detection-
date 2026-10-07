import type { CycloneSummary, Forecast, TrackPoint } from "./types";

const json = async <T>(path: string, signal?: AbortSignal): Promise<T> => {
  const r = await fetch(path, { signal });
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.json() as Promise<T>;
};

export const api = {
  health: (signal?: AbortSignal) => json<{ live_data: boolean; neural_models_trained: boolean }>("/api/health", signal),
  cyclones: (signal?: AbortSignal) => json<{ cyclones: CycloneSummary[]; disclaimer: string }>("/api/cyclones?limit=120", signal),
  cyclone: (id: string, signal?: AbortSignal) => json<CycloneSummary & { track: TrackPoint[] }>("/api/cyclones/" + id, signal),
  forecast: (id: string, timeIndex: number, model: string, ensemble = 11, signal?: AbortSignal) =>
    json<Forecast>(
      `/api/cyclones/${id}/forecast?time_index=${timeIndex}&model=${model}&ensemble_size=${ensemble}`,
      signal,
    ),
  weather: (id: string, timeIndex: number, signal?: AbortSignal) =>
    json<unknown>(`/api/weather?storm_id=${id}&time_index=${timeIndex}`, signal),
  models: (signal?: AbortSignal) => json<unknown>("/api/models", signal),
  evaluation: (signal?: AbortSignal) => json<unknown>("/api/evaluation", signal),
  earlyWarningMeta: (signal?: AbortSignal) => json<unknown>("/api/early-warning/meta", signal),
  analyze: (stormId: string, timeIndex: number, imagery: string, region: string, signal?: AbortSignal) =>
    json<unknown>(
      `/api/early-warning/analyze?storm_id=${encodeURIComponent(stormId)}&time_index=${timeIndex}&imagery=${imagery}&region=${region}`,
      signal,
    ),
};
