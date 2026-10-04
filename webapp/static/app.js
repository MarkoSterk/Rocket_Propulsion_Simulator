"use strict";
const $ = (id) => document.getElementById(id);
const GRAIN_FIELDS = {
  circular: ["core_diameter_mm"],
  star: ["points", "star_inner_diameter_mm", "star_outer_diameter_mm"],
  cross: ["slots", "slot_width_mm", "slot_span_mm"],
  moon: ["core_diameter_mm", "offset_mm"],
  endburner: [],
};
let PROPS = {};

function showGrainFields() {
  const t = $("gtype").value;
  document.querySelectorAll("[data-g]").forEach((el) => {
    el.style.display = el.dataset.g.split(" ").includes(t) ? "" : "none";
  });
  updateGrainHint();
}

function updateGrainHint() {
  const t = $("gtype").value, faces = $("burning_faces").value, n = parseInt($("segments").value, 10) || 1;
  let h;
  if (t === "endburner") {
    h = "Solid cylinder without a canal, bonded to the case: only the nozzle-side face burns (like a fireworks rocket), " +
        "so it is always a single grain.";
  } else {
    h = "Every grain is bonded to the case, so its outer surface never burns.";
    if (faces === "none" && n > 1) h += ` With inhibited faces, ${n} segments behave exactly like one grain of length ${n}·L.`;
    if (faces !== "none") h += " Burning faces recede, so each segment gets shorter (by 2w when both faces burn).";
    if (t === "circular" && faces === "both") {
      const D = num("outer_diameter_mm"), d = num("core_diameter_mm");
      if (D > d && d > 0) h += ` Approximately neutral BATES segment for this canal: L ≈ (3D + d)/2 = ${fmt((3 * D + d) / 2, 0)} mm.`;
    }
  }
  $("grainhint").textContent = h;
}

function num(id) { return parseFloat($(id).value); }

function collect() {
  const t = $("gtype").value;
  const grain = { type: t, length_mm: num("length_mm"), outer_diameter_mm: num("outer_diameter_mm") };
  GRAIN_FIELDS[t].forEach((f) => { grain[f] = num(f); });
  if (t !== "endburner") {
    grain.segments = Math.max(1, parseInt($("segments").value, 10) || 1);
    grain.burning_faces = $("burning_faces").value;
    grain.segment_gap_mm = Math.max(0, num("segment_gap_mm") || 0);
  }
  return {
    propellant: $("propellant").value,
    compare_all: $("compare_all").checked,
    grain,
    nozzle: {
      throat_diameter_mm: num("throat_diameter_mm"), exit_diameter_mm: num("exit_diameter_mm"),
      half_angle_deg: num("half_angle_deg"), efficiency: num("efficiency"),
    },
    target_pressure_MPa: num("target_pressure_MPa"),
    cstar_efficiency: num("cstar_efficiency"),
    burn_rate_multiplier: num("burn_rate_multiplier"),
    free_length_mm: num("free_length_mm"),
    ambient_pressure_kPa: num("ambient_pressure_kPa"),
    burnout_spread_pct: num("burnout_spread_pct"),
  };
}

const BUSY = { t0: 0, timer: 0, f: 0 };

function busyShow(msg) {
  BUSY.t0 = performance.now(); BUSY.f = 0;
  $("busy").hidden = false; busyProgress(0, msg || "Starting…");
  clearInterval(BUSY.timer);
  BUSY.timer = setInterval(() => { $("busy_time").textContent = fmt((performance.now() - BUSY.t0) / 1000, 1) + " s"; }, 100);
}

function busyProgress(f, msg) {
  BUSY.f = Math.max(BUSY.f, f);
  $("busy_fill").style.width = (100 * BUSY.f).toFixed(1) + "%";
  $("busy_pct").textContent = Math.round(100 * BUSY.f) + " %";
  if (msg) $("busy_msg").textContent = msg;
}

function busyHide() { clearInterval(BUSY.timer); $("busy").hidden = true; }

async function streamPost(url, body, lo = 0, hi = 1) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok || !r.body) throw new Error(`request failed (${r.status})`);
  const reader = r.body.getReader(), dec = new TextDecoder();
  let buf = "", result = null;
  const handle = (line) => {
    if (!line.trim()) return;
    const m = JSON.parse(line);
    if (m.type === "progress") busyProgress(lo + (hi - lo) * m.f, m.msg);
    else if (m.type === "result") result = m.data;
    else if (m.type === "error") throw new Error(m.error);
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) { handle(buf.slice(0, i)); buf = buf.slice(i + 1); }
  }
  handle(buf + dec.decode());
  if (!result) throw new Error("the server closed the connection without a result");
  if (!result.ok) throw new Error(result.error || "request failed");
  return result;
}

