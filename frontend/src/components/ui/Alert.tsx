import type { ReactNode } from "react";

export function Alert({ children }: { children: ReactNode }) {
  return (
    <div role="alert" className="alert">
      {children}
    </div>
  );
}
