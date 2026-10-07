import * as THREE from "three";
import type { Forecast, Layers, TrackPoint } from "../types";
import { buildCountryLayer, buildGraticule } from "./countries";
import { disposeObject, EARTH_R, latLonToVec3, makeTextSprite } from "./math";

type WeatherCell = {
  lat: number;
  lon: number;
  u_kt: number;
  v_kt: number;
  wind_kt: number;
  mslp_hpa: number;
  sst_c: number;
  precip_mm_hr: number;
  temp_c: number;
  rh: number;
  ctt_c: number;
};

export class WeatherGlobe {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera: THREE.PerspectiveCamera;
  earth = new THREE.Group();
  clouds: THREE.Mesh | null = null;
  overlays = new THREE.Group();
  windGroup = new THREE.Group();
  cycloneGroup = new THREE.Group();
  labels = new THREE.Group();
  clock = new THREE.Clock();
  dragging = false;
  lastX = 0;
  lastY = 0;
  focusLat = 16.5;
  focusLon = 82.0;
  offsetLat = 4;
  offsetLon = 0;
  distance = 2.72;
  autoRotate = false;
  follow = true;
  private windParticles: THREE.Points | null = null;
  private weatherCells: WeatherCell[] = [];
  private lastLayerKey = "";
  private hasPulse = false;
  private sun: THREE.DirectionalLight;
  private scratch = new THREE.Vector3();

  constructor(canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.05, 80);
    this.scene.background = new THREE.Color(0x04060b);

    this.scene.add(new THREE.AmbientLight(0x6e7f93, 0.5));
    this.sun = new THREE.DirectionalLight(0xfff1dd, 1.55);
    this.sun.position.copy(latLonToVec3(18, 55, 6));
    this.scene.add(this.sun);
    const fill = new THREE.DirectionalLight(0x88aacc, 0.4);
    fill.position.set(2, -1, -2);
    this.scene.add(fill);

    const loader = new THREE.TextureLoader();
    const maxAniso = this.renderer.capabilities.getMaxAnisotropy();
    const colorMap = loader.load("/textures/earth.jpg");
    colorMap.colorSpace = THREE.SRGBColorSpace;
    colorMap.anisotropy = maxAniso;
    const specMap = loader.load("/textures/earth_specular.jpg");
    const cloudMap = loader.load("/textures/earth_clouds.png");
    cloudMap.colorSpace = THREE.SRGBColorSpace;