function fmt(x, d = 1) { return Number(x).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }); }

function renderPropInfo() {
  const p = PROPS[$("propellant").value];
  if (!p) { $("propinfo").innerHTML = ""; return; }
  const rows = p.ranges.map((r) => `<tr><td>${r.p_min}–${r.p_max}</td><td>${r.a}</td><td>${r.n}</td></tr>`).join("");
  $("propinfo").innerHTML =
    `<p>${p.description || ""}</p>
     <p>ρ = ${p.density} kg/m³ · T<sub>c</sub> = ${p.T} K · M = ${p.M} g/mol · ${p.gamma_c === p.gamma_e ? `γ = ${p.gamma_c}` : `γ<sub>c</sub> = ${p.gamma_c} · γ<sub>e</sub> = ${p.gamma_e}`} · ideal c* = ${p.cstar} m/s</p>
     <table><thead><tr><th>p [MPa]</th><th>a [mm/s/MPa<sup>n</sup>]</th><th>n</th></tr></thead><tbody>${rows}</tbody></table>`;
}

async function loadProps(select) {
  const list = await (await fetch("/api/propellants")).json();
  PROPS = {};
  const sel = $("propellant");
  const cur = select || sel.value;
  sel.innerHTML = "";
  list.forEach((p) => {
    PROPS[p.name] = p;
    const o = document.createElement("option"); o.value = p.name; o.textContent = p.name; sel.appendChild(o);
  });
  if (cur && PROPS[cur]) sel.value = cur;
  renderPropInfo();
}

function kpi(label, value, unit) {
  return `<div class="kpi"><div class="kv">${value}<span>${unit}</span></div><div class="kl">${label}</div></div>`;
}

function renderResults(j) {
  const names = Object.keys(j.summary);
  const s = j.summary[names[0]];
  $("kpis").innerHTML = (names.length > 1 ? `<div class="kpi-title">${names[0]}</div>` : "") +
    kpi("peak pressure", fmt(s.peak_pressure_MPa, 2), " MPa") +
    kpi("peak thrust", fmt(s.peak_thrust_N, 0), " N") +
    kpi("average thrust", fmt(s.average_thrust_N, 0), " N") +
    kpi("total impulse", fmt(s.total_impulse_Ns, 0), " N s") +
    kpi("burn time (F ≥ 10 % of peak)", fmt(s.burn_time_s, 2), " s") +
    kpi("specific impulse", fmt(s.specific_impulse_s, 1), " s") +
    kpi("propellant mass", fmt(s.propellant_mass_kg, 3), " kg") +
    kpi("simulated motor class", s.motor_class, "");
  $("warnings").innerHTML = j.warnings.map((w) => `<p>⚠ ${w}</p>`).join("");
  $("p_pressure").innerHTML = j.plots.pressure;
  $("p_thrust").innerHTML = j.plots.thrust;
  $("p_kn").innerHTML = j.plots.kn;
  BB.desc = j.grain;
  setupBurnback(j.burnback);
  $("graindesc").textContent = `${j.grain} · expansion ratio ε = ${j.expansion_ratio} · chamber time constant τ = ${j.tau_ms} ms`;
  const cols = ["propellant_mass_kg", "peak_pressure_MPa", "peak_thrust_N", "average_thrust_N", "total_impulse_Ns",
                "burn_time_s", "specific_impulse_s", "initial_Kn", "peak_Kn", "motor_class"];
  $("table").innerHTML = `<table><thead><tr><th>propellant</th>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>` +
    names.map((n) => `<tr><td>${n}</td>${cols.map((c) => `<td>${j.summary[n][c]}</td>`).join("")}</tr>`).join("") + "</tbody></table>";
  $("downloads").innerHTML = names.map((n) => {
    const url = URL.createObjectURL(new Blob([j.csv[n]], { type: "text/csv" }));
    return `<a class="dl" href="${url}" download="rocket_propulsion_simulator_${n}_${$("gtype").value}.csv">Download ${n} time series (CSV)</a>`;
  }).join("");
}

const BB = { data: null, field: null, img: null, off: null, playing: false, raf: 0 };
const COL = { prop: [233, 196, 106], empty: [255, 255, 255], front: [214, 69, 15], init: [150, 148, 142] };
const CASE = "#8a8984", INKC = "#0b0b0b", INK2C = "#52514e", ACC = "#2a78d6", FRONT = "rgb(214,69,15)";

