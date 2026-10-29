import * as React from "react";
import { useApi } from "../api/client";
import { Async, Code } from "./ui";

/** Side drawer showing a real repository file, scrolled to and highlighting one line. */
export function FileViewer({ repo, path, line, onClose }: { repo: string; path: string; line: number; onClose: () => void }) {
  const res = useApi<{ path: string; text: string }>(`/api/repositories/${repo}/file?path=${encodeURIComponent(path)}`);
  const body = React.useRef<HTMLDivElement>(null);
  const close = React.useRef<HTMLButtonElement>(null);
  React.useEffect(() => {
    close.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  React.useEffect(() => {
    body.current?.querySelector(".code-hit")?.scrollIntoView({ block: "center" });
  }, [res.data]);
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer" role="dialog" aria-modal="true" aria-label={`${path} line ${line}`}>
        <div className="drawer-head">
          <div>
            <strong className="mono">{path}</strong> <span className="muted small">line {line} · working copy of {repo}</span>
          </div>
          <button ref={close} className="btn" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="drawer-body" ref={body}>
          <Async res={res}>{(file) => <Code lines={file.text.split(/\r?\n/).map((text, i) => ({ line: i + 1, text }))} highlight={line} />}</Async>
        </div>
      </div>
    </>
  );
}
