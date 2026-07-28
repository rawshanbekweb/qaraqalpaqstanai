"use client";

import { AnimatePresence, motion } from "motion/react";
import {
  ArrowUp,
  Database,
  Mic,
  Sparkles,
  Square,
  Trash2,
  Volume2,
  VolumeX,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { SUGGESTED_PROMPTS } from "@/lib/prompts";
import { askAi } from "@/lib/api";
import { speak, startListening, stopSpeaking, recognitionSupported } from "@/lib/speech";
import { useDashboard } from "@/lib/store";
import type { ChatMessage, Recommendation } from "@/lib/types";
import { cn, uid } from "@/lib/utils";
import { Markdown } from "@/components/chat/Markdown";
import { StatusPill, ThinkingDots } from "@/components/ui/primitives";

/** useSyncExternalStore uchun o'zgarmas "obuna bo'lmaslik" funksiyasi. */
const NO_SUBSCRIBE = () => () => {};

const HORIZON_META: Record<Recommendation["horizon"], { label: string; color: string }> = {
  short: { label: "Qısqa múddet · 1–3 ay", color: "#0891b2" },
  mid: { label: "Orta múddet · 6 ay", color: "#8b5cf6" },
  long: { label: "Uzaq múddet · 1 jıl", color: "#059669" },
};

export function ChatPanel() {
  const {
    messages,
    thinking,
    pushMessage,
    setThinking,
    clearChat,
    setAiCharts,
    setHighlighted,
    focusDistrict,
    selectedDistrict,
    moduleId,
    year,
    voiceEnabled,
    toggleVoice,
    speaking,
    setSpeaking,
    listening,
    setListening,
  } = useDashboard();

  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const stopListenRef = useRef<(() => void) | null>(null);

  // Brauzer imkoniyati — serverda noma'lum, shuning uchun tashqi "store" sifatida o'qiladi
  const micSupported = useSyncExternalStore(
    NO_SUBSCRIBE,
    recognitionSupported,
    () => false,
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  const send = useCallback(
    async (text: string) => {
      const q = text.trim();
      if (!q || thinking) return;

      setDraft("");
      pushMessage({ id: uid("m"), role: "user", text: q, createdAt: Date.now() });
      setThinking(true);

      const res = await askAi(q, { districtId: selectedDistrict, moduleId, year });

      // "O'ylash" pauzasi — javob birdan otilib chiqmasligi uchun
      await new Promise((r) => setTimeout(r, 420));

      const id = uid("m");
      pushMessage({
        id,
        role: "assistant",
        text: res.text,
        charts: res.charts,
        insight: res.insight,
        recommendations: res.recommendations,
        sources: res.sources,
        createdAt: Date.now(),
      });
      setThinking(false);

      if (res.charts?.length) setAiCharts(res.charts);

      // Javob aynan BITTA hududga tegishli bo'lsa — bu chuqur to'xtalish:
      // xarita o'sha hududga qaraydi, o'ng panel kengayadi. Bir nechta
      // hudud bo'lsa oddiy yoritish bilan cheklanamiz.
      // Takrorlar olib tashlanadi: backend bir tumanning bir necha sohasini
      // qaytarishi mumkin, u holda ro'yxat uzunligi aldamchi bo'ladi.
      const hits = [...new Set(res.highlight ?? [])];
      if (hits.length === 1) focusDistrict(hits[0]);
      else setHighlighted(hits);

      if (voiceEnabled) {
        speak(res.text, {
          onStart: () => setSpeaking(true),
          onEnd: () => setSpeaking(false),
          onError: () => setSpeaking(false),
        });
      }
    },
    [
      thinking,
      pushMessage,
      setThinking,
      selectedDistrict,
      moduleId,
      year,
      setAiCharts,
      setHighlighted,
      focusDistrict,
      voiceEnabled,
      setSpeaking,
    ],
  );

  const toggleMic = useCallback(() => {
    if (listening) {
      stopListenRef.current?.();
      stopListenRef.current = null;
      setListening(false);
      return;
    }
    stopSpeaking();
    setSpeaking(false);
    const stop = startListening({
      onResult: (text, final) => {
        setDraft(text);
        if (final) {
          setListening(false);
          void send(text);
        }
      },
      onEnd: () => setListening(false),
      onError: () => setListening(false),
    });
    if (stop) {
      stopListenRef.current = stop;
      setListening(true);
    }
  }, [listening, send, setListening, setSpeaking]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Sarlavha */}
      <div className="flex items-center gap-2.5 px-4 pt-3 pb-2.5">
        <div className="relative">
          <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-cyan/25 to-violet/25 ring-1 ring-cyan/35">
            <Sparkles size={16} className="text-cyan" />
          </div>
          <AnimatePresence>
            {(speaking || thinking) && (
              <motion.span
                initial={{ scale: 0.6, opacity: 0 }}
                animate={{ scale: [1, 1.5], opacity: [0.6, 0] }}
                exit={{ opacity: 0 }}
                transition={{ duration: 1.6, repeat: Infinity }}
                className="absolute inset-0 rounded-xl ring-2 ring-cyan"
              />
            )}
          </AnimatePresence>
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[13px] font-bold tracking-tight text-ink">AI Analitik</h2>
          <p className="truncate text-[10.5px] text-ink-3">
            {speaking ? "Sóylep atır…" : listening ? "Tıńlap atır…" : "Bazadaǵı maǵlıwmatlar tiykarında"}
          </p>
        </div>
        <button
          onClick={() => {
            toggleVoice();
            if (voiceEnabled) {
              stopSpeaking();
              setSpeaking(false);
            }
          }}
          className={cn(
            "grid size-8 place-items-center rounded-lg ring-1 transition",
            voiceEnabled
              ? "bg-cyan/15 text-cyan ring-cyan/40"
              : "bg-abyss/60 text-ink-3 ring-edge/50 hover:text-ink-2",
          )}
          title={voiceEnabled ? "Dawıstı óshiriw" : "Dawıstı qosıw"}
          aria-pressed={voiceEnabled}
        >
          {voiceEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
        </button>
        {messages.length > 0 && (
          <button
            onClick={() => {
              clearChat();
              stopSpeaking();
              setSpeaking(false);
            }}
            className="grid size-8 place-items-center rounded-lg bg-abyss/60 text-ink-3 ring-1 ring-edge/50 transition hover:text-coral"
            title="Sáwbetti tazalaw"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>

      {/* Xabarlar */}
      <div ref={scrollRef} className="thin-scroll min-h-0 flex-1 space-y-3 overflow-y-auto px-3.5 pb-2">
        {messages.length === 0 && <EmptyState onPick={send} />}

        {messages.map((m) => (
          <Message key={m.id} m={m} />
        ))}

        <AnimatePresence>
          {thinking && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="glass inline-flex items-center gap-2.5 rounded-2xl px-3.5 py-2.5"
            >
              <ThinkingDots />
              <span className="text-[11.5px] text-ink-3">Baza analiz etilip atır…</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Kiritish */}
      <div className="border-t border-hairline/60 p-3">
        <div
          className={cn(
            "glass flex items-end gap-2 rounded-2xl p-2 transition-shadow",
            listening && "ring-2 ring-crimson/50",
          )}
        >
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(draft);
              }
            }}
            rows={1}
            placeholder="Sorawıńızdı jazıń…"
            className="thin-scroll max-h-24 min-h-[36px] flex-1 resize-none bg-transparent px-2 py-2 text-[12.5px] text-ink outline-none placeholder:text-ink-3/80"
          />

          {micSupported && (
            <button
              onClick={toggleMic}
              className={cn(
                "relative grid size-9 shrink-0 place-items-center rounded-xl transition",
                listening
                  ? "bg-crimson/20 text-crimson"
                  : "bg-abyss/60 text-ink-3 hover:text-cyan",
              )}
              title={listening ? "Toqtatıw" : "Dawıs penen soraw"}
            >
              {listening && (
                <motion.span
                  className="absolute inset-0 rounded-xl bg-crimson/25"
                  animate={{ scale: [1, 1.35], opacity: [0.55, 0] }}
                  transition={{ duration: 1.4, repeat: Infinity }}
                />
              )}
              <Mic size={15} className="relative" />
            </button>
          )}

          {speaking ? (
            <button
              onClick={() => {
                stopSpeaking();
                setSpeaking(false);
              }}
              className="grid size-9 shrink-0 place-items-center rounded-xl bg-crimson/20 text-crimson transition hover:bg-crimson/30"
              title="Oqıwdı toqtatıw"
            >
              <Square size={13} />
            </button>
          ) : (
            <button
              onClick={() => void send(draft)}
              disabled={!draft.trim() || thinking}
              className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-cyan to-iris text-void transition disabled:opacity-35 enabled:hover:brightness-110"
              title="Jiberiw"
            >
              <ArrowUp size={16} strokeWidth={2.6} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (t: string) => void }) {
  return (
    <div className="flex flex-col items-center px-2 py-6 text-center">
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        className="mb-3 grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-cyan/20 to-violet/20 ring-1 ring-cyan/30"
      >
        <Sparkles size={22} className="text-cyan" />
      </motion.div>
      <h3 className="text-[13.5px] font-bold text-ink">Ekonomikalıq analiz járdemshisi</h3>
      <p className="mt-1 max-w-[240px] text-[11.5px] leading-relaxed text-ink-3">
        Tek ǵana bazadaǵı statistika tiykarında juwap beredi — grafikler hám usınıslar
        menen.
      </p>
      <div className="mt-4 flex w-full flex-wrap justify-center gap-1.5">
        {SUGGESTED_PROMPTS.map((p, i) => (
          <motion.button
            key={p}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.06 }}
            onClick={() => onPick(p)}
            className="rounded-full bg-abyss/70 px-2.5 py-1.5 text-[11px] text-ink-2 ring-1 ring-edge/50 transition hover:text-ink hover:ring-cyan/50"
          >
            {p}
          </motion.button>
        ))}
      </div>
    </div>
  );
}

function Message({ m }: { m: ChatMessage }) {
  if (m.role === "user") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: "spring", stiffness: 380, damping: 30 }}
        className="flex justify-end"
      >
        <div className="max-w-[86%] rounded-2xl rounded-br-md bg-gradient-to-br from-cyan/85 to-iris/85 px-3.5 py-2 text-[12.5px] font-medium text-void">
          {m.text}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="space-y-2"
    >
      <div className="glass rounded-2xl rounded-bl-md px-3.5 py-3">
        <Markdown text={m.text} />

        {m.sources !== undefined && (
          <div className="mt-2.5 flex items-center gap-1.5 border-t border-hairline/60 pt-2 text-[10px] text-ink-3">
            <Database size={10} />
            <span>{m.sources} jazıw kontekstke alındı</span>
          </div>
        )}
      </div>

      {m.insight && (
        <motion.div
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
          className="glass overflow-hidden rounded-2xl"
        >
          <div className="flex items-start gap-2 px-3.5 py-2.5">
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-[9.5px] font-semibold tracking-wider text-violet uppercase">
                  AI xulosasi
                </span>
                <StatusPill status={m.insight.severity} />
              </div>
              <div className="text-[12px] font-semibold text-ink">{m.insight.headline}</div>
              <div className="mt-0.5 text-[11px] leading-relaxed text-ink-3">{m.insight.body}</div>
            </div>
          </div>
        </motion.div>
      )}

      {m.recommendations?.length ? (
        <div className="space-y-2">
          {m.recommendations.map((r, i) => (
            <motion.div
              key={r.horizon}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
              className="glass overflow-hidden rounded-2xl"
            >
              <div
                className="flex items-center gap-2 px-3.5 py-2"
                style={{
                  background: `linear-gradient(90deg, color-mix(in oklab, ${HORIZON_META[r.horizon].color} 16%, transparent), transparent)`,
                }}
              >
                <span
                  className="size-2 rounded-full"
                  style={{ background: HORIZON_META[r.horizon].color }}
                />
                <span className="text-[10px] font-semibold tracking-wide text-ink-2 uppercase">
                  {HORIZON_META[r.horizon].label}
                </span>
              </div>
              <div className="px-3.5 py-2.5">
                <div className="mb-1.5 text-[12px] font-semibold text-ink">{r.title}</div>
                <ul className="space-y-1.5">
                  {r.actions.map((a, k) => (
                    <li key={k} className="flex gap-2 text-[11.5px] leading-relaxed text-ink-2">
                      <span
                        className="mt-[6px] size-1 shrink-0 rounded-full"
                        style={{ background: HORIZON_META[r.horizon].color }}
                      />
                      <span>{a}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-2 border-t border-hairline/60 pt-2 text-[10.5px] text-ink-3">
                  <span className="font-semibold text-ink-2">Kutilayotgan natija: </span>
                  {r.impact}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      ) : null}
    </motion.div>
  );
}
