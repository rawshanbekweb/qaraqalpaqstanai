"use client";

import { motion } from "motion/react";

const BLOBS = [
  { c: "#22d3ee", x: "-12%", y: "-18%", s: 620, d: 0 },
  { c: "#818cf8", x: "58%", y: "-24%", s: 700, d: 3 },
  { c: "#e879f9", x: "24%", y: "58%", s: 560, d: 6 },
  { c: "#34d399", x: "76%", y: "48%", s: 520, d: 9 },
];

/** Sahifalar orqasidagi jonli aurora fon. */
export function AuroraBackground({ dense = false }: { dense?: boolean }) {
  return (
    <div className="aurora-field" aria-hidden>
      {BLOBS.map((b, i) => (
        <motion.div
          key={i}
          className="aurora-blob"
          style={{
            left: b.x,
            top: b.y,
            width: b.s,
            height: b.s,
            background: `radial-gradient(circle at 35% 35%, ${b.c}, transparent 68%)`,
            opacity: dense ? 0.5 : 0.32,
          }}
          animate={{
            x: [0, 60, -40, 0],
            y: [0, -50, 40, 0],
            scale: [1, 1.16, 0.94, 1],
          }}
          transition={{
            duration: 26 + i * 4,
            repeat: Infinity,
            ease: "easeInOut",
            delay: b.d,
          }}
        />
      ))}
      <div className="grid-veil" />
      <div className="noise-veil" />
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 120% 80% at 50% 0%, transparent 20%, rgb(4 6 15 / 0.75) 100%)",
        }}
      />
    </div>
  );
}