function hiDPI(cv) {
  if (!cv.dataset.bw) { cv.dataset.bw = cv.getAttribute("width"); cv.dataset.bh = cv.getAttribute("height"); }
  const r = window.devicePixelRatio || 1, w = +cv.dataset.bw, h = +cv.dataset.bh;
  if (cv.width !== Math.round(w * r)) { cv.width = Math.round(w * r); cv.height = Math.round(h * r); }
  const ctx = cv.getContext("2d"); ctx.setTransform(r, 0, 0, r, 0, 0);
  return { ctx, w, h };
}

function setupBurnback(d) {
  stopPlay();
  BB.data = d; BB.field = null;
  $("bb_prop").textContent = d ? `(${d.propellant})` : "";
  if (!d) return;
  $("bb_label_cs").textContent = d.kind === "end" ? "Aft face, seen from the nozzle (the burning surface)"
    : "Cross-section, seen from the nozzle (dashed: plane of the longitudinal section)";
  if (d.kind === "field") {
    const bin = atob(d.field), n = d.n, q = new Uint16Array(n * n);
    for (let i = 0; i < n * n; i++) q[i] = bin.charCodeAt(2 * i) | (bin.charCodeAt(2 * i + 1) << 8);
    BB.field = q;
    BB.off = document.createElement("canvas"); BB.off.width = n; BB.off.height = n;
    BB.img = BB.off.getContext("2d").createImageData(n, n);
  }
  const sl = $("bb_slider");
  sl.max = d.t.length - 1; sl.value = 0;
  drawBurnback(0);
}

function mix(a, b, f) { return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f]; }
function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }

function drawSection(ctx, W, H, d, w) {
  const R = d.R_mm, pad = 12, s = (Math.min(W, H) / 2 - pad) / R, cx = W / 2, cy = H / 2;
  ctx.clearRect(0, 0, W, H);
  if (d.kind === "end") {
    if (w < d.web_mm) {
      ctx.fillStyle = "rgb(233,196,106)"; ctx.beginPath(); ctx.arc(cx, cy, R * s, 0, 2 * Math.PI); ctx.fill();
      ctx.fillStyle = "rgba(214,69,15,.28)"; ctx.beginPath(); ctx.arc(cx, cy, R * s, 0, 2 * Math.PI); ctx.fill();
      ctx.fillStyle = INKC; ctx.font = "11px system-ui, sans-serif"; ctx.textAlign = "center";
      ctx.fillText("whole face burns", cx, cy);
    }
    ctx.strokeStyle = CASE; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.arc(cx, cy, R * s + 2, 0, 2 * Math.PI); ctx.stroke();
    return;
  }
  if (d.kind === "field") {
    const n = d.n, q = BB.field, px = BB.img.data, h = 2 * R / (n - 1), wq = w / d.scale_mm, hq = h / d.scale_mm;
    for (let r = 0; r < n; r++) {
      const src = (n - 1 - r) * n;
      for (let c = 0; c < n; c++) {
        const v = q[src + c], o = 4 * (r * n + c);
        if (v === 65535) { px[o + 3] = 0; continue; }
        let col;
        if (v === 0) {
          col = COL.empty;
        } else {
          col = mix(COL.empty, COL.prop, clamp01((v - wq) / hq + 0.5));
          if (v <= wq) col = mix(col, COL.init, 0.35 * clamp01(1.5 - v / hq));
          if (w < d.web_mm) col = mix(col, COL.front, clamp01(1.2 - Math.abs(v - wq) / hq));
        }
        px[o] = col[0]; px[o + 1] = col[1]; px[o + 2] = col[2]; px[o + 3] = 255;
      }
    }
    BB.off.getContext("2d").putImageData(BB.img, 0, 0);
    ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, R * s, 0, 2 * Math.PI); ctx.clip();
    ctx.imageSmoothingEnabled = true;
    const half = (R + h / 2) * s;
    ctx.drawImage(BB.off, cx - half, cy - half, 2 * half, 2 * half);
    ctx.restore();
  } else if (d.kind === "circle") {
    ctx.fillStyle = "rgb(233,196,106)"; ctx.beginPath(); ctx.arc(cx, cy, R * s, 0, 2 * Math.PI); ctx.fill();
    const r = Math.min(d.r0_mm + w, R);
    ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(cx, cy, r * s, 0, 2 * Math.PI); ctx.fill();
    ctx.strokeStyle = "rgba(150,148,142,.6)"; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.arc(cx, cy, d.r0_mm * s, 0, 2 * Math.PI); ctx.stroke(); ctx.setLineDash([]);
    if (r < R) { ctx.strokeStyle = FRONT; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx, cy, r * s, 0, 2 * Math.PI); ctx.stroke(); }
  }
  ctx.strokeStyle = CASE; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.arc(cx, cy, R * s + 2, 0, 2 * Math.PI); ctx.stroke();
  ctx.strokeStyle = "rgba(42,120,214,.75)"; ctx.lineWidth = 1.2; ctx.setLineDash([5, 4]);
  ctx.beginPath(); ctx.moveTo(cx, cy - R * s - 8); ctx.lineTo(cx, cy + R * s + 8); ctx.stroke(); ctx.setLineDash([]);
}

