import { useEffect, useState } from "react";
import { IS_WEB } from "../config/appMode";
import { getDemoConfig, type DemoConfig } from "../services/api/demoApi";

/*
 * The web demo's limits (upload size, retention) are set on the server, so
 * the interface reads them once instead of hard-coding numbers that could
 * drift. Outside the web build this never touches the network.
 */

let cached: DemoConfig | null = null;
let pending: Promise<DemoConfig | null> | null = null;

/** The limits if they have already loaded, otherwise null. */
export function getCachedDemoConfig(): DemoConfig | null {
  return cached;
}

export function loadDemoConfig(): Promise<DemoConfig | null> {
  if (!IS_WEB) return Promise.resolve(null);
  if (cached) return Promise.resolve(cached);

  pending ??= getDemoConfig()
    .then((config) => {
      cached = config;
      return config;
    })
    // The limits are informational; a failure must never break the app.
    .catch(() => null)
    .finally(() => {
      pending = null;
    });

  return pending;
}

export function useDemoConfig(): DemoConfig | null {
  const [config, setConfig] = useState<DemoConfig | null>(cached);

  useEffect(() => {
    if (!IS_WEB || cached) return;
    let active = true;
    void loadDemoConfig().then((loaded) => {
      if (active) setConfig(loaded);
    });
    return () => {
      active = false;
    };
  }, []);

  return config;
}