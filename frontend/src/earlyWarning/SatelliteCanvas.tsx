import { useEffect, useRef } from "react";

function colorFor(v: number, imagery: string): [number, number, number] {
  if (imagery === "visible") {
    const g = Math.round(40 + v * 200);
    return [g, g, Math.min(255, g + 20)];
  }
  // IR: cold = white/cyan, warm = navy
  const t = Math.max(-90, Math.min(20, v));
  const u = (t + 90) / 110;
  if (u < 0.35) return [255, 255, Math.round(255 - u * 200)];
  if (u < 0.55) return [80, Math.round(180 - u * 80), 255];
  if (u < 0.75) return [40, 80, Math.round(120 + u * 80)];
  return [12, 18, 40];
}

export function SatelliteCanvas({
  frame,
  imagery,
  busy,
}: {
  frame: { lats: number[]; lons: number[]; values: number[][] } | null;
  imagery: string;
  busy?: boolean;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c || !frame?.values?.length) return;
    const rows = frame.values.length;
    const cols = frame.values[0].length;
    c.width = cols;
    c.height = rows;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const img = ctx.createImageData(cols, rows);
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const [r, g, b] = colorFor(frame.values[y][x], imagery);
        const i = (y * cols + x) * 4;
        img.data[i] = r;
        img.data[i + 1] = g;
        img.data[i + 2] = b;
        img.data[i + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }, [frame, imagery]);
  return (
    <div className="sat-frame">
      <canvas ref={ref} />
      <span>
        {busy && !frame
          ? "Scanning this fix…"
          : frame
            ? "Synthetic diagnostic · not live satellite"
            : "No scan yet — run detection"}
      </span>
    </div>
  );
}
