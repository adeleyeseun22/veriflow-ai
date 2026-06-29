"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/hooks/use-auth";
import {
  listWorkspaceAuditLogs,
  listWorkspaces,
  type AuditLog,
  type Workspace,
} from "@/lib/api";

import styles from "./dashboard.module.css";

function formatAction(action: string): string {
  return action
    .split(".")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function DashboardPage() {
  const router = useRouter();
  const auth = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState("");
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (auth.status === "unauthenticated") {
      router.replace("/login");
      return;
    }

    if (auth.status !== "authenticated") {
      return;
    }

    async function loadWorkspaces() {
      try {
        const result = await listWorkspaces();

        if (result.length === 0) {
          router.replace("/onboarding");
          return;
        }

        const storedWorkspaceId = localStorage.getItem("veriflow_active_workspace");
        const selected = result.some((workspace) => workspace.id === storedWorkspaceId)
          ? storedWorkspaceId!
          : result[0].id;

        localStorage.setItem("veriflow_active_workspace", selected);
        setWorkspaces(result);
        setActiveWorkspaceId(selected);
      } catch (requestError) {
        setError(
          requestError instanceof Error ? requestError.message : "Unable to load workspaces.",
        );
      } finally {
        setLoadingWorkspace(false);
      }
    }

    void loadWorkspaces();
  }, [auth.status, router]);

  useEffect(() => {
    if (!activeWorkspaceId) {
      return;
    }

    async function loadAuditLogs() {
      try {
        const result = await listWorkspaceAuditLogs(activeWorkspaceId);
        setAuditLogs(result);
      } catch (requestError) {
        setError(
          requestError instanceof Error ? requestError.message : "Unable to load activity.",
        );
      }
    }

    void loadAuditLogs();
  }, [activeWorkspaceId]);

  const activeWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === activeWorkspaceId),
    [activeWorkspaceId, workspaces],
  );

  function changeWorkspace(workspaceId: string) {
    localStorage.setItem("veriflow_active_workspace", workspaceId);
    setActiveWorkspaceId(workspaceId);
    setAuditLogs([]);
  }

  if (auth.status === "loading" || loadingWorkspace || auth.status === "authenticated" && !activeWorkspace) {
    return <div className={styles.fullPageState}>Opening your secure workspace…</div>;
  }

  if (auth.status === "error") {
    return <div className={styles.fullPageState}>{auth.message}</div>;
  }

  if (auth.status !== "authenticated" || !activeWorkspace) {
    return <div className={styles.fullPageState}>Redirecting…</div>;
  }

  return (
    <AppShell
      user={auth.user}
      workspaces={workspaces}
      activeWorkspaceId={activeWorkspaceId}
      onWorkspaceChange={changeWorkspace}
    >
      <section className={styles.heroRow}>
        <div>
          <p className={styles.eyebrow}>Workspace overview</p>
          <h1>Good to have you here, {auth.user.full_name.split(" ")[0]}.</h1>
          <p>
            Your identity, workspace permissions, session security, and audit trail are active.
          </p>
        </div>
        <div className={styles.foundationStatus}>
          <span />
          Phase 1 foundation operational
        </div>
      </section>

      {error && <p className={styles.error}>{error}</p>}

      <section className={styles.metrics} aria-label="Workspace metrics">
        <article>
          <div>
            <span>Documents</span>
            <small>In this workspace</small>
          </div>
          <strong>0</strong>
          <p>Document ingestion begins in Phase 2.</p>
        </article>
        <article>
          <div>
            <span>Open findings</span>
            <small>Awaiting review</small>
          </div>
          <strong>0</strong>
          <p>Evidence findings will appear after processing.</p>
        </article>
        <article>
          <div>
            <span>Workspace role</span>
            <small>Current access</small>
          </div>
          <strong className={styles.roleMetric}>{activeWorkspace.role}</strong>
          <p>Role-based access control is enforced by FastAPI.</p>
        </article>
        <article>
          <div>
            <span>Security</span>
            <small>Session status</small>
          </div>
          <strong className={styles.secureMetric}>Secure</strong>
          <p>Redis session, HTTP-only cookie, and CSRF protection.</p>
        </article>
      </section>

      <section className={styles.workspaceGrid}>
        <article className={styles.workspaceCard}>
          <div className={styles.cardHeading}>
            <div>
              <p className={styles.eyebrow}>Active workspace</p>
              <h2>{activeWorkspace.name}</h2>
            </div>
            <span>{activeWorkspace.role}</span>
          </div>

          <dl className={styles.workspaceDetails}>
            <div>
              <dt>Organization</dt>
              <dd>{activeWorkspace.organization_name}</dd>
            </div>
            <div>
              <dt>Workspace slug</dt>
              <dd>{activeWorkspace.slug}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{formatDate(activeWorkspace.created_at)}</dd>
            </div>
            <div>
              <dt>Workspace ID</dt>
              <dd>{activeWorkspace.id.slice(0, 8)}…</dd>
            </div>
          </dl>

          <div className={styles.nextMilestone}>
            <span>Next milestone</span>
            <strong>Document upload and storage</strong>
            <p>
              Phase 2 will introduce validated uploads, object storage, background processing, and
              document status tracking.
            </p>
          </div>
        </article>

        <article className={styles.activityCard}>
          <div className={styles.cardHeading}>
            <div>
              <p className={styles.eyebrow}>Audit trail</p>
              <h2>Recent activity</h2>
            </div>
            <span>{auditLogs.length} events</span>
          </div>

          <div className={styles.activityList}>
            {auditLogs.length === 0 ? (
              <div className={styles.emptyActivity}>No workspace activity is available yet.</div>
            ) : (
              auditLogs.map((log) => (
                <div className={styles.activityItem} key={log.id}>
                  <span className={styles.activityDot} />
                  <div>
                    <strong>{formatAction(log.action)}</strong>
                    <p>{log.resource_type}</p>
                  </div>
                  <time dateTime={log.created_at}>{formatDate(log.created_at)}</time>
                </div>
              ))
            )}
          </div>
        </article>
      </section>
    </AppShell>
  );
}
