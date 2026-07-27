"use client";

import { Fragment, type ReactNode } from "react";

/**
 * Yengil markdown: **qalin**, _kursiv_, `kod`, ro'yxatlar, sarlavhalar.
 * Tashqi kutubxona olib kelmasdan chat javoblarini formatlash uchun yetarli.
 */

function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;

  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const key = `${keyBase}-${i++}`;
    if (tok.startsWith("**")) {
      out.push(
        <strong key={key} className="font-semibold text-ink">
          {tok.slice(2, -2)}
        </strong>,
      );
    } else if (tok.startsWith("`")) {
      out.push(
        <code key={key} className="rounded bg-abyss/80 px-1 py-0.5 font-mono text-[11px] text-cyan">
          {tok.slice(1, -1)}
        </code>,
      );
    } else {
      out.push(
        <em key={key} className="text-ink-2 italic">
          {tok.slice(1, -1)}
        </em>,
      );
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let list: string[] = [];

  const flushList = (key: string) => {
    if (!list.length) return;
    blocks.push(
      <ul key={key} className="my-1.5 space-y-1 pl-1">
        {list.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span className="mt-[7px] size-1 shrink-0 rounded-full bg-cyan" />
            <span className="flex-1">{inline(item, `${key}-${i}`)}</span>
          </li>
        ))}
      </ul>,
    );
    list = [];
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    const key = `b-${idx}`;

    if (/^\s*[-–]\s+/.test(line)) {
      list.push(line.replace(/^\s*[-–]\s+/, ""));
      return;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      list.push(line.replace(/^\s*\d+\.\s+/, ""));
      return;
    }
    flushList(`${key}-list`);

    if (!line.trim()) {
      blocks.push(<div key={key} className="h-2" />);
      return;
    }
    if (/^\s{2,}↳/.test(raw)) {
      blocks.push(
        <div key={key} className="mt-0.5 mb-1 border-l-2 border-edge/60 pl-2.5 text-[11.5px] text-ink-3">
          {inline(line.replace(/^\s*↳\s*/, ""), key)}
        </div>,
      );
      return;
    }
    blocks.push(
      <p key={key} className="leading-relaxed">
        {inline(line, key)}
      </p>,
    );
  });
  flushList("b-final-list");

  return <div className="space-y-0.5 text-[12.5px] text-ink-2">{blocks.map((b, i) => (
    <Fragment key={i}>{b}</Fragment>
  ))}</div>;
}
