"use client";

import type { SessionUser } from "@/lib/types";

/**
 * Demo autentifikatsiyasi.
 *
 * Sessiya cookie'da saqlanadi, chunki uni `proxy.ts` server tomonda o'qib
 * /admin marshrutini himoya qiladi. Backend ulanganda bu qatlam JWT bilan
 * almashtiriladi — interfeys o'zgarmaydi.
 */

export const COOKIE_NAME = "qr_session";

const DEMO_USERS: Array<{ username: string; password: string } & SessionUser> = [
  {
    username: "admin",
    password: "admin123",
    fullName: "Bosh administrator",
    role: "admin",
  },
  {
    username: "rahbar",
    password: "rahbar123",
    fullName: "Rahbariyat vakili",
    role: "viewer",
  },
];

export function authenticate(username: string, password: string): SessionUser | null {
  const u = DEMO_USERS.find(
    (x) => x.username === username.trim().toLowerCase() && x.password === password,
  );
  if (!u) return null;
  return { username: u.username, fullName: u.fullName, role: u.role };
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
  { label: "Rahbar / ko'ruvchi", username: "rahbar", password: "rahbar123" },
];
