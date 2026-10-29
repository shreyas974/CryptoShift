import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef, useState } from "react";

/** Sortable, filterable table with a sticky header; rows are virtualised above 60 rows. Cells render text only. */
export function DataTable<T>({
  data,
  columns,
  caption,
  height = 520,
  onRowClick,
}: {
  data: T[];
  columns: ColumnDef<T, unknown>[];
  caption: string;
  height?: number;
  onRowClick?: (row: T) => void;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [filter, setFilter] = useState("");
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table v8 is not React-Compiler compatible; this app does not use the React Compiler.
  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter: filter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });
  const rows = table.getRowModel().rows;
  const parent = useRef<HTMLDivElement>(null);
  const virtual = rows.length > 60;
  const v = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parent.current,
    estimateSize: () => 40,
    overscan: 12,
  });
  const items = virtual ? v.getVirtualItems() : rows.map((_, i) => ({ index: i, start: 0, key: i }));
  const first = items[0];
  const lastItem = items[items.length - 1];
  const padTop = virtual && first ? first.start : 0;
  const padBottom = virtual && lastItem ? v.getTotalSize() - lastItem.start - 40 : 0;
  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <label className="text-sm">
          <span className="sr-only">Filter {caption}</span>
          <input className="input" placeholder="Filter…" value={filter} onChange={(e) => setFilter(e.target.value)} />
        </label>
        <span className="t-muted text-sm" aria-live="polite">
          {rows.length} of {data.length} rows
        </span>
      </div>
      <div
        ref={parent}
        className="overflow-auto"
        style={{ maxHeight: height }}
        tabIndex={0}
        role="region"
        aria-label={`${caption} table`}
      >
        <table className="dtable">
          <caption className="sr-only">{caption}</caption>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => {
                  const dir = h.column.getIsSorted();
                  return (
                    <th
                      key={h.id}
                      scope="col"
                      aria-sort={dir === "asc" ? "ascending" : dir === "desc" ? "descending" : "none"}
                    >
                      <button
                        type="button"
                        className="cursor-pointer border-0 bg-transparent p-0 font-semibold text-inherit"
                        onClick={h.column.getToggleSortingHandler()}
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {dir === "asc" ? " ▲" : dir === "desc" ? " ▼" : ""}
                      </button>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {padTop > 0 && (
              <tr aria-hidden="true">
                <td style={{ height: padTop, padding: 0, border: 0 }} />
              </tr>
            )}
            {items.map((it) => {
              const row = rows[it.index];
              if (!row) return null;
              return (
                <tr
                  key={row.id}
                  className={onRowClick ? "cursor-pointer hover:bg-white/5" : undefined}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  onKeyDown={onRowClick ? (e) => e.key === "Enter" && onRowClick(row.original) : undefined}
                  tabIndex={onRowClick ? 0 : undefined}
                >
                  {row.getVisibleCells().map((c) => (
                    <td key={c.id}>{flexRender(c.column.columnDef.cell, c.getContext())}</td>
                  ))}
                </tr>
              );
            })}
            {padBottom > 0 && (
              <tr aria-hidden="true">
                <td style={{ height: padBottom, padding: 0, border: 0 }} />
              </tr>
            )}
          </tbody>
        </table>
        {rows.length === 0 && <p className="t-muted p-3">No rows match this filter.</p>}
      </div>
    </div>
  );
}
