"use client";

import { create } from "zustand";
import { CURRENT_YEAR } from "@/data/dataset";
import type { ChartSpec, ChatMessage, ModuleId, StatusId } from "@/lib/types";

interface DashboardState {
  // ── Filtrlar ──
  moduleId: ModuleId | "all";
  status: StatusId | "all";
  period: "month" | "quarter" | "year";
  year: number;
  setModule: (m: ModuleId | "all") => void;
  setStatus: (s: StatusId | "all") => void;
  setPeriod: (p: "month" | "quarter" | "year") => void;
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
  moduleId: "all",
  status: "all",
  period: "year",
  year: CURRENT_YEAR,
  setModule: (moduleId) => set({ moduleId }),
  setStatus: (status) => set({ status }),
  setPeriod: (period) => set({ period }),
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
