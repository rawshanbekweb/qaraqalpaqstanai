"use client";

import {
  AnimatePresence,
  animate,
  motion,
  useMotionValue,
  useMotionValueEvent,
  useReducedMotion,
  useTransform,
} from "motion/react";
import { Crosshair, Layers, Minus, Plus, Locate, X } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { DISTRICTS, type District } from "@/data/districts";
import { RAIL_LEFT, railRight, stageOffsetX } from "@/lib/layout";
import { VOLUME_LEGEND, volumeColor } from "@/lib/scale";
import { useDashboard } from "@/lib/store";
import { shortUnit, useMapLayer, type MapDistrict } from "@/lib/stats";
import { cn, compact, trim } from "@/lib/utils";
import { DistrictTooltip } from "@/components/map/DistrictTooltip";

/*
 * Manba viewBox (0 0 919 659) tumanlarning chap va o'ng tomonida ~140
 * birlikdan bo'sh joy qoldiradi. Sahna butun ekranni egallagani uchun bu
 * bo'shliq xaritani keraksiz kichraytiradi — shuning uchun viewBox
 * tumanlarning haqiqiy chegarasidan hisoblanadi. Ma'lumot qayta
 * generatsiya qilinsa ham o'zi moslashadi.
 */
const PAD = 12;
const STAGE = (() => {
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (const d of DISTRICTS) {
    x0 = Math.min(x0, d.bbox[0]);
    y0 = Math.min(y0, d.bbox[1]);
    x1 = Math.max(x1, d.bbox[2]);
    y1 = Math.max(y1, d.bbox[3]);
  }
  return { x: x0 - PAD, y: y0 - PAD, w: x1 - x0 + PAD * 2, h: y1 - y0 + PAD * 2 };
})();

const STAGE_VIEWBOX = `${STAGE.x} ${STAGE.y} ${STAGE.w} ${STAGE.h}`;
const VB_W = STAGE.w;
const VB_H = STAGE.h;
const CENTER_X = STAGE.x + VB_W / 2;
const CENTER_Y = STAGE.y + VB_H / 2;

const MIN_SCALE = 0.55;
const MAX_SCALE = 9;
/** Kamera yuguradigan maydon — xarita ekrandan butunlay chiqib ketmasligi uchun */
const PAN_LIMIT = VB_W * 0.85;

const SPRING = { type: "spring", stiffness: 120, damping: 24, mass: 0.9 } as const;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/**
 * Tumanni sahna markaziga olib chiqadigan kamera holati.
 *
 * Masshtab viewBox MARKAZI (C) atrofida qo'llanadi, ya'ni p ↦ C + s·(p−C) + t.
 * Tuman markazi m ekran markaziga tushishi uchun t = s·(C − m).
 */
function focusCamera(d: District | null, zoomBias = 1.9) {
  if (!d) return { x: 0, y: 0, scale: 1 };
  const [x0, y0, x1, y1] = d.bbox;
  const w = Math.max(x1 - x0, 1);
  const h = Math.max(y1 - y0, 1);
  const scale = clamp(Math.min(VB_W / (w * zoomBias), VB_H / (h * zoomBias)), 1.15, 3.6);
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  return { x: scale * (CENTER_X - cx), y: scale * (CENTER_Y - cy), scale };
}

