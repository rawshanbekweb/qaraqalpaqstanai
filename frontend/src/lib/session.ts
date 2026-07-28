"use client";

import type { SessionUser } from "@/lib/types";

/**
 * Autentifikatsiya.
 *
 * Sessiya cookie'da saqlanadi, chunki uni `proxy.ts` server tomonda o'qib
 * /admin marshrutini himoya qiladi. Backend ulangan bo'lsa cookie ichida
 * uning bergan JWT'si ham turadi — admin yozuv amallari o'shanga tayanadi.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export const COOKIE_NAME = "qr_session";

const DEMO_USERS: Array<{ username: string; password: string } & SessionUser> = [
  {
    username: "admin",
    password: "admin123",
    fullName: "Bas administrator",
    role: "admin",
  },
  {
    username: "rahbar",
    password: "rahbar123",
    fullName: "Basshılıq wákili",
    role: "viewer",
  },
];

/**
 * Avval backend tekshiradi — faqat u haqiqiy token beradi. Backend
 * ulanmagan bo'lsa (namoyish rejimi) demo hisoblar ishlaydi, lekin
 * tokensiz: admin panel ma'lumotni ko'rsatmaydi va bu ochiq aytiladi.
 */
export async function authenticate(
  username: string,
  password: string,
): Promise<SessionUser | null> {
  const login = username.trim().toLowerCase();

  if (BASE) {
    try {
      const res = await fetch(`${BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: login, password }),
        signal: AbortSignal.timeout(20_000),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          access_token: string;
          username: string;
          full_name: string;
          role: string;
        };
        return {
          username: data.username,
          fullName: data.full_name,
          role: data.role === "admin" ? "admin" : "viewer",
          token: data.access_token,
        };
      }
      if (res.status === 401) return null;
    } catch {
      // tarmoq xatosi — quyidagi demo tekshiruviga tushamiz
    }
  }

  const u = DEMO_USERS.find((x) => x.username === login && x.password === password);
  if (!u) return null;
  return { username: u.username, fullName: u.fullName, role: u.role };
}

/** Admin so'rovlari uchun sarlavhalar; token bo'lmasa bo'sh obyekt. */
export function authHeaders(): Record<string, string> {
  const token = getSession()?.token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function encode(user: SessionUser): string {
  return encodeURIComponent(btoa(unescape(encodeURIComponent(JSON.stringify(user)))));
}

function decode(raw: string): SessionUser | null {
  try {
    return JSON.parse(decodeURIComponent(escape(atob(decodeURIComponent(raw))))) as SessionUser;
  } catch {
    return null;
  }
}

export function saveSession(user: SessionUser) {
  document.cookie = `${COOKIE_NAME}=${encode(user)}; path=/; max-age=${60 * 60 * 12}; samesite=lax`;
}

export function getSession(): SessionUser | null {
  if (typeof document === "undefined") return null;
  const raw = document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${COOKIE_NAME}=`))
    ?.split("=")[1];
  return raw ? decode(raw) : null;
}

export function clearSession() {
  document.cookie = `${COOKIE_NAME}=; path=/; max-age=0`;
}

export const DEMO_CREDENTIALS = [
  { label: "Administrator", username: "admin", password: "admin123" },
  { label: "Basshı / kóriwshi", username: "rahbar", password: "rahbar123" },
];
