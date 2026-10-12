import { Dropdown } from "./Dropdown";
import { Segmented } from "./Segmented";
import { Switch } from "./Switch";
import {
  COMPARE_META,
  COMPARE_ORDER,
  METRIC_LABEL,
  type RawFilters,
  type Resolved,
} from "../utils/analysisModel";
import type { CompareType, Metric, Scope } from "../types/dataset";

interface FilterBarProps {
  resolved: Resolved;
  regions: string[];
  onChange: (patch: RawFilters) => void;
}

interface GroupProps {
  step: number;
  label: string;
  children: React.ReactNode;
  className?: string;
}

function Group({ step, label, children, className }: GroupProps) {
  return (
    <div className={className}>
      <div className="fl">
        <span className="n">{step}</span>
        {label}
      </div>
      {children}
    </div>
  );
}

export function FilterBar({ resolved, regions, onChange }: FilterBarProps) {
  const { state } = resolved;
  const isRegion = state.scope === "region";
  let step = 0;

  const unavailable = state.allProjects
    ? []
    : COMPARE_ORDER.filter((type) => !resolved.compareAvailable[type]).map(
        (type) => COMPARE_META[type].unavailable,
      );

  return (
    <>
      <div className="card filterbar">
        <Group step={++step} label="Metric">
          <Segmented<Metric>
            ariaLabel="Metric"
            value={state.metric}
            onChange={(metric) => onChange({ metric })}
            items={(["revenue", "cost"] as Metric[]).map((metric) => ({
              value: metric,
              label: METRIC_LABEL[metric],
              disabled: !resolved.metricAvailable[metric],
              tooltip: resolved.reasons.metric[metric],
            }))}
          />
        </Group>

        <Group step={++step} label="Analyze by">
          <Segmented<Scope>
            ariaLabel="Analyze by"
            value={state.scope}
            onChange={(scope) => onChange({ scope })}
            items={[
              { value: "project", label: "Project-wise" },
              {
                value: "region",
                label: "Region-wise",
                disabled: !resolved.scopeAvailable.region,
                tooltip: resolved.reasons.region,
              },
            ]}
          />
        </Group>

        {isRegion && (
          <Group step={++step} label="Region">
            <Dropdown
              ariaLabel="Region"
              value={state.region ?? "Select"}
              selectedId={state.region}
              items={regions.map((region) => ({ id: region, label: region }))}
              searchable={regions.length > 8}
              minWidth={96}
              onSelect={(region) => onChange({ region })}
            />
          </Group>
        )}

        {!state.allProjects && (
          <Group step={++step} label="Compare">
            <Segmented<CompareType>
              ariaLabel="Compare"
              value={state.compare}
              onChange={(compare) => onChange({ compare, period: null })}
              items={COMPARE_ORDER.map((type) => ({
                value: type,
                label: COMPARE_META[type].short,
                disabled: !resolved.compareAvailable[type],
                tooltip: COMPARE_META[type].unavailable,
              }))}
            />
          </Group>
        )}

        <Group step={++step} label="All Projects">
          <Switch
            ariaLabel="All Projects: show monthly totals for every project"
            label="Monthly totals"
            checked={state.allProjects}
            disabled={!resolved.allProjectsAvailable || resolved.allProjectsForced}
            tooltip={
              resolved.allProjectsForced
                ? "Only monthly totals are available: this data has no complete month, quarter or year to compare."
                : resolved.reasons.allProjects
            }
            onChange={(checked) => onChange({ all: checked ? "1" : "0" })}
          />
        </Group>

        {!state.allProjects && (
          <Group step={++step} label="Periods" className="filter-periods">
            {state.compare === "mom" ? (
              // Month-on-Month always compares one fixed set of months.
              <div className="period-static" aria-label="Periods">
                {resolved.option?.label ?? "Not available"}
              </div>
            ) : (
              <Dropdown
                ariaLabel="Periods"
                value={resolved.option?.label ?? "Select"}
                selectedId={state.periodId}
                items={resolved.options.map((option) => ({
                  id: option.id,
                  label: option.label,
                }))}
                footnote={COMPARE_META[state.compare].footnote}
                minWidth={220}
                align="right"
                onSelect={(period) => onChange({ period })}
              />
            )}
          </Group>
        )}
      </div>

      {unavailable.length > 0 && (
        <p className="filter-note">{unavailable.join(" ")}</p>
      )}
    </>
  );
}