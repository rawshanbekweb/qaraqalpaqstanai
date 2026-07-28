"use client";

import { AnimatePresence, motion } from "motion/react";
import { AlertCircle, ArrowRight, Eye, EyeOff, Loader2, Lock, Radio, User } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { DISTRICTS } from "@/data/districts";
import { authenticate, DEMO_CREDENTIALS, saveSession } from "@/lib/session";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { Button, Field, Input } from "@/components/ui/primitives";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginView />
    </Suspense>
  );
}

function LoginView() {
  const router = useRouter();
  const params = useSearchParams();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);

    const user = await authenticate(username, password);
    if (!user) {
      setBusy(false);
      setError("Login yamasa parol qáte. Tómendegi demo esaplardan paydalanıń.");
      return;
    }

    saveSession(user);
    const next = params.get("next");
    router.replace(user.role === "admin" && (!next || next === "/login") ? "/admin" : (next ?? "/"));
  }

  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden p-5">
      <AuroraBackground dense />

      <div className="relative z-10 grid w-full max-w-5xl items-center gap-8 lg:grid-cols-[1.05fr_0.95fr]">
        {/* Chap: brend hikoyasi */}
        <motion.section
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="hidden lg:block"
        >
          <div className="mb-6 inline-flex items-center gap-3">
            <div className="relative grid size-12 place-items-center rounded-2xl bg-gradient-to-br from-cyan via-iris to-magenta">
              <Radio size={22} className="text-void" strokeWidth={2.4} />
              <motion.span
                className="absolute inset-0 rounded-2xl ring-2 ring-cyan/60"
                animate={{ scale: [1, 1.4], opacity: [0.55, 0] }}
                transition={{ duration: 2.8, repeat: Infinity }}
              />
            </div>
            <div>
              <div className="text-[11px] font-semibold tracking-[0.2em] text-cyan uppercase">
                Qaraqalpaqstan Respublikası
              </div>
              <div className="text-[13px] text-ink-3">Ministrler Keńesi monitoringi</div>
            </div>
          </div>

          <h1 className="text-[42px] leading-[1.06] font-bold tracking-tight text-ink">
            Ekonomikalıq monitoring hám
            <br />
            <span className="text-gradient">AI analitika platforması</span>
          </h1>

          <p className="mt-4 max-w-lg text-[14px] leading-relaxed text-ink-2">
            17 rayon hám 7 tiykarǵı taraw boyınsha 2010–2026 jıllardıń rásmiy statistikası bir
            bazada. Jasalma intellekt tap sol maǵlıwmatlar tiykarında analiz etedi, artta qalıp
            atırǵan baǵdarlardı tabadı hám basqıshpa-basqısh háreket rejesin beredi.
          </p>

          <div className="mt-8 grid max-w-lg grid-cols-3 gap-3">
            {[
              { v: DISTRICTS.length, l: "rayon hám qala" },
              { v: 7, l: "tiykarǵı taraw" },
              { v: "2010–2026", l: "esabat jılları" },
            ].map((s, i) => (
              <motion.div
                key={s.l}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 + i * 0.1 }}
                className="glass rounded-2xl px-3.5 py-3"
              >
                <div className="text-2xl font-semibold tracking-tight text-ink">{s.v}</div>
                <div className="mt-0.5 text-[11px] text-ink-3">{s.l}</div>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* O'ng: forma */}
        <motion.section
          initial={{ opacity: 0, y: 26, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
          className="glass glass-top-glow mx-auto w-full max-w-[420px] overflow-hidden rounded-3xl"
        >
          <div className="px-7 pt-7 pb-2">
            <div className="mb-1 flex items-center gap-2.5 lg:hidden">
              <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-cyan via-iris to-magenta">
                <Radio size={17} className="text-void" strokeWidth={2.4} />
              </div>
              <span className="text-[13px] font-bold text-ink">Qaraqalpaqstan Monitoring</span>
            </div>
            <h2 className="text-[22px] font-bold tracking-tight text-ink">Sistemaǵa kiriw</h2>
            <p className="mt-1 text-[12.5px] text-ink-3">
              Panelge kiriw ushın esap maǵlıwmatlarıńızdı kiritiń
            </p>
          </div>

          <form onSubmit={submit} className="space-y-3.5 px-7 pt-5 pb-6">
            <Field label="Login">
              <div className="relative">
                <User
                  size={15}
                  className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-3"
                />
                <Input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  autoComplete="username"
                  className="pl-9"
                  required
                />
              </div>
            </Field>

            <Field label="Parol">
              <div className="relative">
                <Lock
                  size={15}
                  className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-3"
                />
                <Input
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="px-9"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute top-1/2 right-2.5 -translate-y-1/2 rounded p-1 text-ink-3 transition hover:text-ink-2"
                  aria-label={showPass ? "Paroldı jasırıw" : "Paroldı kórsetiw"}
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </Field>

            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="flex items-start gap-2 rounded-xl bg-crimson/12 px-3 py-2.5 ring-1 ring-crimson/30">
                    <AlertCircle size={14} className="mt-0.5 shrink-0 text-crimson" />
                    <span className="text-[11.5px] leading-relaxed text-coral">{error}</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <Button type="submit" disabled={busy} className="w-full">
              {busy ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  Tekserilip atır…
                </>
              ) : (
                <>
                  Kiriw
                  <ArrowRight size={15} />
                </>
              )}
            </Button>

            <div className="pt-1">
              <div className="mb-2 text-center text-[10px] tracking-wider text-ink-3 uppercase">
                Demo esaplar
              </div>
              <div className="grid grid-cols-2 gap-2">
                {DEMO_CREDENTIALS.map((c) => (
                  <button
                    key={c.username}
                    type="button"
                    onClick={() => {
                      setUsername(c.username);
                      setPassword(c.password);
                      setError(null);
                    }}
                    className="rounded-xl bg-abyss/60 px-2.5 py-2 text-left ring-1 ring-edge/50 transition hover:ring-cyan/50"
                  >
                    <div className="truncate text-[11px] font-semibold text-ink-2">{c.label}</div>
                    <div className="tnum truncate text-[10px] text-ink-3">
                      {c.username} / {c.password}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </form>
        </motion.section>
      </div>
    </main>
  );
}