function radialDist(d, y) {
  if (d.kind === "circle") return Math.abs(y) - d.r0_mm;
  if (d.kind === "field") {
    const c = d.cut_mm, n = c.length, f = (y + d.R_mm) / (2 * d.R_mm) * (n - 1);
    const i = Math.max(0, Math.min(n - 2, Math.floor(f))), t = f - i;
    return c[i] * (1 - t) + c[i + 1] * t;
  }
  return Infinity;
}

function faceDist(d, zl) {
  const L = d.L_mm;
  if (d.faces === "aft") return L - zl;
  if (d.faces === "both") return Math.min(zl, L - zl);
  return Infinity;
}

const SIDE = { img: null, off: null, key: "" };

function sideLayout(d, W, Hmax = 240) {
  const R = d.R_mm, n = d.n_seg, L = d.L_mm, gap = d.gap_mm;
  const stack = n * L + (n - 1) * gap, Lc = Math.max(d.chamber_mm, stack);
  const rt = d.throat_mm / 2, re = Math.max(d.exit_mm / 2, rt);
  const lconv = Math.max(R - rt, 1), ldiv = (re - rt) / Math.tan(Math.max(d.half_angle_deg, 5) * Math.PI / 180);
  const padL = 14, padR = 10, top = 22, bot = 18;
  const s = Math.min((W - padL - padR) / (Lc + lconv + ldiv), (Hmax - top - bot) / (2 * R + 6));
  return { W, H: Math.round(2 * R * s + top + bot + 8), s, stack, Lc, rt, re, lconv, ldiv, padL, top };
}

function drawSide(cv, d, w) {
  if (!cv.dataset.bw) cv.dataset.bw = cv.getAttribute("width");
  const lay = sideLayout(d, +cv.dataset.bw);
  if (+cv.dataset.bh !== lay.H) { cv.dataset.bh = lay.H; cv.setAttribute("height", lay.H); cv.width = 0; }
  const { ctx } = hiDPI(cv);
  drawSideCtx(ctx, lay, d, w, window.devicePixelRatio || 1, SIDE);
}

