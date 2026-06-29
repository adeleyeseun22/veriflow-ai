"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { Brand } from "@/components/brand";
import { logoutAccount, type User, type Workspace } from "@/lib/api";

import styles from "./app-shell.module.css";

export function AppShell({
  user,
  workspaces,
  activeWorkspaceId,
  onWorkspaceChange,
  children,
}: {
  user: User;
  workspaces: Workspace[];
  activeWorkspaceId: string;
  onWorkspaceChange: (workspaceId: string) => void;
  children: ReactNode;
}) {
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);
  const initials = user.full_name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  async function logout() {
    setLoggingOut(true);

    try {
      await logoutAccount();
      localStorage.removeItem("veriflow_active_workspace");
      router.replace("/login");
      router.refresh();
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarTop}>
          <Brand />

          <nav className={styles.navigation} aria-label="Application navigation">
            <Link className={styles.activeLink} href="/dashboard">
              <span>⌂</span>
              Overview
            </Link>
            <button type="button" disabled>
              <span>□</span>
              Documents
              <small>Phase 2</small>
            </button>
            <button type="button" disabled>
              <span>⌕</span>
              Ask VeriFlow
              <small>Phase 5</small>
            </button>
            <button type="button" disabled>
              <span>✓</span>
              Evidence review
              <small>Phase 6</small>
            </button>
            <button type="button" disabled>
              <span>↯</span>
              Contradictions
              <small>Phase 8</small>
            </button>
          </nav>
        </div>

        <div className={styles.sidebarFooter}>
          <div className={styles.identity}>
            <span>{initials}</span>
            <div>
              <strong>{user.full_name}</strong>
              <small>{user.email}</small>
            </div>
          </div>
          <button type="button" onClick={logout} disabled={loggingOut}>
            {loggingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </aside>

      <div className={styles.workspaceArea}>
        <header className={styles.topbar}>
          <div>
            <span>Active workspace</span>
            <select
              aria-label="Active workspace"
              value={activeWorkspaceId}
              onChange={(event) => onWorkspaceChange(event.target.value)}
            >
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.organization_name} · {workspace.name}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.topbarActions}>
            <span className={styles.roleBadge}>
              {workspaces.find((workspace) => workspace.id === activeWorkspaceId)?.role ?? "member"}
            </span>
            <button type="button" disabled>
              Upload documents
            </button>
          </div>
        </header>

        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
