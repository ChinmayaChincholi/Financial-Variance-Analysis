import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

export interface DropdownItem {
  id: string;
  label: string;
}

interface DropdownProps {
  ariaLabel: string;
  value: string;
  items: DropdownItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  footnote?: string;
  searchable?: boolean;
  minWidth?: number;
  align?: "left" | "right";
  disabled?: boolean;
}

export function Dropdown({
  ariaLabel,
  value,
  items,
  selectedId,
  onSelect,
  footnote,
  searchable = false,
  minWidth = 160,
  align = "left",
  disabled = false,
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle
      ? items.filter((item) => item.label.toLowerCase().includes(needle))
      : items;
  }, [items, query]);

  function toggle() {
    setOpen((current) => !current);
    setQuery("");
  }

  return (
    <div className="dd" ref={rootRef}>
      <button
        type="button"
        className="ghost dd-button"
        style={{ minWidth }}
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        disabled={disabled}
        onClick={toggle}
      >
        <span>{value}</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>

      {open && (
        <div className={`menu ${align === "right" ? "menu-right" : ""}`}>
          {searchable && (
            <input
              className="menu-search"
              type="search"
              placeholder="Search"
              aria-label={`Search ${ariaLabel}`}
              value={query}
              autoFocus
              onChange={(event) => setQuery(event.target.value)}
            />
          )}
          <div className="menu-list" id={listId} role="listbox">
            {visible.map((item) => {
              const selected = item.id === selectedId;
              return (
                <button
                  key={item.id}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={`menu-item ${selected ? "cur" : ""}`}
                  onClick={() => {
                    setOpen(false);
                    onSelect(item.id);
                  }}
                >
                  <span>{item.label}</span>
                  {selected && <Check size={16} aria-hidden="true" />}
                </button>
              );
            })}
            {visible.length === 0 && (
              <div className="menu-empty">No matches.</div>
            )}
          </div>
          {footnote && <div className="menu-foot">{footnote}</div>}
        </div>
      )}
    </div>
  );
}