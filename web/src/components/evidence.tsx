import * as Dialog from "@radix-ui/react-dialog";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import type { Source } from "../api/client";

type Open = (source: Source, label: string) => void;
const Ctx = createContext<Open>(() => undefined);
export const useEvidence = () => useContext(Ctx);

/** Evidence drawer: source file, producer, label, mode, modified time, SHA-256 and the command that regenerates it. */
export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [item, setItem] = useState<{ source: Source; label: string } | null>(null);
  const open = useCallback<Open>((source, label) => setItem({ source, label }), []);
  return (
    <Ctx.Provider value={open}>
      {children}
      <Dialog.Root open={item !== null} onOpenChange={(o) => !o && setItem(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
          <Dialog.Content
            className="glass glass-overlay fixed top-4 right-4 bottom-4 z-50 w-[min(440px,92vw)] overflow-auto p-5"
            aria-describedby={undefined}
          >
            <Dialog.Title className="mt-0 text-xl font-semibold">Evidence: {item?.label}</Dialog.Title>
            {item && (
              <table className="dtable">
                <tbody>
                  {(
                    [
                      ["File", item.source.file],
                      ["Producer", item.source.producer],
                      ["Label", item.source.label],
                      ["Data mode", item.source.mode ?? "LIVE"],
                      ["Modified", item.source.modified ?? "n/a"],
                      ["SHA-256", item.source.sha256 ?? "file missing"],
                      ["Regenerate with", item.source.command],
                    ] as const
                  ).map(([k, v]) => (
                    <tr key={k}>
                      <th scope="row">{k}</th>
                      <td>
                        <code className="break-all">{v}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <Dialog.Close className="btn mt-4">Close (Esc)</Dialog.Close>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </Ctx.Provider>
  );
}