function drawSideCtx(ctx, lay, d, w, dpr, cache) {
  const R = d.R_mm, n = d.n_seg, L = d.L_mm, gap = d.gap_mm, pitch = L + gap;
  const { W, H, s, stack, Lc, rt, re, lconv, ldiv } = lay;
  ctx.clearRect(0, 0, W, H);
  const x0 = lay.padL, top = lay.top, yc = top + 4 + R * s;
  const pw = Math.max(1, Math.round(stack * s * dpr)), ph = Math.max(1, Math.round(2 * R * s * dpr));
  const key = `${pw}x${ph}`;
  if (cache.key !== key) {
    cache.off = document.createElement("canvas"); cache.off.width = pw; cache.off.height = ph;
    cache.img = cache.off.getContext("2d").createImageData(pw, ph); cache.key = key;
  }
  const SIDEC = cache;
  const px = SIDEC.img.data, mmpp = 1 / (s * dpr), hf = 1.6 * mmpp, live = w < d.web_mm;
  const dr = new Float32Array(ph), dz = new Float32Array(pw), inSeg = new Uint8Array(pw);
  for (let r = 0; r < ph; r++) dr[r] = radialDist(d, R - (r + 0.5) * mmpp);
  for (let c = 0; c < pw; c++) {
    const z = (c + 0.5) * mmpp, i = Math.floor(z / pitch), zl = z - i * pitch;
    inSeg[c] = i < n && zl <= L ? 1 : 0;
    dz[c] = inSeg[c] ? faceDist(d, zl) : 0;
  }
  for (let r = 0; r < ph; r++) {
    for (let c = 0; c < pw; c++) {
      const o = 4 * (r * pw + c);
      let col;
      if (!inSeg[c] || dr[r] <= 0) {
        col = COL.empty;
      } else {
        const v = Math.min(dr[r], dz[c]);
        col = mix(COL.empty, COL.prop, clamp01((v - w) / mmpp + 0.5));
        if (live) col = mix(col, COL.front, clamp01(1.2 - Math.abs(v - w) / hf));
      }
      px[o] = col[0]; px[o + 1] = col[1]; px[o + 2] = col[2]; px[o + 3] = 255;
    }
  }
  SIDEC.off.getContext("2d").putImageData(SIDEC.img, 0, 0);
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(SIDEC.off, x0, yc - R * s, stack * s, 2 * R * s);
  ctx.strokeStyle = "rgba(60,60,60,.85)"; ctx.lineWidth = 1.6;
  for (let i = 0; i < n; i++) {
    const za = x0 + i * pitch * s, zb = za + L * s;
    const inh = d.faces === "none" ? [za, zb] : d.faces === "aft" ? [za] : [];
    for (const z of inh) {
      for (const sg of [-1, 1]) {
        const r0 = d.kind === "circle" ? d.r0_mm : 0;
        ctx.beginPath(); ctx.moveTo(z, yc + sg * r0 * s); ctx.lineTo(z, yc + sg * R * s); ctx.stroke();
      }
    }
  }
  const zc = x0 + Lc * s, zt = zc + lconv * s, ze = zt + ldiv * s;
  ctx.strokeStyle = CASE; ctx.lineWidth = 3; ctx.lineJoin = "round";
  for (const sg of [-1, 1]) {
    ctx.beginPath();
    ctx.moveTo(x0, yc); ctx.lineTo(x0, yc + sg * (R * s + 1.5));
    ctx.lineTo(zc, yc + sg * (R * s + 1.5)); ctx.lineTo(zt, yc + sg * rt * s); ctx.lineTo(ze, yc + sg * re * s);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(82,81,78,.45)"; ctx.lineWidth = 0.8; ctx.setLineDash([6, 3, 1, 3]);
  ctx.beginPath(); ctx.moveTo(x0 - 6, yc); ctx.lineTo(ze + 4, yc); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = INK2C; ctx.font = "10px system-ui, sans-serif"; ctx.textAlign = "center";
  if (n > 1) for (let i = 0; i < n; i++) ctx.fillText(String(i + 1), x0 + (i * pitch + L / 2) * s, top - 6);
  ctx.textAlign = "left"; ctx.fillText("head end", x0, H - 4);
  ctx.textAlign = "right"; ctx.fillText("nozzle", ze, H - 4);
}

function drawTrace(ctx, W, H, d, i) {
  const t = d.t, p = d.p_MPa, tmax = t[t.length - 1] || 1, pmax = Math.max(...p) * 1.08 || 1;
  const l = 30, r = 8, top = 8, b = 20, X = (x) => l + (W - l - r) * x / tmax, Y = (y) => top + (H - top - b) * (1 - y / pmax);
  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = "#dcdad3"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(l, top); ctx.lineTo(l, H - b); ctx.lineTo(W - r, H - b); ctx.stroke();
  ctx.fillStyle = INK2C; ctx.font = "10px system-ui, sans-serif"; ctx.textAlign = "right";
  ctx.fillText(fmt(pmax / 1.08, 1), l - 4, top + 8); ctx.fillText("0", l - 4, H - b);
  ctx.textAlign = "center"; ctx.fillText("t [s]", W / 2, H - 4);
  ctx.save(); ctx.translate(9, (H - b + top) / 2); ctx.rotate(-Math.PI / 2); ctx.fillText("p [MPa]", 0, 0); ctx.restore();
  ctx.textAlign = "right"; ctx.fillText(fmt(tmax, tmax < 10 ? 2 : 1), W - r, H - 4);
  ctx.strokeStyle = ACC; ctx.lineWidth = 1.6; ctx.beginPath();
  for (let k = 0; k < t.length; k++) (k ? ctx.lineTo : ctx.moveTo).call(ctx, X(t[k]), Y(p[k]));
  ctx.stroke();
  ctx.strokeStyle = FRONT; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(X(t[i]), top); ctx.lineTo(X(t[i]), H - b); ctx.stroke();
  ctx.fillStyle = FRONT; ctx.beginPath(); ctx.arc(X(t[i]), Y(p[i]), 3.5, 0, 2 * Math.PI); ctx.fill();
}

function drawBurnback(i) {
  const d = BB.data; if (!d) return;
  i = Math.max(0, Math.min(d.t.length - 1, i | 0));
  const w = d.w_mm[i];
  const a = hiDPI($("bb_canvas")); drawSection(a.ctx, a.w, a.h, d, w);
  drawSide($("bb_side"), d, w);
  const b = hiDPI($("bb_trace")); drawTrace(b.ctx, b.w, b.h, d, i);
  const burnt = Math.min(100, 100 * w / d.web_mm);
  $("bb_readout").innerHTML =
    `<span>t <b>${fmt(d.t[i], 3)}</b> s</span><span>w <b>${fmt(Math.min(w, d.web_mm), 2)}</b> mm</span><span>web <b>${fmt(burnt, 0)}</b> %</span>` +
    `<span>p <b>${fmt(d.p_MPa[i], 2)}</b> MPa</span><span>F <b>${fmt(d.F_N[i], 0)}</b> N</span><span>K<sub>n</sub> <b>${fmt(d.Kn[i], 0)}</b></span>` +
    (d.faces !== "none" ? `<span>L<sub>seg</sub> <b>${fmt(Math.max(d.L_mm - (d.faces === "both" ? 2 : 1) * Math.min(w, d.web_mm), 0), 1)}</b> mm</span>` : "");
}

function stopPlay() {
  BB.playing = false; cancelAnimationFrame(BB.raf);
  const b = $("bb_play"); if (b) { b.textContent = "▶"; b.setAttribute("aria-label", "Play"); }
}

function togglePlay() {
  const d = BB.data; if (!d) return;
  if (BB.playing) { stopPlay(); return; }
  const sl = $("bb_slider"), N = d.t.length - 1;
  if (+sl.value >= N) sl.value = 0;
  BB.playing = true; $("bb_play").textContent = "❚❚"; $("bb_play").setAttribute("aria-label", "Pause");
  const dur = 6000, t0 = performance.now(), i0 = +sl.value;
  const step = (now) => {
    if (!BB.playing) return;
    const i = Math.min(N, Math.round(i0 + (now - t0) / dur * N));
    sl.value = i; drawBurnback(i);
    if (i >= N) { stopPlay(); return; }
    BB.raf = requestAnimationFrame(step);
  };
  BB.raf = requestAnimationFrame(step);
}

const EXPORT_SIDE = { img: null, off: null, key: "" };

function frameIndexAt(d, T) {
  const t = d.t; let lo = 0, hi = t.length - 1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (t[m] <= T) lo = m; else hi = m - 1; }
  return lo;
}

