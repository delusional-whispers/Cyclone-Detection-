export type TrackPoint = {
  iso_time: string;
  hours_from_start: number;
  lat: number;
  lon: number;
  wind_kt: number | null;
  pres_hpa: number | null;
  category: string;
  imd_code: string;
  dist2land_km: number | null;
  heading_deg: number | null;
  speed_kt: number | null;
  radius_km: number | null;
  sub_basin: string;
};

export type CycloneSummary = {
  id: string;
  name: string;
  season: number;
  start_time: string;
  end_time: string;
  genesis_basin: string;
  sub_basin: string;
  peak_wind_kt: number | null;
  min_pres_hpa: number | null;
  peak_category: string | null;
  split: string;
  n_points: number;
  landfall_hint: { lat: number; lon: number; iso_time: string } | null;
};

export type Forecast = {
  storm_id: string;
  model: string;
  model_trained: boolean;
  disclaimer: string;
  now: {
    iso_time: string;
    lat: number;
    lon: number;
    wind_kt: number | null;
    pres_hpa: number | null;
    category: string;
    heading_deg: number;
    heading: string;
    speed_kt: number;
    speed_kmh: number;
  };
  mean_track: Array<{
    lead_hours: number;
    lat: number;
    lon: number;
    wind_kt: number;
    pres_hpa: number;
    category: string;
    spread_km: number;
  }>;
  median_track: Array<{ lead_hours: number; lat: number; lon: number }>;
  ensemble: Array<{ member: number; track: Forecast["mean_track"] }>;
  uncertainty_cone: Array<{ lead_hours: number; lat: number; lon: number; radius_km: number }>;
  rapid_intensification_probability: number;
  rapid_weakening_probability: number;
  landfall: Record<string, unknown>;
  formation: { window_hours: Record<string, number>; method: string; disclaimer: string };
  verification?: { errors: Record<string, number | null>; metric: string };
  detection?: {
    cyclone_probability: number;
    latitude: number;
    longitude: number;
    max_wind_speed: number;
    central_pressure: number | null;
    radius_km: number;
    imd_class: string;
    disclaimer: string;
  };
};

export type Layers = {
  wind: boolean;
  pressure: boolean;
  temperature: boolean;
  humidity: boolean;
  precipitation: boolean;
  sst: boolean;
  satellite: boolean;
  clouds: boolean;
  observed: boolean;
  aiTrack: boolean;
  ensemble: boolean;
  cone: boolean;
  landfall: boolean;
  historical: boolean;
  riskZones: boolean;
};
