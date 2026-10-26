// Decorative projection only; backend state and confirmed fill events arrive as inputs.
export function createMarketUniverse(canvas, labels, assetSource, getState) {
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas unavailable");
  let width = 800,
    height = 345,
    zoom = 1,
    yaw = -0.18,
    pitch = 0.48,
    dragging = false,
    lastPointer,
    manualYaw = 0,
    manualPitch = 0;
  let disposed = false,
    animationFrame = 0,
    sceneTime = 0,
    lastFrame = performance.now();
  const listeners = new AbortController();
  const listen = (type, callback, options = {}) =>
    canvas.addEventListener(type, callback, {
      ...options,
      signal: listeners.signal,
    });
  const effects = [];
  let lastFill = 0;
  const TAU = Math.PI * 2;
  const randomSeed = (n) => {
    const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
  };
  const stars = Array.from({ length: 260 }, (_, i) => ({
    x: randomSeed(i + 1),
    y: randomSeed(i + 400),
    r: 0.25 + randomSeed(i + 820) * 0.8,
    a: 0.12 + randomSeed(i + 980) * 0.6,
  }));
  const particles = Array.from({ length: 1150 }, (_, i) => {
    const p = randomSeed(i + 2000) * TAU,
      r = Math.pow(randomSeed(i + 3300), 0.55) * 240;
    return {
      x: Math.cos(p) * r,
      y: (randomSeed(i + 4600) - 0.5) * 45,
      z: Math.sin(p) * r,
      size: 0.2 + randomSeed(i + 6100) * 0.8,
      alpha: 0.1 + randomSeed(i + 7800) * 0.5,
    };
  });
  function resize() {
    const rect = canvas.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  resize();
  function project(x, y, z) {
    const cy = Math.cos(yaw),
      sy = Math.sin(yaw),
      cp = Math.cos(pitch),
      sp = Math.sin(pitch);
    const rx = x * cy - z * sy,
      rz = x * sy + z * cy,
      ry = y * cp - rz * sp,
      zz = y * sp + rz * cp;
    const scale =
      (Math.min(width / 690, height / 330) * zoom * 720) / (720 + zz);
    return {
      x: width * 0.5 + rx * scale,
      y: height * 0.47 + ry * scale,
      z: zz,
      scale,
    };
  }
  function glow(x, y, r, color, alpha = 1) {
    if (r <= 0) return;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, color.replace("ALPHA", String(alpha)));
    g.addColorStop(0.2, color.replace("ALPHA", String(alpha * 0.35)));
    g.addColorStop(1, color.replace("ALPHA", "0"));
    ctx.fillStyle = g;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  function pointFor(a) {
    const angle =
      a.phase + sceneTime * 0.035 * (a.type === "crypto" ? 1.1 : 0.8);
    return project(
      Math.cos(angle) * a.radius,
      Math.sin(angle * 2) * 14,
      Math.sin(angle) * a.radius * 0.91,
    );
  }
  function renderScene(now) {
    if (disposed) return;
    const assets = typeof assetSource === "function" ? assetSource() : assetSource;
    const { selected, paused, motion, fill, fillAt } = getState();
    if (fill && fillAt !== lastFill) {
      if (
        (lastFill !== 0 || Date.now() - fillAt < 1000) &&
        assets.some((a) => a.symbol === fill.symbol)
      )
        effects.push({ ...fill, time: now, seed: fillAt % 100 });
      lastFill = fillAt;
    }
    const dt = Math.min((now - lastFrame) / 1000, 0.1);
    lastFrame = now;
    if (!paused && motion !== "reduced")
      sceneTime += dt * (motion === "calm" ? 0.25 : 1);
    yaw = -0.18 + manualYaw + sceneTime * 0.016;
    pitch = 0.48 + manualPitch;
    ctx.clearRect(0, 0, width, height);
    for (const s of stars) {
      const flicker =
        motion === "reduced"
          ? 1
          : 0.8 + Math.sin(sceneTime * 0.4 + s.x * 20) * 0.2;
      ctx.fillStyle = `rgba(158,195,214,${s.a * flicker})`;
      ctx.beginPath();
      ctx.arc(s.x * width, s.y * height, s.r, 0, TAU);
      ctx.fill();
    }
    const cx = width * 0.5,
      cy = height * 0.47;
    glow(cx - 60, cy, 180, "rgba(29,141,148,ALPHA)", 0.22);
    glow(cx + 70, cy - 4, 170, "rgba(98,61,158,ALPHA)", 0.22);
    for (let i = 0; i < 5; i++) {
      ctx.beginPath();
      for (let j = 0; j <= 160; j++) {
        const angle = (j / 160) * TAU,
          r = 95 + i * 39;
        const p = project(
          Math.cos(angle) * r,
          Math.sin(angle * 2 + i) * 8,
          Math.sin(angle) * r,
        );
        if (j) ctx.lineTo(p.x, p.y);
        else ctx.moveTo(p.x, p.y);
      }
      ctx.strokeStyle =
        i === 2 ? "rgba(96,168,169,.20)" : "rgba(96,135,163,.12)";
      ctx.lineWidth = 0.6;
      ctx.stroke();
    }
    for (const p of particles) {
      const a = sceneTime * 0.011,
        px = p.x * Math.cos(a) - p.z * Math.sin(a),
        pz = p.x * Math.sin(a) + p.z * Math.cos(a);
      const v = project(px, p.y, pz);
      ctx.fillStyle = `rgba(${pz > 0 ? "110,182,195" : "143,130,199"},${p.alpha * (pz > 0 ? 0.65 : 0.45)})`;
      ctx.fillRect(v.x, v.y, p.size * v.scale, p.size * v.scale);
    }
    // A quiet spherical core and orbital rings create depth without obscuring figures.
    glow(cx, cy, 74, "rgba(71,216,191,ALPHA)", 0.12);
    glow(cx, cy, 37, "rgba(112,231,207,ALPHA)", 0.17);
    for (let k = 0; k < 9; k++) {
      ctx.beginPath();
      const r = 32;
      for (let j = 0; j <= 80; j++) {
        const a = (j / 80) * TAU;
        const p = project(
          Math.cos(a) * r,
          Math.sin(a) * r * Math.cos(k * 0.35),
          Math.sin(a) * r * Math.sin(k * 0.35),
        );
        if (j) ctx.lineTo(p.x, p.y);
        else ctx.moveTo(p.x, p.y);
      }
      ctx.strokeStyle = `rgba(113,222,205,${k === 0 ? 0.19 : 0.045})`;
      ctx.lineWidth = 0.7;
      ctx.stroke();
    }
    ctx.setLineDash([2, 5]);
    ctx.beginPath();
    ctx.ellipse(cx, cy, 53 * zoom, 13 * zoom, -0.22, 0, TAU);
    ctx.strokeStyle = "rgba(134,225,210,.20)";
    ctx.stroke();
    ctx.setLineDash([]);
    const sizes = new Map(assets.map((a) => {
      const el = labels.get(a.symbol);
      return [a.symbol, { width: el?.offsetWidth || 0, height: el?.offsetHeight || 0 }];
    }));
    const sorted = assets
      .map((a) => ({ a, p: pointFor(a) }))
      .sort((x, y) => y.p.z - x.p.z);
    for (const { a, p } of sorted) {
      const isSelected = a.symbol === selected;
      glow(
        p.x,
        p.y,
        (isSelected ? 18 : 11) * p.scale,
        isSelected
          ? "rgba(170,245,190,ALPHA)"
          : a.type === "crypto"
            ? "rgba(169,133,225,ALPHA)"
            : "rgba(95,203,223,ALPHA)",
        isSelected ? 0.45 : 0.26,
      );
      ctx.beginPath();
      ctx.arc(p.x, p.y, (isSelected ? 3 : 2) * p.scale, 0, TAU);
      ctx.fillStyle = isSelected ? "#ceffcb" : a.color;
      ctx.fill();
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 9 * p.scale, 0, TAU);
        ctx.strokeStyle = "rgba(175,242,197,.32)";
        ctx.lineWidth = 0.7;
        ctx.stroke();
      }
      const el = labels.get(a.symbol);
      if (!el) continue;
      const size = sizes.get(a.symbol);
      el.style.left = `${Math.max(size.width / 2 + 8, Math.min(width - size.width / 2 - 8, p.x))}px`;
      el.style.top = `${Math.max(size.height / 2 + 45, Math.min(height - size.height / 2 - 12, p.y + 22 * p.scale))}px`;
      el.style.opacity = "1";
      el.style.zIndex = String(Math.round(720 - p.z));
    }
    for (let e = effects.length - 1; e >= 0; e--) {
      const effect = effects[e],
        age = (now - effect.time) / 1000;
      if (age > 6) {
        effects.splice(e, 1);
        continue;
      }
      if (motion === "reduced") continue;
      const a = assets.find((a) => a.symbol === effect.symbol);
      if (!a) continue;
      const p = pointFor(a);
      const f = 1 - age / 6;
      const power = motion === "calm" ? 0.35 : 1;
      if (effect.side === "buy") {
        for (let i = 0; i < 32; i++) {
          const angle = randomSeed(i + effect.seed) * TAU,
            spread =
              (15 + randomSeed(i + effect.seed + 70) * 80) * (age * 0.18 + 0.2);
          const x = p.x + Math.cos(angle) * spread,
            y = p.y + Math.sin(angle) * spread * 0.6;
          glow(
            x,
            y,
            (18 + randomSeed(i + 30) * 25) * power,
            "rgba(93,211,177,ALPHA)",
            f * 0.1 * power,
          );
        }
        ctx.beginPath();
        ctx.ellipse(
          p.x,
          p.y,
          (12 + age * 22) * power,
          (4 + age * 9) * power,
          -0.3,
          0,
          TAU,
        );
        ctx.strokeStyle = `rgba(165,242,192,${f * 0.45})`;
        ctx.lineWidth = 0.8;
        ctx.stroke();
      } else {
        glow(
          p.x,
          p.y,
          (28 + age * 25) * power,
          "rgba(207,159,248,ALPHA)",
          f * 0.45 * power,
        );
        const r = (12 + age * 45) * power;
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, r, r * 0.45, -0.4, 0, TAU);
        ctx.strokeStyle = `rgba(212,177,255,${f * 0.65})`;
        ctx.lineWidth = 1.3;
        ctx.stroke();
        for (let i = 0; i < 32; i++) {
          const angle = (i / 32) * TAU;
          ctx.beginPath();
          ctx.moveTo(
            p.x + Math.cos(angle) * r * 0.4,
            p.y + Math.sin(angle) * r * 0.4,
          );
          ctx.lineTo(p.x + Math.cos(angle) * r, p.y + Math.sin(angle) * r);
          ctx.strokeStyle = `rgba(197,173,241,${f * 0.25 * power})`;
          ctx.lineWidth = 0.6;
          ctx.stroke();
        }
      }
    }
    animationFrame = requestAnimationFrame(renderScene);
  }
  listen("pointerdown", (e) => {
    dragging = true;
    lastPointer = { x: e.clientX, y: e.clientY };
    canvas.setPointerCapture(e.pointerId);
  });
  listen("pointermove", (e) => {
    if (!dragging) return;
    manualYaw += (e.clientX - lastPointer.x) * 0.005;
    manualPitch = Math.max(
      -0.5,
      Math.min(0.6, manualPitch + (e.clientY - lastPointer.y) * 0.003),
    );
    lastPointer = { x: e.clientX, y: e.clientY };
  });
  listen("pointerup", () => (dragging = false));
  listen("pointercancel", () => (dragging = false));
  listen(
    "wheel",
    (e) => {
      if (e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      zoom = Math.max(0.65, Math.min(1.4, zoom - e.deltaY * 0.0007));
    },
    { passive: false },
  );
  animationFrame = requestAnimationFrame(renderScene);
  return {
    reset() {
      manualYaw = 0;
      manualPitch = 0;
      zoom = 1;
    },
    dispose() {
      disposed = true;
      cancelAnimationFrame(animationFrame);
      observer.disconnect();
      listeners.abort();
      effects.length = 0;
    },
  };
}
