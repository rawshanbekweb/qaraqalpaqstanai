"use client";

import { motion } from "motion/react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { KarakalpakstanMap } from "@/components/map/KarakalpakstanMap";
import { StatsPanel } from "@/components/charts/StatsPanel";
import { InsightBar } from "@/components/layout/InsightBar";
import { TopBar } from "@/components/layout/TopBar";
import { warmUpApi } from "@/lib/api";
import { RAIL_LEFT, railRight } from "@/lib/layout";
import { useDashboard } from "@/lib/store";

/**
 * Foydalanuvchi paneli.
 *
 * Xarita butun ekranni egallaydi, chat (chapda) va statistika (o'ngda) esa
 * uning ustida suzuvchi shisha panellar sifatida turadi. Panellar orasidagi
 * bo'shliqda sichqoncha to'g'ridan-to'g'ri xaritaga tegishi kerak, shuning
 * uchun ustki qatlamga `overlay-pass` qo'yilgan.
 */
export default function DashboardPage() {
  const focusMode = useDashboard((s) => s.focusMode);

  // Yuqori qatorlar balandligi shrift/o'rash tufayli o'zgaruvchan —
  // panellarni qattiq raqamga emas, o'lchangan qiymatga bog'laymiz.
  const headRef = useRef<HTMLDivElement>(null);
  const [headH, setHeadH] = useState(112);

  // Uxlab qolgan backendni oldindan uyg'otamiz (bepul hostingda muhim)
  useEffect(() => {
    warmUpApi();
  }, []);

  useLayoutEffect(() => {
    const el = headRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setHeadH(e.contentRect.height));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const railTop = headH + 12;

  return (
    <div
      className="app-shell relative h-dvh overflow-hidden"
      // Xarita ustidagi suzuvchi boshqaruvlar ham shu balandlikka tayanadi
      style={{ "--head-h": `${headH}px` } as React.CSSProperties}
    >
      <AuroraBackground />

      {/* Xarita — eng ostki, lekin to'liq interaktiv qatlam */}
      <div className="absolute inset-0 z-0">
        <KarakalpakstanMap />
      </div>

      {/* Yuqori qatorlar */}
      <div ref={headRef} className="absolute inset-x-0 top-0 z-30">
        <TopBar />
        <InsightBar />
      </div>

      {/* Keng ekran — suzuvchi panellar */}
      <div className="overlay-pass absolute inset-0 z-20 hidden lg:block">
        <motion.section
          className="glass-rail glass-top-glow absolute bottom-3 left-3 overflow-hidden"
          style={{ width: RAIL_LEFT - 24, top: railTop }}
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
          <ChatPanel />
        </motion.section>

        {/* Chuqur fokusda chat tomon kengayadi */}
        <motion.section
          className="glass-rail glass-top-glow absolute right-3 bottom-3 overflow-hidden"
          style={{ top: railTop }}
          initial={{ opacity: 0, x: 24, width: railRight(false) - 24 }}
          animate={{ opacity: 1, x: 0, width: railRight(focusMode) - 24 }}
          transition={{ type: "spring", stiffness: 120, damping: 24, mass: 0.9 }}
        >
          <StatsPanel />
        </motion.section>
      </div>

      {/*
        Tor ekran — panellar ustma-ust. Tepada xarita ko'rinib turishi uchun
        ataylab bo'sh joy qoldirilgan; u sichqonchani o'tkazib yuboradi,
        shuning uchun ikkinchi SVG chizish shart emas.
      */}
      <div className="pointer-events-none absolute inset-0 z-20 overflow-y-auto lg:hidden">
        <div className="h-[46vh]" aria-hidden />
        <div className="pointer-events-auto space-y-3 p-3">
          <section className="glass-rail glass-top-glow h-[440px] overflow-hidden">
            <ChatPanel />
          </section>
          <section className="glass-rail glass-top-glow h-[620px] overflow-hidden">
            <StatsPanel />
          </section>
        </div>
      </div>
    </div>
  );
}
