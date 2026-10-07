import type { ReactNode } from "react";

import { BackButton } from "./BackButton";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  children?: ReactNode;
}

export function PageHeader({
  title,
  subtitle,
  children,
}: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header-left">
        <BackButton />

        <div>
          <h1>{title}</h1>

          {subtitle && (
            <p className="page-subtitle">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {children && (
        <div className="page-header-actions">
          {children}
        </div>
      )}
    </header>
  );
}