function panel(w, h, scale, draw) {
  const c = document.createElement("canvas"); c.width = Math.round(w * scale); c.height = Math.round(h * scale);
  const ctx = c.getContext("2d"); ctx.setTransform(scale, 0, 0, scale, 0, 0); draw(ctx); return c;
}

function composeFrame(cv, d, i, scale) {
  const W = 960, pad = 16, csz = 250, w = d.w_mm[i];
  const lay = sideLayout(d, W - csz - 3 * pad, 260);
  const headH = 50, rowH = Math.max(csz, lay.H) + 18, traceW = 600, traceH = 110;
  const H = headH + rowH + 12 + traceH + 26;
  cv.width = Math.round(W * scale); cv.height = Math.round(H * scale);
  const ctx = cv.getContext("2d"); ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H);
  ctx.textAlign = "left"; ctx.fillStyle = INKC; ctx.font = "600 15px system-ui, sans-serif";
  ctx.fillText(`Grain burn-back · ${d.propellant}`, pad, 22);
  ctx.fillStyle = INK2C; ctx.font = "11px system-ui, sans-serif";
  let desc = BB.desc || ""; while (desc.length > 20 && ctx.measureText(desc).width > W - 2 * pad) desc = desc.slice(0, -2);
  ctx.fillText(desc + (desc !== (BB.desc || "") ? "…" : ""), pad, 40);
  const cs = panel(csz, csz, scale, (c) => drawSection(c, csz, csz, d, w));
  const yRow = headH + (rowH - 18 - csz) / 2;
  ctx.drawImage(cs, pad, yRow, csz, csz);
  const sd = panel(lay.W, lay.H, scale, (c) => drawSideCtx(c, lay, d, w, scale, EXPORT_SIDE));
  const xs = pad * 2 + csz, ys = headH + (rowH - 18 - lay.H) / 2;
  ctx.drawImage(sd, xs, ys, lay.W, lay.H);
  ctx.fillStyle = INK2C; ctx.font = "11px system-ui, sans-serif"; ctx.textAlign = "center";
  ctx.fillText(d.kind === "end" ? "aft face, seen from the nozzle" : "cross-section, seen from the nozzle", pad + csz / 2, headH + rowH - 4);
  ctx.fillText("longitudinal section through the axis", xs + lay.W / 2, headH + rowH - 4);
  const tr = panel(traceW, traceH, scale, (c) => drawTrace(c, traceW, traceH, d, i));
  const yT = headH + rowH + 12;
  ctx.drawImage(tr, pad, yT, traceW, traceH);
  const k = d.faces === "both" ? 2 : d.faces === "aft" ? 1 : 0;
  const rows = [["t", fmt(d.t[i], 3), "s"], ["w", fmt(Math.min(w, d.web_mm), 2), "mm"], ["p", fmt(d.p_MPa[i], 2), "MPa"],
                ["F", fmt(d.F_N[i], 0), "N"], ["Kn", fmt(d.Kn[i], 0), ""]];
  if (k) rows.push(["L seg", fmt(Math.max(d.L_mm - k * Math.min(w, d.web_mm), 0), 1), "mm"]);
  ctx.textAlign = "left";
  rows.forEach((r, j) => {
    const x = pad + traceW + 30 + (j % 2) * 150, y = yT + 22 + Math.floor(j / 2) * 26;
    ctx.fillStyle = INK2C; ctx.font = "12px system-ui, sans-serif"; ctx.fillText(r[0], x, y);
    ctx.fillStyle = INKC; ctx.font = "600 14px system-ui, sans-serif"; ctx.fillText(r[1], x + 42, y);
    const vw = ctx.measureText(r[1]).width;
    ctx.fillStyle = INK2C; ctx.font = "12px system-ui, sans-serif"; ctx.fillText(r[2], x + 42 + vw + 5, y);
  });
  ctx.fillStyle = "#9a9893"; ctx.font = "10px system-ui, sans-serif"; ctx.textAlign = "right";
  ctx.fillText("Rocket Propulsion Simulator", W - pad, H - 8);
}