export function KarakalpakstanMap() {
  const {
    moduleId,
    year,
    hoveredDistrict,
    selectedDistrict,
    highlighted,
    focusMode,
    setHovered,
    selectDistrict,
  } = useDashboard();

  const wrapRef = useRef<HTMLDivElement>(null);
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [showLabels, setShowLabels] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [isWide, setIsWide] = useState(false);
  const reduce = useReducedMotion();

  // ── Kamera (motion qiymatlari — surish paytida React qayta chizilmaydi) ──
  const camX = useMotionValue(0);
  const camY = useMotionValue(0);
  const camScale = useMotionValue(1);

  /** Yorliqlar qarori uchun kifoya qiladigan "qo'pol" masshtab nusxasi. */
  const [scaleTick, setScaleTick] = useState(1);
  useMotionValueEvent(camScale, "change", (s) => {
    setScaleTick((prev) => (Math.abs(s - prev) / prev > 0.04 ? s : prev));
  });

  // Chiziqlar va yozuvlar ekranda bir xil qalinlikda qolishi uchun teskari masshtab
  const invScale = useTransform(camScale, (s) => 1 / s);
  const labelSize = useTransform(camScale, (s) => 11 / s);
  const labelStroke = useTransform(camScale, (s) => 2.4 / s);

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      setSize({ w: e.contentRect.width, h: e.contentRect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const sync = () => setIsWide(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  /** Bir viewBox birligi necha ekran pikseliga teng (preserveAspectRatio=meet). */
  const renderScale = useMemo(() => {
    if (!size.w || !size.h) return 1;
    return Math.min(size.w / VB_W, size.h / VB_H);
  }, [size]);

  const { data: layer } = useMapLayer(moduleId, year || null);
  const cells = useMemo(() => {
    const out: Record<string, MapDistrict> = {};
    for (const d of layer?.districts ?? []) out[d.district_id] = d;
    return out;
  }, [layer]);

  const selected = useMemo(
    () => DISTRICTS.find((d) => d.id === selectedDistrict) ?? null,
    [selectedDistrict],
  );
  const highlightSet = useMemo(() => new Set(highlighted), [highlighted]);

  // ── Kamerani tanlov/fokusga moslash ──
  useEffect(() => {
    // Chuqur fokusda kamera kuchliroq yaqinlashadi va ochiq maydonga tekislanadi
    const cam = focusCamera(selected, focusMode ? 1.45 : 1.9);
    const shiftPx = isWide ? stageOffsetX(size.w, focusMode) : 0;
    const shiftVb = renderScale ? shiftPx / renderScale : 0;

    const opts = reduce ? { duration: 0 } : SPRING;
    const controls = [
      animate(camX, cam.x + shiftVb * cam.scale, opts),
      animate(camY, cam.y, opts),
      animate(camScale, cam.scale, opts),
    ];
    return () => controls.forEach((c) => c.stop());
  }, [selected, focusMode, isWide, size.w, renderScale, reduce, camX, camY, camScale]);

  // ── Erkin surish ──
  const dragRef = useRef<{ id: number; x: number; y: number; moved: boolean } | null>(null);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return;
    dragRef.current = { id: e.pointerId, x: e.clientX, y: e.clientY, moved: false };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }, []);

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      const r = wrapRef.current?.getBoundingClientRect();
      if (r) setPointer({ x: e.clientX - r.left, y: e.clientY - r.top });

      const d = dragRef.current;
      if (!d || d.id !== e.pointerId) return;

      const dx = e.clientX - d.x;
      const dy = e.clientY - d.y;
      if (!d.moved && Math.hypot(dx, dy) < 4) return;

      if (!d.moved) {
        d.moved = true;
        setDragging(true);
      }
      d.x = e.clientX;
      d.y = e.clientY;

      const k = renderScale || 1;
      camX.set(clamp(camX.get() + dx / k, -PAN_LIMIT, PAN_LIMIT));
      camY.set(clamp(camY.get() + dy / k, -PAN_LIMIT, PAN_LIMIT));
    },
    [renderScale, camX, camY],
  );

  const endDrag = useCallback((e: React.PointerEvent) => {
    const d = dragRef.current;
    dragRef.current = null;
    setDragging(false);
    if (d?.moved) {
      // Surishdan keyingi "klik"ni bostiramiz
      e.stopPropagation();
    }
  }, []);

  /** Ko'rsatkich ostidagi nuqtani joyida qoldirib masshtablash. */
  const zoomAt = useCallback(
    (factor: number, px: number, py: number) => {
      const k = renderScale || 1;
      const s = camScale.get();
      const next = clamp(s * factor, MIN_SCALE, MAX_SCALE);
      if (next === s) return;

      // Kursorning sahna markazidan viewBox birligidagi siljishi
      const qx = (px - size.w / 2) / k;
      const qy = (py - size.h / 2) / k;

      camX.set(clamp(qx - (next / s) * (qx - camX.get()), -PAN_LIMIT, PAN_LIMIT));
      camY.set(clamp(qy - (next / s) * (qy - camY.get()), -PAN_LIMIT, PAN_LIMIT));
      camScale.set(next);
    },
    [renderScale, size, camX, camY, camScale],
  );

  const onWheel = useCallback(
    (e: React.WheelEvent) => {
      const r = wrapRef.current?.getBoundingClientRect();
      if (!r) return;
      zoomAt(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX - r.left, e.clientY - r.top);
    },
    [zoomAt],
  );

  const resetCamera = useCallback(() => {
    selectDistrict(null);
    const opts = reduce ? { duration: 0 } : SPRING;
    animate(camX, 0, opts);
    animate(camY, 0, opts);
    animate(camScale, 1, opts);
  }, [selectDistrict, reduce, camX, camY, camScale]);

  // Suzuvchi boshqaruvlar panellar orasida qolishi uchun
  const chrome = isWide
    ? { left: RAIL_LEFT + 20, right: railRight(focusMode) + 20 }
    : { left: 12, right: 12 };

  return (
    <div
      ref={wrapRef}
      data-dragging={dragging}
      className="map-stage absolute inset-0 overflow-hidden"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onWheel={onWheel}
      onMouseLeave={() => setHovered(null)}
    >
      {/* Fon halqalari */}
      <div className="pointer-events-none absolute inset-0 grid place-items-center opacity-[0.1]">
        {[0.5, 0.72, 0.95].map((s, i) => (
          <motion.div
            key={i}
            className="absolute aspect-square rounded-full border border-cyan/40"
            style={{ width: `${s * 68}%` }}
            animate={reduce ? {} : { rotate: 360 }}
            transition={{ duration: 90 + i * 40, repeat: Infinity, ease: "linear" }}
          />
        ))}
      </div>

      <svg
        viewBox={STAGE_VIEWBOX}
        className="absolute inset-0 size-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Qaraqalpaqstan Respublikası rayonları kartası"
      >
        <defs>
          <filter id="district-lift" x="-25%" y="-25%" width="150%" height="150%">
            <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#04060f" floodOpacity="0.85" />
          </filter>
          <filter id="edge-halo" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="2.5" />
          </filter>
          {/* Chegaralarning yuqori qismi yorug', pastki qismi qorong'i —
              tumanlar bir-birining ustiga qalqib turgandek ko'rinadi. */}
          <linearGradient id="edge-bevel" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#dbeafe" stopOpacity="0.85" />
            <stop offset="45%" stopColor="#7dd3fc" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#0b1024" stopOpacity="0.55" />
          </linearGradient>
        </defs>

        {/*
          Kamera. `transformBox: view-box` MAJBURIY: motion SVG elementlariga
          o'zicha `fill-box` qo'yadi, u holda transform-origin guruhning o'z
          bbox markaziga ko'chib, yuqoridagi hisob-kitob buziladi.
        */}
        <motion.g
          style={{
            x: camX,
            y: camY,
            scale: camScale,
            transformBox: "view-box",
            originX: 0.5,
            originY: 0.5,
          }}
        >
          {/* 1-qatlam — to'ldirish */}
          {DISTRICTS.map((d, i) => {
            const cell = cells[d.id];
            const isHover = hoveredDistrict === d.id;
            const isSelected = selectedDistrict === d.id;
            const isHighlighted = highlightSet.has(d.id);
            const off =
              (selectedDistrict && !isSelected) ||
              (highlightSet.size > 0 && !isHighlighted && !isHover && !isSelected);

            return (
              <motion.path
                key={d.id}
                d={d.d}
                className="district-path"
                tabIndex={0}
                role="button"
                aria-label={
                  cell?.value !== null && cell?.value !== undefined
                    ? `${d.name}: ${trim(cell.value)} ${shortUnit(layer?.unit ?? "")}`
                    : `${d.name}: maǵlıwmat joq`
                }
                fill={volumeColor(cell?.intensity, isHover || isSelected ? 0.95 : off ? 0.2 : 0.72)}
                // Chuqur fokusda e'tibordan tashqaridagilar deyarli so'nadi
                opacity={focusMode && off ? 0.3 : 1}
                filter={isHover || isSelected ? "url(#district-lift)" : undefined}
                initial={{ opacity: 0 }}
                animate={{ opacity: focusMode && off ? 0.3 : 1 }}
                transition={{
                  delay: reduce ? 0 : Math.min(0.03 * i, 0.4),
                  duration: 0.5,
                  ease: [0.22, 1, 0.36, 1],
                }}
                onMouseEnter={() => setHovered(d.id)}
                onFocus={() => setHovered(d.id)}
                onClick={() => {
                  if (dragRef.current?.moved) return;
                  selectDistrict(isSelected ? null : d.id);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    selectDistrict(isSelected ? null : d.id);
                  }
                }}
              />
            );
          })}

          {/* 2-qatlam — chegaralar. Alohida chiziladi, aks holda qo'shni
              tumanning to'ldirishi konturning yarmini yeb qo'yadi. */}
          <g>
            {DISTRICTS.map((d) => {
              const isActive = hoveredDistrict === d.id || selectedDistrict === d.id;
              const isHighlighted = highlightSet.has(d.id);
              return (
                <g key={`edge-${d.id}`}>
                  {/* yumshoq nur */}
                  <path
                    d={d.d}
                    className="district-edge"
                    stroke={isActive || isHighlighted ? "#7de2e7" : "#38bdf8"}
                    strokeWidth={isActive || isHighlighted ? 5 : 2.5}
                    opacity={isActive ? 0.55 : isHighlighted ? 0.4 : 0.12}
                    filter="url(#edge-halo)"
                  />
                  {/* qirrali kontur */}
                  <path
                    d={d.d}
                    className="district-edge"
                    stroke="url(#edge-bevel)"
                    strokeWidth={isActive ? 1.8 : 1.1}
                    strokeLinejoin="round"
                    opacity={isActive ? 1 : 0.75}
                  />
                </g>
              );
            })}
          </g>

          {/* 3-qatlam — tanlangan tuman atrofida yuguruvchi punktir */}
          {selected && (
            <path
              key={`march-${selected.id}`}
              d={selected.d}
              className="district-marching"
              stroke="#eef2ff"
              strokeWidth={1.4}
              opacity={0.9}
            />
          )}

          {/* Yoritilgan tumanlarda puls markerlari */}
          {DISTRICTS.filter((d) => highlightSet.has(d.id)).map((d) => {
            const accent = volumeColor(cells[d.id]?.intensity ?? 1);
            return (
              <g key={`pulse-${d.id}`} pointerEvents="none">
                <motion.circle
                  cx={d.labelX}
                  cy={d.labelY}
                  r={5}
                  fill="none"
                  stroke={accent}
                  style={{ strokeWidth: invScale }}
                  initial={{ scale: 0.5, opacity: 0.9 }}
                  animate={{ scale: [0.5, 3.2], opacity: [0.9, 0] }}
                  transition={{ duration: 2.2, repeat: Infinity, ease: "easeOut" }}
                />
                <motion.circle
                  cx={d.labelX}
                  cy={d.labelY}
                  r={2.6}
                  fill={accent}
                  style={{ scale: invScale, transformBox: "fill-box", transformOrigin: "center" }}
                />
              </g>
            );
          })}

          {/* Tuman nomlari — kichik tumanlarda ustma-ust tushmasligi uchun
              faqat yetarli joy bo'lganda chiziladi. */}
          {showLabels &&
            DISTRICTS.map((d) => {
              const isActive = hoveredDistrict === d.id || selectedDistrict === d.id;
              const off = selectedDistrict && selectedDistrict !== d.id;

              const FS = 11;
              const boxW = (d.bbox[2] - d.bbox[0]) * scaleTick;
              const boxH = (d.bbox[3] - d.bbox[1]) * scaleTick;
              const fits = boxW >= d.name.length * FS * 0.56 && boxH >= FS * 1.5;
              if (!fits && !isActive) return null;

              return (
                <motion.text
                  key={`label-${d.id}`}
                  x={d.labelX}
                  y={d.labelY}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  pointerEvents="none"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: off ? (focusMode ? 0.12 : 0.24) : isActive ? 1 : 0.82 }}
                  transition={{ duration: 0.35 }}
                  style={{
                    fontSize: labelSize,
                    strokeWidth: labelStroke,
                    fontWeight: isActive ? 800 : 600,
                    fill: "#eef2ff",
                    paintOrder: "stroke",
                    stroke: "rgb(4 6 15 / 0.9)",
                    letterSpacing: "0.01em",
                  }}
                >
                  {d.name}
                </motion.text>
              );
            })}
        </motion.g>
      </svg>

      {/* Radar skaner chizig'i */}
      {!reduce && (
        <motion.div
          className="pointer-events-none absolute inset-x-0 h-24 opacity-20"
          style={{
            background: "linear-gradient(180deg, transparent, rgb(34 211 238 / 0.18), transparent)",
          }}
          animate={{ top: ["-10%", "105%"] }}
          transition={{ duration: 9, repeat: Infinity, ease: "linear", repeatDelay: 4 }}
        />
      )}

      {/* Chuqur fokusda chekkalarni qoraytiruvchi vinyetka */}
      <AnimatePresence>
        {focusMode && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse 55% 55% at 42% 50%, transparent 30%, rgb(4 6 15 / 0.72) 100%)",
            }}
          />
        )}
      </AnimatePresence>

      <DistrictTooltip
        districtId={
          !dragging && hoveredDistrict && hoveredDistrict !== selectedDistrict
            ? hoveredDistrict
            : null
        }
        x={pointer.x}
        y={pointer.y}
        year={year}
        minX={isWide ? RAIL_LEFT : 0}
        maxX={isWide ? size.w - railRight(focusMode) : size.w}
      />

      {/* ── Suzuvchi xarita boshqaruvlari ── */}
      <motion.div
        className="overlay-pass pointer-events-none absolute bottom-0 z-20"
        style={{ top: "var(--head-h, 112px)" }}
        animate={{ left: chrome.left, right: chrome.right }}
        transition={SPRING}
      >
        {/* Sarlavha */}
        <div className="glass-chip absolute top-3 left-1/2 flex max-w-[min(92%,520px)] -translate-x-1/2 items-center gap-2.5 rounded-full px-4 py-2">
          <span className="size-1.5 shrink-0 animate-pulse rounded-full bg-cyan" />
          <span className="truncate text-[12.5px] font-bold tracking-tight text-ink">
            Qaraqalpaqstan Respublikası
          </span>
          <span className="truncate text-[10.5px] text-ink-3">
            {layer ? layer.indicator.module_name : "…"} · {year}
            {/* Yil tugamagan bo'lsa qiymat qay davrga tegishli ekani yozilmasa,
                joriy yil o'tgan yildan past ko'rinib chalg'itadi */}
            {layer?.partial ? ` (${layer.period_caption})` : ""}
          </span>
        </div>

        {/* Masshtab boshqaruvlari */}
        <div className="glass-chip absolute top-1/2 right-2 flex -translate-y-1/2 flex-col gap-1 rounded-2xl p-1.5">
          <MapBtn label="Jaqınlastırıw" onClick={() => zoomAt(1.25, size.w / 2, size.h / 2)}>
            <Plus size={15} />
          </MapBtn>
          <MapBtn label="Uzaqlastırıw" onClick={() => zoomAt(1 / 1.25, size.w / 2, size.h / 2)}>
            <Minus size={15} />
          </MapBtn>
          <MapBtn label="Dáslepki kórinis" onClick={resetCamera}>
            <Locate size={15} />
          </MapBtn>
          <MapBtn
            label="Atamalar"
            active={showLabels}
            onClick={() => setShowLabels((v) => !v)}
          >
            <Layers size={15} />
          </MapBtn>
        </div>

        {/* Legenda */}
        <div className="glass-chip absolute bottom-3 left-1/2 flex max-w-[min(94%,560px)] -translate-x-1/2 items-center gap-3 rounded-full px-4 py-2">
          <Crosshair size={12} className="shrink-0 text-ink-3" />
          <span className="shrink-0 text-[9.5px] font-semibold tracking-wider text-ink-3 uppercase">
            Kólemi{layer ? `, ${shortUnit(layer.unit)}` : ""}
          </span>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {VOLUME_LEGEND.map((s) => (
              <span key={s.label} className="inline-flex items-center gap-1.5">
                <span
                  className="size-2.5 rounded-[3px] ring-1 ring-void/70"
                  style={{ background: s.color }}
                />
                {/* Rang yolg'iz ma'no tashimasligi uchun har bosqichda
                    o'sha bosqichga to'g'ri keladigan qiymat yoziladi */}
                <span className="tnum text-[10.5px] text-ink-2">
                  {layer ? compact(layer.max * s.t) : s.label}
                </span>
              </span>
            ))}
          </div>
        </div>

        {/*
          Tanlangan tuman kartochkasi. Chuqur fokusda ko'rsatilmaydi: o'ng
          panel allaqachon shu ma'lumotni kengroq beradi, kartochka esa
          torayib qolgan bo'shliqda legendani to'sib qo'yardi.
        */}
        <AnimatePresence>
          {selected && !focusMode && (
            <SelectedCard district={selected} onClose={() => selectDistrict(null)} />
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

function MapBtn({
  children,
  label,
  active,
  onClick,
}: {
  children: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      aria-label={label}
      className={cn(
        "grid size-8 place-items-center rounded-xl transition",
        active
          ? "bg-cyan/15 text-cyan ring-1 ring-cyan/40"
          : "text-ink-3 hover:bg-raised/50 hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

function SelectedCard({ district, onClose }: { district: District; onClose: () => void }) {
  const { year, moduleId } = useDashboard();
  const { data: layer } = useMapLayer(moduleId, year || null);
  const cell = layer?.districts.find((d) => d.district_id === district.id);

  return (
    <motion.div
      initial={{ opacity: 0, y: 14, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 10, scale: 0.97 }}
      transition={{ type: "spring", stiffness: 320, damping: 30 }}
      className="glass-chip absolute bottom-16 left-2 w-56 overflow-hidden rounded-2xl"
    >
      <div className="flex items-start gap-2 px-3.5 py-3">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-bold text-ink">{district.name}</div>
          <div className="text-[10.5px] text-ink-3">
            {district.center} · {trim(district.areaKm2, 0)} km²
          </div>
        </div>
        <button
          onClick={onClose}
          className="grid size-6 shrink-0 place-items-center rounded-md text-ink-3 transition hover:bg-raised/60 hover:text-ink"
        >
          <X size={13} />
        </button>
      </div>
      <div className="flex items-end justify-between border-t border-hairline/60 px-3.5 py-2.5">
        <div className="min-w-0">
          <div className="text-[10px] tracking-wider text-ink-3 uppercase">
            {layer?.indicator.module_name ?? "Kólemi"}
          </div>
          <div className="truncate text-[10px] text-ink-3">
            {cell?.rank ? `${cell.rank}-orın · ` : ""}
            {cell?.share !== null && cell?.share !== undefined ? `${trim(cell.share)}%` : "—"}
          </div>
        </div>
        <span
          className="tnum shrink-0 text-2xl font-bold"
          style={{ color: volumeColor(cell?.intensity) }}
        >
          {cell?.value !== null && cell?.value !== undefined ? compact(cell.value) : "—"}
        </span>
      </div>
    </motion.div>
  );
}
