import type { AiInsight, ChartSpec, Recommendation } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface AiAnswer {
  text: string;
  charts: ChartSpec[];
  insight?: AiInsight;
  recommendations: Recommendation[];
  sources: number;
  highlight: string[];
}

/**
 * Backend javobini qancha kutamiz.
 *
 * Render'ning bepul darajasi 15 daqiqa harakatsizlikdan keyin uxlaydi va
 * uyg'onishi ~30–60 soniya oladi. Cheksiz kutish o'rniga shu muddatdan
 * so'ng foydalanuvchiga holatni ochiq aytamiz; so'rov esa backendni
 * baribir uyg'otib yuboradi — keyingi savol allaqachon javob topadi.
 */
const TIMEOUT_MS = 20_000;

/**
 * Javob bazadagi 24 mingdan ortiq o'lchov ustida quriladi, ya'ni FAQAT
 * backendda. Brauzerda mahalliy nusxa yo'q: raqamlarni klientda qayta
 * ixtiro qilish javoblar bazadagidan farq qilishiga olib kelardi.
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
        body: JSON.stringify({
          prompt,
          district_id: context?.districtId ?? null,
          module_id: context?.moduleId ?? null,
          year: context?.year ?? null,
        }),
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      if (res.ok) {
        const data = (await res.json()) as AiAnswer;
        return { ...data, offline: false };
      }
    } catch {
      // tarmoq xatosi yoki kutish muddati tugadi
    }
  }

  return {
    text:
      "**Maǵlıwmatlar bazası menen baylanıs joq**\n\n" +
      "Juwap 24 199 ólshem ústinde qurıladı, sonlıqtan server ulanbaǵanda " +
      "sanlardı beriw múmkin emes. Bir neshe sekundtan keyin qayta urınıń — " +
      "server oyanıp atır.",
    charts: [],
    recommendations: [],
    sources: 0,
    highlight: [],
    offline: true,
  };
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