function saveBlob(blob, name) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 30000);
}

function exportName(ext) {
  const d = BB.data, nseg = d.n_seg > 1 ? `_${d.n_seg}seg` : "";
  return `burnback_${d.propellant}_${$("gtype").value}${nseg}.${ext}`.replace(/[^A-Za-z0-9_.-]/g, "_");
}

function frameTimes(d) {
  const len = Math.min(Math.max(num("ex_len") || 6, 1), 60), fps = +$("ex_fps").value || 15;
  const n = Math.max(2, Math.round(len * fps)), tmax = d.t[d.t.length - 1];
  return { fps, idx: Array.from({ length: n }, (_, f) => frameIndexAt(d, tmax * f / (n - 1))) };
}

function exportBusy(on) { ["ex_png", "ex_gif", "ex_vid", "run", "size"].forEach((id) => { $(id).disabled = on; }); }

async function exportPNG() {
  const d = BB.data; if (!d) return;
  stopPlay();
  const i = +$("bb_slider").value, cv = document.createElement("canvas");
  composeFrame(cv, d, i, 2);
  cv.toBlob((b) => saveBlob(b, exportName("png").replace(".png", `_t${fmt(d.t[i], 3)}s.png`)), "image/png");
}

async function exportGIF() {
  const d = BB.data; if (!d) return;
  stopPlay(); exportBusy(true); busyShow("Rendering the frames…");
  try {
    const { fps, idx } = frameTimes(d), cv = document.createElement("canvas"), frames = [];
    for (let f = 0; f < idx.length; f++) {
      composeFrame(cv, d, idx[f], 1);
      frames.push(cv.toDataURL("image/png"));
      if (f % 5 === 0) { busyProgress(0.6 * f / idx.length, `Rendering frame ${f + 1} of ${idx.length}`); await new Promise((r) => setTimeout(r, 0)); }
    }
    busyProgress(0.65, "Building the GIF on the server…");
    const r = await fetch("/api/export_gif", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fps, frames, hold_last_ms: 1500 }) });
    if (!r.ok) { let m = `request failed (${r.status})`; try { m = (await r.json()).error || m; } catch (e) {  } throw new Error(m); }
    saveBlob(await r.blob(), exportName("gif"));
    $("exportmsg").textContent = `GIF saved (${idx.length} frames, ${fps} fps).`;
  } catch (e) {
    $("exportmsg").textContent = "Export failed: " + e.message;
  } finally { busyHide(); exportBusy(false); }
}

