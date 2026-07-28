import type { StatusId } from "@/lib/types";

/**
 * Holat palitrasi.
 *
 * Sohalar ro'yxati bu yerda YO'Q — u bazadan (`/api/stats/meta`) keladi,
 * chunki qaysi ko'rsatkich qaysi sohani ta'minlashini admin belgilaydi.
 */
export interface StatusMeta {
  id: StatusId;
  name: string;
  color: string;
}

/**
 * Status palitrasi — SERIYA ranglaridan qat'iy ajratilgan va hech qachon
 * "9-chi seriya" sifatida ishlatilmaydi. Har doim matnli yorliq bilan
 * birga chiqadi, ya'ni ma'no faqat rangga tayanmaydi.
 *
 * Nomlar o'sish ma'nosida: manba statistikada reja yo'q, shuning uchun
 * "bajarilgan/kritik" o'rniga o'tgan yilga nisbatan o'zgarish o'qiladi.
 * Topshiriqlarda esa o'sha ranglar bajarilish foizini ko'rsatadi.
 */
export const STATUSES: StatusMeta[] = [
  { id: "completed", name: "Ósiw", color: "#0ca30c" },
  { id: "in_progress", name: "Turaqlı", color: "#8fa3d4" },
  { id: "at_risk", name: "Tómenlew", color: "#fab219" },
  { id: "critical", name: "Keskin tómenlew", color: "#d03b3b" },
];

export const STATUS_BY_ID = Object.fromEntries(STATUSES.map((s) => [s.id, s])) as Record<
  StatusId,
  StatusMeta
>;
