"use client";

import { AnimatePresence, motion } from "motion/react";
import { CalendarClock, Plus, User, X } from "lucide-react";
import { useMemo, useState } from "react";
import { CURRENT_YEAR, TASKS } from "@/data/dataset";
import { DISTRICTS, DISTRICT_BY_ID } from "@/data/districts";
import { MODULES, MODULE_BY_ID, STATUS_BY_ID } from "@/data/modules";
import type { EconomicTask, ModuleId, StatusId } from "@/lib/types";
import { cn, daysLeft, formatDate, trim, uid } from "@/lib/utils";
import { Button, Field, Input, Meter, Segmented, Select, StatusPill, Textarea } from "@/components/ui/primitives";

/** Iqtisodiy topshiriqlar va loyihalar boshqaruvi. */
export function TaskBoard() {
  const [tasks, setTasks] = useState<EconomicTask[]>(TASKS);
  const [filter, setFilter] = useState<StatusId | "all">("all");
  const [creating, setCreating] = useState(false);

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

  return (
    <div className="space-y-3.5">
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
        <Button type="button" onClick={() => setCreating((v) => !v)} variant={creating ? "outline" : "solid"}>
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
              onCreate={(t) => {
                setTasks((prev) => [t, ...prev]);
                setCreating(false);
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-3">
        <AnimatePresence mode="popLayout">
          {visible.map((t, i) => (
            <TaskCard
              key={t.id}
              task={t}
              index={i}
              onProgress={(p) =>
                setTasks((prev) =>
                  prev.map((x) =>
                    x.id === t.id
                      ? {
                          ...x,
                          progress: p,
                          status:
                            p >= 100
                              ? "completed"
                              : p >= 60
                                ? "in_progress"
                                : p >= 30
                                  ? "at_risk"
                                  : "critical",
                        }
                      : x,
                  ),
                )
              }
            />
          ))}
        </AnimatePresence>
      </div>

      {visible.length === 0 && (
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
  onProgress,
}: {
  task: EconomicTask;
  index: number;
  onProgress: (p: number) => void;
}) {
  const m = MODULE_BY_ID[task.moduleId];
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
        <span className="mt-1 size-2 shrink-0 rounded-full" style={{ background: m.color }} />
        <h3 className="min-w-0 flex-1 text-[12.5px] leading-snug font-semibold text-ink">
          {task.title}
        </h3>
        <StatusPill status={task.status} />
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10.5px] text-ink-3">
        <span>{DISTRICT_BY_ID[task.districtId]?.name}</span>
        <span>·</span>
        <span>{m.short}</span>
      </div>

      <div>
        <div className="mb-1.5 flex items-baseline justify-between">
          <span className="text-[10.5px] text-ink-3">Orınlanıwı</span>
          <span className="tnum text-[11.5px] font-semibold text-ink">{trim(task.progress, 0)}%</span>
        </div>
        <Meter value={task.progress / 100} color={STATUS_BY_ID[task.status].color} />
        <input
          type="range"
          min={0}
          max={100}
          value={task.progress}
          onChange={(e) => onProgress(Number(e.target.value))}
          className="mt-2 w-full accent-cyan"
          aria-label={`${task.title} orınlanıw procenti`}
        />
      </div>

      <div className="flex items-center gap-2 border-t border-hairline/60 pt-2.5 text-[10.5px]">
        <User size={11} className="shrink-0 text-ink-3" />
        <span className="min-w-0 flex-1 truncate text-ink-2">{task.assignee}</span>
        <CalendarClock size={11} className={cn("shrink-0", overdue ? "text-crimson" : "text-ink-3")} />
        <span className={cn("tnum", overdue ? "font-semibold text-crimson" : "text-ink-2")}>
          {formatDate(task.deadline)}
          {overdue ? ` (${Math.abs(left)} kún keshikti)` : ""}
        </span>
      </div>
    </motion.article>
  );
}

function NewTaskForm({ onCreate }: { onCreate: (t: EconomicTask) => void }) {
  const [title, setTitle] = useState("");
  const [moduleId, setModuleId] = useState<ModuleId>("agriculture");
  const [districtId, setDistrictId] = useState(DISTRICTS[0].id);
  const [deadline, setDeadline] = useState(`${CURRENT_YEAR}-12-31`);
  const [assignee, setAssignee] = useState("");
  const [description, setDescription] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!title.trim()) return;
        onCreate({
          id: uid("task"),
          title: title.trim(),
          moduleId,
          districtId,
          status: "in_progress",
          progress: 0,
          deadline,
          assignee: assignee.trim() || "Belgilenbegen",
          description: description.trim() || undefined,
          createdAt: "2026-07-27",
        });
      }}
      className="glass space-y-3.5 rounded-2xl p-4"
    >
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
          <Select value={moduleId} onChange={(e) => setModuleId(e.target.value as ModuleId)}>
            {MODULES.map((m) => (
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

      <Button type="submit">
        <Plus size={14} />
        Tapsırma jaratıw
      </Button>
    </form>
  );
}
