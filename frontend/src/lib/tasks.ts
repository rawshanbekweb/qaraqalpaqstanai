"use client";

/**
 * Iqtisodiy topshiriqlar — `/api/tasks`.
 *
 * Statistika (kuzatilgan qiymatlar) va topshiriqlar (ma'muriy qaror)
 * ikki xil narsa: birinchisi Excel'dan keladi va o'zgarmaydi, ikkinchisi
 * shu yerda yaratiladi va tahrirlanadi.
 */

import { authHeaders } from "@/lib/session";
import type { StatusId } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface Task {
  id: number;
  title: string;
  description: string | null;
  district_id: string;
  module_id: string;
  status: StatusId;
  progress: number;
  deadline: string;
  assignee: string;
}

export interface TaskDraft {
  title: string;
  description?: string;
  district_id: string;
  module_id: string;
  deadline: string;
  assignee: string;
  progress?: number;
}

async function readError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // JSON emas
  }
  if (res.status === 401) return "Sessiya tamamlandı, qaytadan kiriń";
  if (res.status === 403) return "Bul ámel ushın administrator huqıqı kerek";
  return `Server qátesi (${res.status})`;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...authHeaders(),
      ...init?.headers,
    },
    signal: AbortSignal.timeout(30_000),
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as T;
}

export function listTasks(): Promise<Task[]> {
  return call<Task[]>("/api/tasks");
}

export function createTask(draft: TaskDraft): Promise<Task> {
  return call<Task>("/api/tasks", { method: "POST", body: JSON.stringify(draft) });
}

/**
 * Bajarilish foizini yangilaydi. Status ochiq berilmasa backend uni
 * foizdan kelib chiqib o'zi aniqlaydi — qoida bitta joyda qoladi.
 */
export function updateTaskProgress(id: number, progress: number): Promise<Task> {
  return call<Task>(`/api/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ progress }),
  });
}

export function deleteTask(id: number): Promise<{ ok: boolean }> {
  return call<{ ok: boolean }>(`/api/tasks/${id}`, { method: "DELETE" });
}

export function tasksConfigured(): boolean {
  return Boolean(BASE);
}
