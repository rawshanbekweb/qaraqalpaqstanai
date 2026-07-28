"use client";

import { create } from "zustand";
import type { ChartSpec, ChatMessage } from "@/lib/types";

interface DashboardState {
  // ── Filtrlar ──
  /**
   * Tayanch soha kodi (`sanaat`, `awil_xojaligi`, ...) — backend
   * `/api/stats/meta` qaytaradigan ro'yxatdan. "Barchasi" varianti yo'q:
   * tonna bilan mlrd so'mni qo'shib bo'lmaydi, xarita esa har doim bitta
   * ko'rsatkichni bo'yaydi.
   */
  moduleId: string;
  /** 0 — yillar ro'yxati hali kelmagan (meta yuklanmoqda). */
  year: number;
  setModule: (m: string) => void;
  setYear: (y: number) => void;

  // ── Xarita ──
  hoveredDistrict: string | null;
  selectedDistrict: string | null;
  /** AI javobidan kelib chiqib yoritiladigan tumanlar */
  highlighted: string[];
  setHovered: (id: string | null) => void;
  selectDistrict: (id: string | null) => void;
  setHighlighted: (ids: string[]) => void;

  // ── Chuqur fokus ──
  /**
   * AI bitta hududga chuqur to'xtalganda yoqiladi: xarita ortga chekinib
   * faqat shu hududga qaraydi, o'ng panel esa chat tomon kengayadi.
   */
  focusMode: boolean;
  focusDistrict: (id: string) => void;
  exitFocus: () => void;

  // ── Chat ──
  messages: ChatMessage[];
  thinking: boolean;
  pushMessage: (m: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  setThinking: (v: boolean) => void;
  clearChat: () => void;

  // ── O'ng panel ──
  /** AI generatsiya qilgan grafiklar — o'ng panelga uzatiladi */
  aiCharts: ChartSpec[];
  setAiCharts: (c: ChartSpec[]) => void;

  // ── Ovoz ──
  voiceEnabled: boolean;
  speaking: boolean;
  listening: boolean;
  toggleVoice: () => void;
  setSpeaking: (v: boolean) => void;
  setListening: (v: boolean) => void;
}

export const useDashboard = create<DashboardState>((set) => ({
  moduleId: "sanaat",
  year: 0,
  setModule: (moduleId) => set({ moduleId }),
  setYear: (year) => set({ year }),

  hoveredDistrict: null,
  selectedDistrict: null,
  highlighted: [],
  setHovered: (hoveredDistrict) => set({ hoveredDistrict }),
  // Tumandan voz kechilsa chuqur fokus ham o'z-o'zidan yopiladi
  selectDistrict: (selectedDistrict) =>
    set(selectedDistrict ? { selectedDistrict } : { selectedDistrict: null, focusMode: false }),
  setHighlighted: (highlighted) => set({ highlighted }),

  focusMode: false,
  focusDistrict: (id) => set({ selectedDistrict: id, highlighted: [id], focusMode: true }),
  exitFocus: () => set({ focusMode: false }),

  messages: [],
  thinking: false,
  pushMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  updateMessage: (id, patch) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),
  setThinking: (thinking) => set({ thinking }),
  clearChat: () => set({ messages: [], aiCharts: [], highlighted: [], focusMode: false }),

  aiCharts: [],
  setAiCharts: (aiCharts) => set({ aiCharts }),

  voiceEnabled: true,
  speaking: false,
  listening: false,
  toggleVoice: () => set((s) => ({ voiceEnabled: !s.voiceEnabled })),
  setSpeaking: (speaking) => set({ speaking }),
  setListening: (listening) => set({ listening }),
}));