function videoType() {
  if (!window.MediaRecorder) return null;
  for (const t of ["video/mp4;codecs=avc1", "video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm", "video/mp4"])
    if (MediaRecorder.isTypeSupported(t)) return t;
  return null;
}

async function exportVideo() {
  const d = BB.data; if (!d) return;
  const type = videoType();
  if (!type) { $("exportmsg").textContent = "This browser cannot record video; use the GIF export."; return; }
  stopPlay(); exportBusy(true); busyShow("Recording the video (runs in real time)…");
  try {
    const { fps, idx } = frameTimes(d), cv = document.createElement("canvas");
    composeFrame(cv, d, idx[0], 1.5);
    const stream = cv.captureStream(fps), chunks = [];
    const rec = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 6e6 });
    rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    const done = new Promise((res) => { rec.onstop = res; });
    rec.start();
    const extra = Math.round(1.5 * fps);
    for (let f = 0; f < idx.length + extra; f++) {
      const t0 = performance.now();
      composeFrame(cv, d, idx[Math.min(f, idx.length - 1)], 1.5);
      busyProgress(f / (idx.length + extra), `Recording frame ${Math.min(f + 1, idx.length)} of ${idx.length}`);
      await new Promise((r) => setTimeout(r, Math.max(0, 1000 / fps - (performance.now() - t0))));
    }
    rec.stop(); await done;
    const ext = type.startsWith("video/mp4") ? "mp4" : "webm";
    saveBlob(new Blob(chunks, { type: type.split(";")[0] }), exportName(ext));
    $("exportmsg").textContent = `Video saved (${ext.toUpperCase()}, ${fps} fps).`;
  } catch (e) {
    $("exportmsg").textContent = "Export failed: " + e.message;
  } finally { busyHide(); exportBusy(false); }
}

async function simulate(lo = 0, hi = 1) {
  stopPlay();
  const j = await streamPost("/api/simulate", collect(), lo, hi);
  renderResults(j);
}

async function run(ev) {
  if (ev) ev.preventDefault();
  $("status").textContent = ""; $("run").disabled = true; $("size").disabled = true;
  busyShow("Starting the simulation…");
  try {
    await simulate();
  } catch (e) {
    $("status").textContent = "Error: " + e.message;
  } finally { busyHide(); $("run").disabled = false; $("size").disabled = false; }
}

async function sizeThroat() {
  $("status").textContent = ""; $("size").disabled = true; $("run").disabled = true;
  busyShow("Sizing the throat…");
  try {
    const j = await streamPost("/api/size_throat", collect(), 0, 0.8);
    $("throat_diameter_mm").value = j.throat_diameter_mm;
    const eps = Math.pow(num("exit_diameter_mm") / j.throat_diameter_mm, 2);
    busyProgress(0.8, `Throat set to ${j.throat_diameter_mm} mm, running the simulation…`);
    await simulate(0.8, 1);
    $("status").textContent = `Throat set to ${j.throat_diameter_mm} mm (ε = ${fmt(eps, 2)}).`;
  } catch (e) {
    $("status").textContent = "Error: " + e.message;
  } finally { busyHide(); $("size").disabled = false; $("run").disabled = false; }
}

async function upload() {
  const f = $("propfile").files[0];
  if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  const r = await fetch("/api/propellants", { method: "POST", body: fd });
  const j = await r.json();
  $("uploadmsg").textContent = j.ok ? `Added propellant ${j.name}.` : j.error;
  if (j.ok) await loadProps(j.name);
}

$("gtype").addEventListener("change", showGrainFields);
["burning_faces", "segments", "outer_diameter_mm", "core_diameter_mm"].forEach((id) => $(id).addEventListener("input", updateGrainHint));
$("propellant").addEventListener("change", renderPropInfo);
$("form").addEventListener("submit", run);
$("size").addEventListener("click", sizeThroat);
$("propfile").addEventListener("change", upload);
$("bb_slider").addEventListener("input", (e) => { stopPlay(); drawBurnback(+e.target.value); });
$("bb_play").addEventListener("click", togglePlay);
$("ex_png").addEventListener("click", exportPNG);
$("about_btn").addEventListener("click", () => $("about").showModal());
$("about").addEventListener("click", (e) => { if (e.target === $("about")) $("about").close(); });
$("ex_gif").addEventListener("click", exportGIF);
$("ex_vid").addEventListener("click", exportVideo);
if (!videoType()) $("ex_vid").title = "Video recording is not supported by this browser";
window.addEventListener("resize", () => BB.data && drawBurnback(+$("bb_slider").value));
showGrainFields();
loadProps().then(run);
