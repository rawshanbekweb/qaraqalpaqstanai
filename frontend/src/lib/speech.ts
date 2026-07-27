"use client";

/**
 * Ovozli interfeys — brauzerning Web Speech API'si ustida.
 *
 * TTS: o'zbekcha ovoz mavjud bo'lmasa (aksar brauzerlarda yo'q), tur/ru/en
 * ovoziga tushiladi — o'zbek lotin matni tur ovozida eng tabiiy o'qiladi.
 * STT: uz-UZ tanilmasa ru-RU ga tushadi.
 */

const LANG_PREFERENCE = ["uz-UZ", "uz", "tr-TR", "ru-RU", "en-US"];

export function speechSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function recognitionSupported(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as unknown as Record<string, unknown>;
  return Boolean(w.SpeechRecognition || w.webkitSpeechRecognition);
}

let cachedVoice: SpeechSynthesisVoice | null = null;

function pickVoice(): SpeechSynthesisVoice | null {
  if (!speechSupported()) return null;
  if (cachedVoice) return cachedVoice;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;
  for (const lang of LANG_PREFERENCE) {
    const v = voices.find((x) => x.lang?.toLowerCase().startsWith(lang.toLowerCase()));
    if (v) {
      cachedVoice = v;
      return v;
    }
  }
  cachedVoice = voices[0];
  return cachedVoice;
}

/** Markdown belgilarini olib tashlab, o'qishga qulay matn qaytaradi. */
export function toSpeakable(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, "")
    .replace(/[*_`#>]/g, "")
    .replace(/\[(.*?)\]\(.*?\)/g, "$1")
    .replace(/^\s*[-–]\s*/gm, "")
    .replace(/\n{2,}/g, ". ")
    .replace(/\n/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export interface SpeakHandlers {
  onStart?: () => void;
  onEnd?: () => void;
  onError?: () => void;
}

export function speak(text: string, handlers: SpeakHandlers = {}) {
  if (!speechSupported()) {
    handlers.onError?.();
    return;
  }
  const synth = window.speechSynthesis;
  synth.cancel();

  const clean = toSpeakable(text).slice(0, 1200);
  if (!clean) {
    handlers.onEnd?.();
    return;
  }

  const utter = new SpeechSynthesisUtterance(clean);
  const voice = pickVoice();
  if (voice) {
    utter.voice = voice;
    utter.lang = voice.lang;
  } else {
    utter.lang = "tr-TR";
  }
  utter.rate = 1.02;
  utter.pitch = 1.0;
  utter.volume = 1;
  utter.onstart = () => handlers.onStart?.();
  utter.onend = () => handlers.onEnd?.();
  utter.onerror = () => handlers.onError?.();

  // Chrome'da ovozlar ro'yxati kech yuklanadi
  if (!voice) {
    synth.addEventListener(
      "voiceschanged",
      () => {
        const v = pickVoice();
        if (v) {
          utter.voice = v;
          utter.lang = v.lang;
        }
      },
      { once: true },
    );
  }

  synth.speak(utter);
}

export function stopSpeaking() {
  if (speechSupported()) window.speechSynthesis.cancel();
}

// ── Nutqni matnga (STT) ──────────────────────────────────────────────

type RecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};

export interface ListenHandlers {
  onResult: (text: string, final: boolean) => void;
  onEnd?: () => void;
  onError?: (reason: string) => void;
}

export function startListening(handlers: ListenHandlers): (() => void) | null {
  if (!recognitionSupported()) {
    handlers.onError?.("unsupported");
    return null;
  }
  const w = window as unknown as Record<string, new () => RecognitionLike>;
  const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
  const rec = new Ctor();

  rec.lang = "uz-UZ";
  rec.continuous = false;
  rec.interimResults = true;

  rec.onresult = (e) => {
    let interim = "";
    let final = "";
    for (let i = 0; i < e.results.length; i++) {
      const res = e.results[i] as ArrayLike<{ transcript: string }> & { isFinal?: boolean };
      const t = res[0]?.transcript ?? "";
      if (res.isFinal) final += t;
      else interim += t;
    }
    if (final) handlers.onResult(final, true);
    else if (interim) handlers.onResult(interim, false);
  };
  rec.onerror = () => handlers.onError?.("error");
  rec.onend = () => handlers.onEnd?.();

  try {
    rec.start();
  } catch {
    handlers.onError?.("start-failed");
    return null;
  }

  return () => {
    try {
      rec.stop();
    } catch {
      /* allaqachon to'xtagan */
    }
  };
}
