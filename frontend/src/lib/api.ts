import { answer, type AiAnswer } from "@/lib/ai-engine";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

/**
 * Backend javobini qancha kutamiz.
 *
 * Render'ning bepul darajasi 15 daqiqa harakatsizlikdan keyin uxlaydi va
 * uyg'onishi ~30–60 soniya oladi. Cheksiz kutish o'rniga shu muddatdan
 * so'ng mahalliy dvigatelga o'tamiz: foydalanuvchi javobni darhol oladi,
 * so'rov esa backendni baribir uyg'otib yuboradi — keyingi savol allaqachon
 * haqiqiy bazadan javob topadi.
 */
const TIMEOUT_MS = 12_000;

/**
 * Backend (FastAPI + PostgreSQL + Claude) mavjud bo'lsa — o'sha javob beradi.
 * Aks holda brauzerdagi mahalliy RAG dvigateli ishlaydi, shunda platforma
 * backendsiz ham to'liq namoyish qilinadi.
 */
export async function askAi(
  prompt: string,
  context?: { districtId?: string | null; moduleId?: string; year?: number },
): Promise<AiAnswer & { offline: boolean }> {
  if (BASE) {
    try {
      const res = await fetch(`${BASE}/api/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, ...context }),
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      if (res.ok) {
        const data = (await res.json()) as AiAnswer;
        return { ...data, offline: false };
      }
    } catch {
      // tarmoq xatosi yoki kutish muddati tugadi — mahalliy dvigatelga tushamiz
    }
  }
  return { ...answer(prompt), offline: true };
}

/**
 * Backendni oldindan uyg'otish. Sahifa ochilganda bir marta chaqiriladi —
 * foydalanuvchi dashboardni ko'zdan kechirguncha xizmat tayyor bo'ladi.
 * Natijasi ahamiyatsiz, xatolar ataylab yutiladi.
 */
export function warmUpApi(): void {
  if (!BASE) return;
  void fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(60_000) }).catch(() => {});
}

export function apiConfigured(): boolean {
  return Boolean(BASE);
}
