import * as THREE from "three";

// Same Three.js/additive sprite approach as Brain's scene/glow.js and backdrop.js.
// All positions are decorative; health observations only affect dependency lights.
function glowTexture(sharp = false) {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const x = c.getContext("2d"),
    g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  for (const [stop, color] of sharp
    ? [
        [0, "#fff"],
        [0.07, "#fff"],
        [0.18, "#ffffffb0"],
        [0.44, "#ffffff26"],
        [1, "#ffffff00"],
      ]
    : [
        [0, "#fff"],
        [0.12, "#fff"],
        [0.3, "#ffffff99"],
        [1, "#ffffff00"],
      ])
    g.addColorStop(stop, color);
  x.fillStyle = g;
  x.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
function random(seed = 6831) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}
function hash(text) {
  let h = 2166136261;
  for (const c of text) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return h >>> 0;
}
function gaussian(rng) {
  return (
    Math.sqrt(-2 * Math.log(Math.max(0.0001, rng()))) *
    Math.cos(rng() * Math.PI * 2)
  );
}

export function createHealthGalaxy(
  canvas,
  {
    topics,
    colors,
    getNodes,
    getView,
    onSelect,
    isLive,
    getPulse,
    isReduced,
    onRendererStatus,
  },
) {
  let disposed = false,
    animationFrame = 0;
  const listeners = new AbortController();
  const listen = (type, callback, options = {}) =>
    canvas.addEventListener(type, callback, {
      ...options,
      signal: listeners.signal,
    });
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
    powerPreference: "low-power",
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.6));
  renderer.setClearColor("#030710");
  const scene = new THREE.Scene(),
    galaxy = new THREE.Group(),
    camera = new THREE.PerspectiveCamera(45, 1, 1, 1800);
  camera.position.set(0, 0, 430);
  scene.add(galaxy);
  const soft = glowTexture(),
    sharp = glowTexture(true),
    rng = random(),
    groups = Object.keys(topics),
    objects = new Map();
  const raycaster = new THREE.Raycaster(),
    pointer = new THREE.Vector2();
  let yaw = -0.1,
    pitch = 0.12,
    zoom = 1,
    drag = null,
    width = 0,
    height = 0,
    lost = false;
  function sprite(texture, color, opacity, size, parent = galaxy) {
    const s = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: texture,
        color,
        transparent: true,
        opacity,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    );
    s.scale.setScalar(size);
    parent.add(s);
    return s;
  }
  function cloud(count, background = false) {
    const positions = [],
      tints = [],
      sizes = [],
      phases = [],
      rates = [];
    for (let i = 0; i < count; i++) {
      const angle = rng() * Math.PI * 2,
        r = Math.pow(rng(), 0.65) * 155;
      positions.push(
        background ? (rng() - 0.5) * 1000 : Math.cos(angle) * r,
        background
          ? (rng() - 0.5) * 680
          : Math.sin(angle) * r * 0.54 + gaussian(rng) * 9,
        background
          ? -100 - rng() * 300
          : gaussian(rng) * (10 + (1 - r / 155) * 17),
      );
      const color = new THREE.Color(
        rng() < 0.22 ? "#f6d8b3" : rng() < 0.5 ? "#bac8ee" : "#7ca4d5",
      );
      tints.push(color.r, color.g, color.b);
      sizes.push(0.55 + Math.pow(rng(), 3) * 2.8);
      phases.push(rng() * Math.PI * 2);
      rates.push(0.45 + rng() * 1.1);
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3),
    );
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(tints, 3));
    geometry.setAttribute("aSize", new THREE.Float32BufferAttribute(sizes, 1));
    geometry.setAttribute(
      "aPhase",
      new THREE.Float32BufferAttribute(phases, 1),
    );
    geometry.setAttribute("aRate", new THREE.Float32BufferAttribute(rates, 1));
    const material = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uTexture: { value: soft },
        uOpacity: { value: background ? 0.85 : 0.92 },
        uSize: { value: background ? 2.1 : 2.6 },
        uPixelRatio: { value: renderer.getPixelRatio() },
      },
      vertexShader: `attribute vec3 color; attribute float aSize; attribute float aPhase; attribute float aRate;
        uniform float uTime; uniform float uSize; uniform float uPixelRatio; varying vec3 vColor; varying float vPulse;
        void main(){vec3 p=position; p+=vec3(sin(uTime*.11+aPhase)*.8,sin(uTime*.14+aPhase*1.7)*.6,sin(uTime*.09+aPhase)*1.1);
          vPulse=.72+.28*sin(uTime*aRate+aPhase); vColor=color;
          vec4 mv=modelViewMatrix*vec4(p,1.); gl_Position=projectionMatrix*mv;
          gl_PointSize=max(.75,uSize*aSize*(.90+vPulse*.18)*uPixelRatio*220./max(1.,-mv.z));}`,
      fragmentShader: `uniform sampler2D uTexture; uniform float uOpacity; varying vec3 vColor; varying float vPulse;
        void main(){vec4 glow=texture2D(uTexture,gl_PointCoord);gl_FragColor=vec4(vColor*glow.rgb,glow.a*uOpacity*(.6+.4*vPulse));
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    const points = new THREE.Points(geometry, material);
    (background ? scene : galaxy).add(points);
    return points;
  }
  const dust = cloud(4200),
    backgroundStars = cloud(1700, true);
  // Irregular diffuse clouds and depth, without drawn arms or repeated circular systems.
  for (let i = 0; i < 11; i++) {
    const cloud = sprite(
      soft,
      i % 3 === 0 ? "#bd8eb3" : i % 2 ? "#476b9b" : "#73629a",
      0.075,
      100 + rng() * 65,
    );
    cloud.position.set(
      (rng() - 0.5) * 210,
      (rng() - 0.5) * 95,
      -25 - rng() * 25,
    );
    cloud.scale.y *= 0.58 + rng() * 0.25;
  }
  const halo = sprite(soft, "#b5b6ed", 0.1, 100),
    core = sprite(soft, "#fff1d8", 0.54, 21);
  halo.scale.y = 70;
  core.scale.y = 16;
  const wave = new THREE.Mesh(
    new THREE.RingGeometry(0.98, 1, 96),
    new THREE.MeshBasicMaterial({
      color: "#b9d9ff",
      transparent: true,
      opacity: 0,
      depthWrite: false,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
    }),
  );
  galaxy.add(wave);
  // Each neuron has one continuous, camera-facing ribbon sampled along its 3D path.
  const trailMap = trailTexture(),
    trailSegments = 64,
    zAxis = new THREE.Vector3(0, 0, 1);
  const neurons = Array.from({ length: 4 }, (_, i) => {
    const color = groups[i % groups.length],
      head = sprite(sharp, topics[color].color, 1, 7),
      aura = sprite(soft, topics[color].color, 0.23, 12);
    const geometry = new THREE.BufferGeometry(),
      uv = [],
      indices = [];
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(
        new Float32Array((trailSegments + 1) * 6),
        3,
      ).setUsage(THREE.DynamicDrawUsage),
    );
    for (let k = 0; k <= trailSegments; k++) {
      const u = k / trailSegments;
      uv.push(u, 0, u, 1);
      if (k < trailSegments) {
        const v = k * 2;
        indices.push(v, v + 1, v + 2, v + 1, v + 3, v + 2);
      }
    }
    geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
    geometry.setIndex(indices);
    const plume = new THREE.Mesh(
      geometry,
      new THREE.MeshBasicMaterial({
        map: trailMap,
        color: topics[color].color,
        transparent: true,
        opacity: 1,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
      }),
    );
    plume.frustumCulled = false;
    galaxy.add(plume);
    return {
      head,
      aura,
      plume,
      samples: Array.from(
        { length: trailSegments + 1 },
        () => new THREE.Vector3(),
      ),
      r: 45 + rng() * 115,
      phase: rng() * Math.PI * 2,
      speed: (rng() < 0.5 ? -1 : 1) * (0.12 + rng() * 0.14),
      tilt: (i % 2 ? -1 : 1) * (0.65 + rng() * 0.6),
      orientation: rng() * Math.PI * 2,
      depth: 75 + rng() * 65,
      eccentricity: 0.4 + rng() * 0.25,
      wobble: 8 + rng() * 12,
    };
  });
  function neuronPosition(n, angle, target = new THREE.Vector3()) {
    const radius = n.r + Math.sin(angle * 3 + n.phase) * n.wobble;
    const x = Math.cos(angle) * radius,
      y = Math.sin(angle) * radius * n.eccentricity;
    // Each path crosses the full depth of the disk, with its own tilted plane.
    return target
      .set(
        x,
        y,
        Math.sin(angle + n.orientation) * n.depth +
          Math.sin(angle * 2 + n.phase) * 18,
      )
      .applyAxisAngle(zAxis, n.tilt);
  }
  const worldPosition = new THREE.Vector3();
  function depthVisibility(position) {
    worldPosition.copy(position).applyMatrix4(galaxy.matrixWorld);
    const near = THREE.MathUtils.clamp((worldPosition.z + 150) / 300, 0, 1);
    // Distant trails fade into the translucent dust; front passes stay crisp.
    const behindCore =
      worldPosition.z < 0
        ? Math.exp(-(worldPosition.x ** 2 + worldPosition.y ** 2) / 1800) * 0.5
        : 0;
    return (0.25 + near * 0.75) * (1 - behindCore);
  }
  // Soft billboard ribbons: luminous head, narrow white core and long tapering ion glow.
  function trailTexture() {
    const c = document.createElement("canvas");
    c.width = 256;
    c.height = 32;
    const x = c.getContext("2d"),
      im = x.createImageData(256, 32);
    for (let y = 0; y < 32; y++)
      for (let u = 0; u < 256; u++) {
        const f = u / 255,
          d = Math.abs(y - 15.5) / 15.5,
          spread = 0.04 + f * 0.48,
          alpha =
            Math.pow(f, 1.7) *
            Math.exp((-d * d) / (spread * spread)) *
            Math.min(1, (1 - f) * 35);
        const k = (y * 256 + u) * 4;
        im.data[k] = 175 + 80 * f;
        im.data[k + 1] = 205 + 50 * f;
        im.data[k + 2] = 255;
        im.data[k + 3] = Math.round(alpha * 210);
      }
    x.putImageData(im, 0, 0);
    return new THREE.CanvasTexture(c);
  }
  const meteors = Array.from({ length: 3 }, (_, i) => {
    const group = new THREE.Group();
    scene.add(group);
    const plume = new THREE.Mesh(
      new THREE.PlaneGeometry(1, 1),
      new THREE.MeshBasicMaterial({
        map: trailMap,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
      }),
    );
    group.add(plume);
    const head = sprite(sharp, "#e8f5ff", 1, 5, group),
      bloom = sprite(soft, "#9dcfff", 0.25, 10, group);
    return {
      group,
      plume,
      head,
      bloom,
      delay: i * 4.1,
      period: 12.5 + i * 2.2,
      duration: 1.7 + i * 0.25,
      x: -170 + rng() * 70,
      y: 85 - rng() * 160,
      slope: -0.28 - rng() * 0.25,
      length: 37 + rng() * 25,
    };
  });
  function syncNodes() {
    const nodes = getNodes(),
      ids = new Set(nodes.map((n) => n.id));
    for (const [id, obj] of objects)
      if (!ids.has(id)) {
        galaxy.remove(obj.light, obj.status);
        obj.light.material.dispose();
        obj.status.material.dispose();
        objects.delete(id);
      }
    for (const n of nodes) {
      let obj = objects.get(n.id);
      if (!obj) {
        const r = random(hash(n.id)),
          a = r() * Math.PI * 2,
          radius = 35 + Math.sqrt(r()) * 112;
        const light = sprite(sharp, topics[n.group]?.color || "#a5c6e7", 1, 8),
          status = sprite(soft, colors[n.status] || colors.unknown, 1, 2.5);
        light.position.set(
          Math.cos(a) * radius,
          Math.sin(a) * radius * 0.57,
          (r() - 0.5) * 42,
        );
        status.position.copy(light.position).add(new THREE.Vector3(3, 2, 2));
        light.userData.id = n.id;
        obj = {
          light,
          status,
          node: n,
          angle: a,
          radius,
          depth: light.position.z,
          baseSize: 5 + r() * 8.5,
          phase: r() * Math.PI * 2,
          pulseRate: 0.55 + r() * 1.2,
          driftSpeed: 0.006 + r() * 0.012,
        };
        objects.set(n.id, obj);
      }
      obj.node = n;
    }
  }
  function reset() {
    yaw = -0.1;
    pitch = 0.12;
    zoom = 1;
  }
  function resize() {
    const r = canvas.getBoundingClientRect();
    if (width !== r.width || height !== r.height) {
      width = r.width;
      height = r.height;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
  }
  listen("pointerdown", (e) => {
    drag = { x: e.clientX, y: e.clientY, distance: 0 };
    canvas.setPointerCapture(e.pointerId);
  });
  listen("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x,
      dy = e.clientY - drag.y;
    drag.distance += Math.abs(dx) + Math.abs(dy);
    yaw += dx * 0.005;
    pitch = Math.max(-1, Math.min(1, pitch + dy * 0.004));
    drag.x = e.clientX;
    drag.y = e.clientY;
  });
  listen("pointerup", (e) => {
    if (drag && drag.distance < 6) {
      const r = canvas.getBoundingClientRect(),
        view = getView();
      pointer.set(
        ((e.clientX - r.left) / r.width) * 2 - 1,
        (-(e.clientY - r.top) / r.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointer, camera);
      const eligible = [...objects.values()].filter(
        (o) =>
          (view.topic === "all" || view.topic === o.node.group) &&
          (!view.issuesOnly ||
            ["down", "degraded", "unknown"].includes(o.node.status)),
      );
      const chosen = raycaster.intersectObjects(
        eligible.map((o) => o.light),
      )[0];
      if (chosen) onSelect(chosen.object.userData.id);
    }
    drag = null;
  });
  listen("pointercancel", () => {
    drag = null;
  });
  listen(
    "wheel",
    (e) => {
      if (e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      zoom = Math.max(0.7, Math.min(1.8, zoom - e.deltaY * 0.001));
    },
    { passive: false },
  );

  listen("webglcontextlost", (e) => {
    e.preventDefault();
    lost = true;
    onRendererStatus("3D view paused · use Systems by Type");
  });
  listen("webglcontextrestored", () => {
    lost = false;
    onRendererStatus("");
  });
  const localCamera = new THREE.Vector3(),
    tangent = new THREE.Vector3(),
    toCamera = new THREE.Vector3(),
    side = new THREE.Vector3();
  let lastSync = -Infinity;
  function frame(t) {
    if (disposed) return;
    const reduced = isReduced();
    animationFrame = requestAnimationFrame(frame);
    if (document.hidden || lost) return;
    resize();
    const time = reduced ? 0 : t / 1000,
      view = getView(),
      beat = isLive() ? Math.max(0, 1 - (t - getPulse()) / 2500) : 0;
    if (t - lastSync > 350) {
      syncNodes();
      lastSync = t;
    }
    galaxy.rotation.set(pitch, yaw + (reduced ? 0 : time * 0.008), -0.1);
    camera.position.z = 430 / zoom;
    dust.material.uniforms.uTime.value = time;
    backgroundStars.material.uniforms.uTime.value = time;
    core.material.opacity = isLive() ? 0.48 + beat * 0.15 : 0.2;
    halo.scale.setScalar(
      95 + (reduced ? 0 : Math.sin(time * 0.9) * 4) + beat * 12,
    );
    halo.scale.y *= 0.64;
    wave.visible = !!beat && !reduced;
    wave.scale.set(15 + (1 - beat) * 160, (15 + (1 - beat) * 160) * 0.58, 1);
    wave.material.opacity = beat * 0.11;
    for (const [id, o] of objects) {
      const dim =
          (view.topic !== "all" && view.topic !== o.node.group) ||
          (view.issuesOnly &&
            !["degraded", "down", "unknown"].includes(o.node.status)),
        focus = id === view.selected;
      const pulse = 0.5 + 0.5 * Math.sin(time * o.pulseRate + o.phase),
        angle = o.angle + time * o.driftSpeed,
        radius =
          o.radius + (reduced ? 0 : Math.sin(time * 0.22 + o.phase) * 1.8);
      o.light.position.set(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius * 0.57,
        o.depth + (reduced ? 0 : Math.sin(time * 0.3 + o.phase) * 2.5),
      );
      o.status.position.copy(o.light.position).add(new THREE.Vector3(3, 2, 2));
      o.light.material.opacity = dim ? 0.1 : focus ? 1 : 0.68 + pulse * 0.25;
      o.light.scale.setScalar(
        o.baseSize * (focus ? 1.45 : 1) * (reduced ? 1 : 0.87 + pulse * 0.26),
      );
      o.status.material.color.set(colors[o.node.status] || colors.unknown);
      o.status.material.opacity = dim ? 0.1 : 1;
    }
    galaxy.updateMatrixWorld(true);
    localCamera.copy(camera.position);
    galaxy.worldToLocal(localCamera);
    for (const n of neurons) {
      const a = n.phase + time * n.speed;
      neuronPosition(n, a, n.head.position);
      n.aura.position.copy(n.head.position);
      const visibility = depthVisibility(n.head.position);
      n.head.material.opacity = visibility;
      n.aura.material.opacity = visibility * 0.23;
      n.plume.material.opacity = visibility;
      // Continuous path history: tail spacing is based on time, never straight chord branches.
      for (let k = 0; k <= trailSegments; k++)
        neuronPosition(
          n,
          a - (1 - k / trailSegments) * n.speed * 2.0,
          n.samples[k],
        );
      const data = n.plume.geometry.attributes.position;
      for (let k = 0; k <= trailSegments; k++) {
        const point = n.samples[k];
        tangent
          .subVectors(
            n.samples[Math.min(trailSegments, k + 1)],
            n.samples[Math.max(0, k - 1)],
          )
          .normalize();
        toCamera.subVectors(localCamera, point).normalize();
        side.crossVectors(tangent, toCamera).normalize().multiplyScalar(2.7);
        data.setXYZ(
          k * 2,
          point.x - side.x,
          point.y - side.y,
          point.z - side.z,
        );
        data.setXYZ(
          k * 2 + 1,
          point.x + side.x,
          point.y + side.y,
          point.z + side.z,
        );
      }
      data.needsUpdate = true;
    }
    for (const m of meteors) {
      const age = (time + m.delay) % m.period,
        progress = age / m.duration;
      m.group.visible = !reduced && progress < 1;
      if (m.group.visible) {
        const x = m.x + progress * 320,
          y = m.y + progress * 320 * m.slope,
          angle = Math.atan(m.slope),
          length = m.length * (0.65 + progress * 0.4),
          opacity = Math.min(1, progress * 10, (1 - progress) * 8);
        m.group.position.set(x, y, 100);
        m.group.rotation.z = angle;
        m.plume.scale.set(length, 7, 1);
        m.plume.position.x = -length * 0.5;
        m.plume.material.opacity = opacity;
        m.head.material.opacity = opacity;
        m.bloom.material.opacity = opacity * 0.3;
      }
    }
    renderer.render(scene, camera);
    canvas.dataset.renderer = "three-webgl";
    canvas.dataset.shootingStars = String(
      meteors.filter((m) => m.group.visible).length,
    );
  }
  animationFrame = requestAnimationFrame(frame);
  return {
    reset,
    dispose() {
      disposed = true;
      cancelAnimationFrame(animationFrame);
      listeners.abort();
      if (drag) {
        drag = null;
      }
      const geometries = new Set(),
        materials = new Set(),
        textures = new Set([soft, sharp, trailMap]);
      scene.traverse((object) => {
        if (object.geometry) geometries.add(object.geometry);
        const list = object.material
          ? Array.isArray(object.material)
            ? object.material
            : [object.material]
          : [];
        for (const material of list) {
          materials.add(material);
          if (material.map) textures.add(material.map);
        }
      });
      geometries.forEach((value) => value.dispose());
      materials.forEach((value) => value.dispose());
      textures.forEach((value) => value.dispose());
      renderer.dispose();
      renderer.forceContextLoss();
      delete canvas.dataset.renderer;
      delete canvas.dataset.shootingStars;
    },
  };
}
