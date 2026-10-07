import * as THREE from "three";
import earcut from "earcut";
import { EARTH_R, latLonToVec3 } from "./math";

type Ring = number[][];

const FOCUS = new Set(["India", "Sri Lanka", "Bangladesh", "Myanmar", "Pakistan", "Oman", "Maldives", "Nepal", "Bhutan"]);

function ringsFromGeom(geom: { type: string; coordinates: any }): Ring[] {
  const out: Ring[] = [];
  const walk = (coords: number[][]) => {
    if (coords.length < 4) return;
    out.push(coords.map(([lon, lat]) => [lat, lon]));
  };
  if (geom.type === "Polygon") geom.coordinates.forEach(walk);
  if (geom.type === "MultiPolygon") geom.coordinates.forEach((poly: number[][][]) => poly.forEach(walk));
  return out;
}

function lineGeom(rings: Ring[], radius: number): THREE.BufferGeometry {
  const positions: number[] = [];
  for (const ring of rings) {
    for (let i = 0; i < ring.length - 1; i++) {
      const a = latLonToVec3(ring[i][0], ring[i][1], radius);
      const b = latLonToVec3(ring[i + 1][0], ring[i + 1][1], radius);
      positions.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  return g;
}

function fillMesh(ring: Ring, color: number, opacity: number, radius: number): THREE.Mesh | null {
  if (ring.length < 4) return null;
  const flat: number[] = [];
  for (const pt of ring) {
    flat.push(pt[1], pt[0]);
  }
  const idx = earcut(flat, null, 2);
  if (idx.length < 3) return null;
  const pos: number[] = [];
  const nrm: number[] = [];
  for (let i = 0; i < idx.length; i++) {
    const pt = ring[idx[i]];
    const v = latLonToVec3(pt[0], pt[1], radius);
    pos.push(v.x, v.y, v.z);
    const n = v.clone().normalize();
    nrm.push(n.x, n.y, n.z);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
  return new THREE.Mesh(
    g,
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      depthWrite: false,
      side: THREE.DoubleSide,
    }),
  );
}

export async function buildCountryLayer(): Promise<THREE.Group> {
  const group = new THREE.Group();
  const res = await fetch("/geo/countries.json");
  const fc = await res.json();
  const worldRings: Ring[] = [];
  const indiaRings: Ring[] = [];

  for (const f of fc.features as Array<{ properties: { ADMIN: string }; geometry: any }>) {
    const rings = ringsFromGeom(f.geometry);
    worldRings.push(...rings);
    if (FOCUS.has(f.properties.ADMIN)) indiaRings.push(...rings);
    if (f.properties.ADMIN === "India") {
      for (const ring of rings) {
        const mesh = fillMesh(ring, 0xc4a574, 0.18, EARTH_R + 0.003);
        if (mesh) {
          mesh.renderOrder = 2;
          group.add(mesh);
        }
      }
    }
  }

  const world = new THREE.LineSegments(
    lineGeom(worldRings, EARTH_R + 0.004),
    new THREE.LineBasicMaterial({ color: 0x8ea4b8, transparent: true, opacity: 0.28 }),
  );
  world.renderOrder = 3;
  group.add(world);

  const region = new THREE.LineSegments(
    lineGeom(indiaRings, EARTH_R + 0.006),
    new THREE.LineBasicMaterial({ color: 0xf3e6c8, transparent: true, opacity: 0.95 }),
  );
  region.renderOrder = 4;
  group.add(region);

  // NIO domain box
  const box: Ring = [];
  for (let lon = 50; lon <= 110; lon += 2) box.push([0, lon]);
  for (let lat = 0; lat <= 30; lat += 2) box.push([lat, 110]);
  for (let lon = 110; lon >= 50; lon -= 2) box.push([30, lon]);
  for (let lat = 30; lat >= 0; lat -= 2) box.push([lat, 50]);
  box.push([0, 50]);
  group.add(
    new THREE.LineSegments(
      lineGeom([box], EARTH_R + 0.008),
      new THREE.LineBasicMaterial({ color: 0x6aa7c9, transparent: true, opacity: 0.45 }),
    ),
  );

  return group;
}

export function buildGraticule(): THREE.LineSegments {
  const rings: Ring[] = [];
  for (let lat = -80; lat <= 80; lat += 20) {
    const r: Ring = [];
    for (let lon = -180; lon <= 180; lon += 4) r.push([lat, lon]);
    rings.push(r);
  }
  for (let lon = -180; lon < 180; lon += 20) {
    const r: Ring = [];
    for (let lat = -80; lat <= 80; lat += 4) r.push([lat, lon]);
    rings.push(r);
  }
  return new THREE.LineSegments(
    lineGeom(rings, EARTH_R + 0.0015),
    new THREE.LineBasicMaterial({ color: 0x2a4158, transparent: true, opacity: 0.35 }),
  );
}
