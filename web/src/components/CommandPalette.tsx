import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useMemo, useState } from "react";

export type Command = { id: string; label: string; hint?: string; run: () => void };

/** Ctrl+K / Cmd+K palette: pages and actions. Arrow keys move, Enter runs, Esc closes (focus trapped by Radix). */
export function CommandPalette({ commands }: { commands: Command[] }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const list = useMemo(
    () => commands.filter((c) => c.label.toLowerCase().includes(q.toLowerCase())).slice(0, 12),
    [commands, q],
  );
  const run = (c: Command | undefined) => {
    if (!c) return;
    setOpen(false);
    setQ("");
    c.run();
  };
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger className="btn whitespace-nowrap" aria-label="Ctrl K: open command palette">
        <span className="mono text-xs whitespace-nowrap">
          <span aria-hidden="true">⌕ </span>Ctrl K
        </span>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <Dialog.Content
          className="glass glass-overlay fixed top-[15vh] left-1/2 z-50 w-[min(560px,92vw)] -translate-x-1/2 p-4"
          aria-describedby={undefined}
        >
          <Dialog.Title className="sr-only">Command palette</Dialog.Title>
          <input
            autoFocus
            className="input w-full"
            placeholder="Go to page or run action…"
            value={q}
            aria-label="Search commands"
            onChange={(e) => {
              setQ(e.target.value);
              setSel(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") setSel((s) => Math.min(s + 1, list.length - 1));
              if (e.key === "ArrowUp") setSel((s) => Math.max(s - 1, 0));
              if (e.key === "Enter") run(list[sel]);
            }}
          />
          <ul role="listbox" aria-label="Commands" className="m-0 mt-3 list-none p-0">
            {list.map((c, i) => (
              <li key={c.id} role="option" aria-selected={i === sel}>
                <button
                  type="button"
                  className={`w-full cursor-pointer rounded-lg border-0 px-3 py-2 text-left text-inherit ${i === sel ? "bg-white/10" : "bg-transparent"}`}
                  onClick={() => run(c)}
                  onMouseEnter={() => setSel(i)}
                >
                  {c.label} {c.hint && <span className="t-muted text-sm">· {c.hint}</span>}
                </button>
              </li>
            ))}
            {list.length === 0 && <li className="t-muted p-2">No match.</li>}
          </ul>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