    const globe = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_R, 96, 64),
      new THREE.MeshPhongMaterial({
        map: colorMap,
        specularMap: specMap,
        specular: new THREE.Color(0x335577),
        shininess: 12,
      }),
    );
    this.earth.add(globe);

    this.clouds = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_R + 0.012, 64, 48),
      new THREE.MeshLambertMaterial({
        map: cloudMap,
        transparent: true,
        opacity: 0.28,
        depthWrite: false,
      }),
    );
    this.earth.add(this.clouds);

    const atm = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_R * 1.04, 48, 32),
      new THREE.MeshBasicMaterial({
        color: 0x4d88cc,
        transparent: true,
        opacity: 0.09,
        side: THREE.BackSide,
        depthWrite: false,
      }),
    );
    this.earth.add(atm);
    this.earth.add(buildGraticule());

    this.scene.add(this.earth);
    this.scene.add(this.overlays);
    this.scene.add(this.windGroup);
    this.scene.add(this.cycloneGroup);
    this.scene.add(this.labels);
    this.addStars();
    this.addSeaLabels();

    buildCountryLayer()
      .then((g) => this.earth.add(g))
      .catch(() => undefined);

    canvas.addEventListener("pointerdown", (e) => {
      this.dragging = true;
      this.autoRotate = false;
      this.follow = false;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener("pointerup", (e) => {
      this.dragging = false;
      canvas.releasePointerCapture(e.pointerId);
    });
    canvas.addEventListener("pointermove", (e) => {
      if (!this.dragging) return;
      this.offsetLon -= (e.clientX - this.lastX) * 0.12;
      this.offsetLat += (e.clientY - this.lastY) * 0.08;
      this.offsetLat = THREE.MathUtils.clamp(this.offsetLat, -35, 35);
      this.lastX = e.clientX;
      this.lastY = e.clientY;
    });
    canvas.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        this.distance = THREE.MathUtils.clamp(this.distance + e.deltaY * 0.0018, 2.05, 6.2);
      },
      { passive: false },
    );
  }

  private addStars() {
    const n = 1600;
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const v = this.scratch.randomDirection().multiplyScalar(18 + Math.random() * 16);
      pos.set([v.x, v.y, v.z], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    this.scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0xc9d6e5, size: 0.018 })));
  }

  private addSeaLabels() {
    const places: [string, number, number][] = [
      ["India", 22.5, 79.0],
      ["Bay of Bengal", 14.5, 88.5],
      ["Arabian Sea", 16.0, 66.0],
      ["Sri Lanka", 7.6, 80.7],
      ["Bangladesh", 23.7, 90.3],
      ["Mumbai", 19.07, 72.88],
      ["Chennai", 13.08, 80.27],
      ["Kolkata", 22.57, 88.36],
    ];
    for (const [name, lat, lon] of places) {
      const s = makeTextSprite(name, name === "India" ? "#f4e4c1" : "#d5deea");
      s.position.copy(latLonToVec3(lat, lon, EARTH_R + 0.05));
      this.labels.add(s);
    }
  }

  focusOn(lat: number, lon: number) {
    this.follow = true;
    this.focusLat = lat;
    this.focusLon = lon;
    this.offsetLat = 6;
    this.offsetLon = 8;
    this.distance = 2.55;
  }

  resize(w: number, h: number) {
    this.renderer.setSize(Math.max(1, w), Math.max(1, h), false);
    this.camera.aspect = w / Math.max(1, h);
    this.camera.updateProjectionMatrix();
  }

  setStorm(track: TrackPoint[], forecast: Forecast | null, timeIndex: number, layers: Layers, weather: { cells?: WeatherCell[] } | null) {
    disposeObject(this.overlays);
    disposeObject(this.cycloneGroup);
    this.overlays.clear();
    this.cycloneGroup.clear();
    this.hasPulse = false;
    const nextCells = weather?.cells ?? [];
    const layerKey = [
      layers.wind,
      layers.pressure,
      layers.temperature,
      layers.humidity,
      layers.precipitation,
      layers.sst,
      layers.satellite,
      layers.clouds,
      nextCells.length,
    ].join(":");
    if (nextCells !== this.weatherCells || layerKey !== this.lastLayerKey) {
      this.weatherCells = nextCells;
      this.lastLayerKey = layerKey;
      this.rebuildWind(layers);
    }

    if (!track.length) return;
    const idx = Math.max(0, Math.min(timeIndex, track.length - 1));
    const here = track[idx];
    if (this.follow) {
      this.focusLat = THREE.MathUtils.lerp(this.focusLat, here.lat, 0.35);
      this.focusLon = THREE.MathUtils.lerp(this.focusLon, here.lon, 0.35);
    }

    if ((layers.historical || layers.observed) && idx > 0) {
      this.overlays.add(this.lineTrack(track.slice(0, idx + 1).map((p) => latLonToVec3(p.lat, p.lon, EARTH_R + 0.018)), 0xf0c14b, 0.95));
    }
    if (forecast && layers.aiTrack) {
      this.overlays.add(this.lineTrack(forecast.mean_track.map((p) => latLonToVec3(p.lat, p.lon, EARTH_R + 0.02)), 0x7ad7ff, 0.95));
    }
    if (forecast && layers.ensemble) {
      forecast.ensemble.slice(0, 5).forEach((m, i) => {
        const pts = m.track.map((p) => latLonToVec3(p.lat, p.lon, EARTH_R + 0.016));
        this.overlays.add(this.lineTrack(pts, 0x7aa6ff, 0.18 + (i % 4) * 0.05));
      });
    }
    if (forecast && layers.cone) this.overlays.add(this.coneSurface(forecast.uncertainty_cone));
    if (forecast && layers.landfall && forecast.landfall?.possible) {
      const lat = Number(forecast.landfall.latitude ?? forecast.landfall.coast_lat);
      const lon = Number(forecast.landfall.longitude ?? forecast.landfall.coast_lon);
      if (!Number.isNaN(lat)) {
        const pulse = new THREE.Mesh(
          new THREE.SphereGeometry(0.028, 16, 16),
          new THREE.MeshBasicMaterial({ color: 0xff6b6b, transparent: true, opacity: 0.85 }),
        );
        pulse.position.copy(latLonToVec3(lat, lon, EARTH_R + 0.03));
        pulse.userData.pulse = true;
        this.hasPulse = true;
        this.overlays.add(pulse);
      }
    }

    this.buildCyclone(here);
    this.buildFieldLayer(layers);
    this.addEarlyWarning();
  }

  earlyWarning: {
    points?: Array<{ lat: number; lon: number; lead_hours: number; risk_level: number }>;
    activeLead?: number;
    riskZones?: boolean;
  } | null = null;

  setEarlyWarning(ew: WeatherGlobe["earlyWarning"]) {
    this.earlyWarning = ew;
  }

  private addEarlyWarning() {
    const ew = this.earlyWarning;
    if (!ew?.points?.length || !ew.riskZones) return;
    const colors = [0x8fa38f, 0xd4c05a, 0xe28a28, 0xe0523c, 0xa81228];
    ew.points.forEach((p) => {
      const col = colors[Math.max(0, Math.min(4, (p.risk_level || 1) - 1))];
      const m = new THREE.Mesh(
        new THREE.SphereGeometry(p.lead_hours === (ew.activeLead ?? 0) ? 0.022 : 0.012, 12, 12),
        new THREE.MeshBasicMaterial({ color: col }),
      );
      m.position.copy(latLonToVec3(p.lat, p.lon, EARTH_R + 0.026));
      this.overlays.add(m);
    });
  }

  private lineTrack(points: THREE.Vector3[], color: number, opacity: number) {
    const g = new THREE.BufferGeometry().setFromPoints(points);
    return new THREE.Line(g, new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
  }

  private coneSurface(cone: Array<{ lat: number; lon: number; radius_km: number }>) {
    const group = new THREE.Group();
    cone.forEach((c) => {
      const pts: THREE.Vector3[] = [];
      const dlat = c.radius_km / 111;
      const dlon = dlat / Math.max(0.4, Math.cos((c.lat * Math.PI) / 180));
      for (let i = 0; i <= 24; i++) {
        const a = (i / 24) * Math.PI * 2;
        pts.push(latLonToVec3(c.lat + Math.sin(a) * dlat, c.lon + Math.cos(a) * dlon, EARTH_R + 0.017));
      }
      group.add(this.lineTrack(pts, 0xe8a23a, 0.5));
    });
    return group;
  }

  private buildCyclone(here: TrackPoint) {
    const wind = here.wind_kt ?? 35;
    const group = new THREE.Group();
    const eye = new THREE.Mesh(
      new THREE.SphereGeometry(0.014, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0xffffff }),
    );
    eye.position.copy(latLonToVec3(here.lat, here.lon, EARTH_R + 0.028));
    group.add(eye);

    const pN = 420;
    const ppos = new Float32Array(pN * 3);
    for (let i = 0; i < pN; i++) {
      const t = i / pN;
      const ang = t * Math.PI * 6.5;
      const rad = 0.1 + t * (0.7 + wind / 160);
      const lat = here.lat + Math.sin(ang) * rad;
      const lon = here.lon + Math.cos(ang) * rad / Math.cos((here.lat * Math.PI) / 180);
      const v = latLonToVec3(lat, lon, EARTH_R + 0.022 + (1 - t) * 0.03);
      ppos.set([v.x, v.y, v.z], i * 3);
    }
    const pg = new THREE.BufferGeometry();
    pg.setAttribute("position", new THREE.BufferAttribute(ppos, 3));
    group.add(new THREE.Points(pg, new THREE.PointsMaterial({ color: 0xf4f7fb, size: 0.014, transparent: true, opacity: 0.8 })));
    this.cycloneGroup.add(group);
  }

  private rebuildWind(layers: Layers) {
    disposeObject(this.windGroup);
    this.windGroup.clear();
    this.windParticles = null;
    if (!this.weatherCells.length) return;
    if (layers.wind) {
      const n = 480;
      const pos = new Float32Array(n * 3);
      const col = new Float32Array(n * 3);
      const c = new THREE.Color();
      for (let i = 0; i < n; i++) {
        const cell = this.weatherCells[i % this.weatherCells.length];
        const v = latLonToVec3(cell.lat, cell.lon, EARTH_R + 0.03);
        pos.set([v.x, v.y, v.z], i * 3);
        c.setHSL(0.55 - Math.min(0.45, cell.wind_kt / 180), 0.65, 0.55);
        col.set([c.r, c.g, c.b], i * 3);
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      g.setAttribute("color", new THREE.BufferAttribute(col, 3));
      this.windParticles = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.018, vertexColors: true, transparent: true, opacity: 0.7 }));
      this.windGroup.add(this.windParticles);
    }
  }

  private buildFieldLayer(layers: Layers) {
    const fieldOn = layers.pressure || layers.sst || layers.temperature || layers.humidity || layers.satellite || layers.clouds;
    if (!fieldOn || !this.weatherCells.length) return;
    const pos: number[] = [];
    const col: number[] = [];
    const color = new THREE.Color();
    this.weatherCells.forEach((cell, i) => {
      if (i % 2) return;
      const v = latLonToVec3(cell.lat, cell.lon, EARTH_R + 0.011);
      pos.push(v.x, v.y, v.z);
      if (layers.sst) color.setHSL(0.58 - (cell.sst_c - 24) / 18, 0.8, 0.45);
      else if (layers.pressure) color.setHSL(0.62, 0.55, THREE.MathUtils.clamp((cell.mslp_hpa - 960) / 70, 0.15, 0.7));
      else if (layers.temperature) color.setHSL(0.08 + (32 - cell.temp_c) / 80, 0.7, 0.5);
      else color.setHSL(0.55, 0.2, 0.25 + cell.rh / 220);
      col.push(color.r, color.g, color.b);
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    this.overlays.add(new THREE.Points(g, new THREE.PointsMaterial({ size: 0.034, vertexColors: true, transparent: true, opacity: 0.5 })));
  }

  tick() {
    const t = this.clock.getElapsedTime();
    if (this.autoRotate) this.offsetLon += 0.012;
    if (this.clouds) this.clouds.rotation.y = t * 0.004;
    if (this.hasPulse) {
      this.overlays.traverse((obj) => {
        if (obj.userData.pulse) obj.scale.setScalar(1 + Math.sin(t * 3) * 0.18);
      });
    }
    const camLat = THREE.MathUtils.clamp(this.focusLat + this.offsetLat, -70, 70);
    const camLon = this.focusLon + this.offsetLon;
    this.camera.position.copy(latLonToVec3(camLat, camLon, this.distance));
    this.camera.up.set(0, 1, 0);
    this.camera.lookAt(0, 0, 0);
    this.labels.visible = this.distance < 3.6;
    this.renderer.render(this.scene, this.camera);
  }
}
