import * as THREE from "three";

export const EARTH_R = 1.6;

export function latLonToVec3(lat: number, lon: number, r = EARTH_R): THREE.Vector3 {
  const phi = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lon + 180);
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta),
  );
}

export function vec3ToLatLon(v: THREE.Vector3): { lat: number; lon: number } {
  const r = v.length();
  const lat = 90 - THREE.MathUtils.radToDeg(Math.acos(THREE.MathUtils.clamp(v.y / r, -1, 1)));
  const lon = THREE.MathUtils.radToDeg(Math.atan2(v.z, -v.x)) - 180;
  return { lat, lon: ((lon + 540) % 360) - 180 };
}

export function disposeObject(obj: THREE.Object3D) {
  obj.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (mesh.geometry) mesh.geometry.dispose();
    const mat = mesh.material as THREE.Material | THREE.Material[] | undefined;
    if (Array.isArray(mat)) mat.forEach((m) => m.dispose());
    else mat?.dispose();
  });
}

export function makeTextSprite(text: string, color = "#f2f0ea"): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 128;
  const ctx = canvas.getContext("2d")!;
  ctx.clearRect(0, 0, 512, 128);
  ctx.font = "600 36px 'Source Sans 3', 'Segoe UI', sans-serif";
  ctx.fillStyle = "rgba(8,12,18,0.55)";
  const w = Math.min(500, ctx.measureText(text).width + 28);
  ctx.fillRect(8, 40, w, 52);
  ctx.fillStyle = color;
  ctx.fillText(text, 22, 76);
  const map = new THREE.CanvasTexture(canvas);
  map.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({ map, transparent: true, depthTest: false }),
  );
  sprite.scale.set(0.42, 0.105, 1);
  sprite.renderOrder = 20;
  return sprite;
}
