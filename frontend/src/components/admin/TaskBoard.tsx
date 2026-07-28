"use client";

import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, CalendarClock, Loader2, Plus, Trash2, User, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { DISTRICTS, DISTRICT_BY_ID } from "@/data/districts";
import { STATUS_BY_ID } from "@/data/modules";
import {
  createTask,
  deleteTask,
  listTasks,
  tasksConfigured,
  updateTaskProgress,
  type Task,
} from "@/lib/tasks";
import { useStatsMeta } from "@/lib/stats";
import type { StatusId } from "@/lib/types";
import { cn, daysLeft, formatDate, trim } from "@/lib/utils";
import {
  Button,
  Field,
  Input,
  Meter,
  Segmented,
  Select,
  StatusPill,
  Textarea,
} from "@/components/ui/primitives";

/**
 * Iqtisodiy topshiriqlar boshqaruvi.
 *
 * Ma'lumot backendda saqlanadi: bu yerdagi o'zgarish sahifa yangilangach
 * ham qolishi kerak, xotiradagi ro'yxat esa yo'qolib ketardi.
 */
export function TaskBoard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<StatusId | "all">("all");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(tasksConfigured());
  const { data: meta } = useStatsMeta();
  const modules = useMemo(() => meta?.modules ?? [], [meta]);

  const reload = useCallback(() => {
    if (!tasksConfigured()) return;
    listTasks()
      .then((rows) => {
        setTasks(rows);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(reload, [reload]);

  const moduleName = useCallback(
    (id: string) => modules.find((m) => m.id === id)?.short ?? id,
    [modules],
  );
  const moduleColor = useCallback(
    (id: string) => modules.find((m) => m.id === id)?.color ?? "#5a6588",
    [modules],
  );

  const visible = useMemo(
    () =>
      tasks
        .filter((t) => filter === "all" || t.status === filter)
        .sort((a, b) => a.deadline.localeCompare(b.deadline)),
    [tasks, filter],
  );

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: tasks.length };
    for (const t of tasks) c[t.status] = (c[t.status] ?? 0) + 1;
    return c;
  }, [tasks]);

  /** Avval ekranda, keyin serverda — sudragich sakramasin. */
  async function changeProgress(task: Task, progress: number) {
    setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, progress } : t)));
    try {
      const saved = await updateTaskProgress(task.id, progress);
      setTasks((prev) => prev.map((t) => (t.id === saved.id ? saved : t)));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Saqlanbadı");
      reload();
    }
  }

  async function remove(task: Task) {
    try {
      await deleteTask(task.id);
      setTasks((prev) => prev.filter((t) => t.id !== task.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Óshirilmedi");
    }
  }

  if (!tasksConfigured()) {
    return (
      <div className="rounded-2xl bg-abyss/50 px-4 py-10 text-center text-[12.5px] text-ink-3 ring-1 ring-edge/40">
        Tapsırmalar serverde saqlanadı — NEXT_PUBLIC_API_URL sazlanbaǵan.
      </div>
    );
  }

  return (
    <div className="space-y-3.5">
      {error && (
        <div className="flex items-start gap-2 rounded-xl bg-crimson/12 px-3 py-2.5 ring-1 ring-crimson/30">
          <AlertTriangle size={14} className="mt-0.5 shrink-0 text-crimson" />
          <span className="text-[11.5px] text-coral">{error}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Segmented<StatusId | "all">
          layoutId="task-status"
          size="sm"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: `Barlıǵı (${counts.all})` },
            ...Object.values(STATUS_BY_ID).map((s) => ({
              value: s.id,
              label: `${s.name} (${counts[s.id] ?? 0})`,
              color: s.color,
            })),
          ]}
        />
        <div className="flex-1" />
        <Button
          type="button"
          onClick={() => setCreating((v) => !v)}
          variant={creating ? "outline" : "solid"}
          disabled={modules.length === 0}
        >
          {creating ? <X size={14} /> : <Plus size={14} />}
          {creating ? "Biykarlaw" : "Jańa tapsırma"}
        </Button>
      </div>

      <AnimatePresence>
        {creating && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <NewTaskForm
              modules={modules}
              onCreated={(t) => {
                setTasks((prev) => [t, ...prev]);
                setCreating(false);
                setError(null);
              }}
              onError={setError}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-10 text-[12px] text-ink-3">
          <Loader2 size={14} className="animate-spin" />
          Júklenbekte…
        </div>
      ) : (
        <div className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence mode="popLayout">
            {visible.map((t, i) => (
              <TaskCard
                key={t.id}
                task={t}
                index={i}
                color={moduleColor(t.module_id)}
                moduleName={moduleName(t.module_id)}
                onProgress={(p) => void changeProgress(t, p)}
                onRemove={() => void remove(t)}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      {!loading && visible.length === 0 && (
        <div className="rounded-2xl bg-abyss/50 px-4 py-10 text-center text-[12.5px] text-ink-3 ring-1 ring-edge/40">
          Saylanǵan halatta tapsırma joq.
        </div>
      )}
    </div>
  );
}

function TaskCard({
  task,
  index,
  color,
  moduleName,
  onProgress,
  onRemove,
}: {
  task: Task;
  index: number;
  color: string;
  moduleName: string;
  onProgress: (p: number) => void;
  onRemove: () => void;
}) {
  const left = daysLeft(task.deadline);
  const overdue = left < 0 && task.status !== "completed";

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ delay: Math.min(index * 0.035, 0.3), duration: 0.4 }}
      className="glass flex flex-col gap-2.5 rounded-2xl p-3.5"
    >
      <div className="flex items-start gap-2">
        <span className="mt-1 size-2 shrink-0 rounded-full" style={{ background: color }} />
        <h3 className="min-w-0 flex-1 text-[12.5px] leading-snug font-semibold text-ink">
          {task.title}
        </h3>
        <StatusPill status={task.status} />
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10.5px] text-ink-3">
        <span>{DISTRICT_BY_ID[task.district_id]?.name ?? task.district_id}</span>
        <span>·</span>
        <span>{moduleName}</span>
      </div>

      <div>
        <div className="mb-1.5 flex items-baseline justify-between">
          <span className="text-[10.5px] text-ink-3">Orınlanıwı</span>
          <span className="tnum text-[11.5px] font-semibold text-ink">
            {trim(task.progress, 0)}%
          </span>
        </div>
        <Meter value={task.progress / 100} color={STATUS_BY_ID[task.status].color} />
        <input
          type="range"
          min={0}
          max={100}
          defaultValue={task.progress}
          // Serverga faqat sudragich qo'yib yuborilganda yoziladi —
          // har piksel siljishida so'rov ketmasin
          onPointerUp={(e) => onProgress(Number((e.target as HTMLInputElement).value))}
          onKeyUp={(e) => onProgress(Number((e.target as HTMLInputElement).value))}
          className="mt-2 w-full accent-cyan"
          aria-label={`${task.title} orınlanıw procenti`}
        />
      </div>

      <div className="flex items-center gap-2 border-t border-hairline/60 pt-2.5 text-[10.5px]">
        <User size={11} className="shrink-0 text-ink-3" />
        <span className="min-w-0 flex-1 truncate text-ink-2">{task.assignee}</span>
        <CalendarClock
          size={11}
          className={cn("shrink-0", overdue ? "text-crimson" : "text-ink-3")}
        />
        <span className={cn("tnum", overdue ? "font-semibold text-crimson" : "text-ink-2")}>
          {formatDate(task.deadline)}
          {overdue ? ` (${Math.abs(left)} kún keshikti)` : ""}
        </span>
        <button
          onClick={onRemove}
          title="Óshiriw"
          className="grid size-5 shrink-0 place-items-center rounded text-ink-3 transition hover:text-coral"
        >
          <Trash2 size={11} />
        </button>
      </div>
    </motion.article>
  );
}

function NewTaskForm({
  modules,
  onCreated,
  onError,
}: {
  modules: Array<{ id: string; short: string }>;
  onCreated: (t: Task) => void;
  onError: (msg: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [moduleId, setModuleId] = useState(modules[0]?.id ?? "");
  const [districtId, setDistrictId] = useState(DISTRICTS[0].id);
  const [deadline, setDeadline] = useState("2026-12-31");
  const [assignee, setAssignee] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || busy) return;
    setBusy(true);
    try {
      const task = await createTask({
        title: title.trim(),
        description: description.trim() || undefined,
        district_id: districtId,
        module_id: moduleId,
        deadline,
        assignee: assignee.trim() || "Belgilenbegen",
        progress: 0,
      });
      onCreated(task);
      setTitle("");
      setAssignee("");
      setDescription("");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Tapsırma jaratılmadı");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="glass space-y-3.5 rounded-2xl p-4">
      <Field label="Tapsırma atı">
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Oń jaǵa rayonlarında tamshılatıp suwǵarıwdı 20% ke asırıw"
          required
        />
      </Field>

      <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Taraw">
          <Select value={moduleId} onChange={(e) => setModuleId(e.target.value)}>
            {modules.map((m) => (
              <option key={m.id} value={m.id}>
                {m.short}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Aymaq">
          <Select value={districtId} onChange={(e) => setDistrictId(e.target.value)}>
            {DISTRICTS.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Múddet">
          <Input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        </Field>
        <Field label="Juwapker">
          <Input
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            placeholder="A.Á.T."
          />
        </Field>
      </div>

      <Field label="Tákirarlaw">
        <Textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          placeholder="Tapsırma mazmunı hám kútilgen nátiyje"
        />
      </Field>

      <Button type="submit" disabled={busy}>
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
        Tapsırma jaratıw
      </Button>
    </form>
  );
}
