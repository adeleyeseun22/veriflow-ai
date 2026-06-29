"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Brand } from "@/components/brand";
import { useAuth } from "@/hooks/use-auth";
import { createWorkspace, listWorkspaces } from "@/lib/api";

import styles from "./onboarding.module.css";

export default function OnboardingPage() {
  const router = useRouter();
  const auth = useAuth();
  const [organizationName, setOrganizationName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [checkingWorkspaces, setCheckingWorkspaces] = useState(true);

  useEffect(() => {
    if (auth.status === "unauthenticated") {
      router.replace("/login");
      return;
    }

    if (auth.status !== "authenticated") {
      return;
    }

    async function checkExistingWorkspaces() {
      try {
        const workspaces = await listWorkspaces();

        if (workspaces.length > 0) {
          localStorage.setItem("veriflow_active_workspace", workspaces[0].id);
          router.replace("/dashboard");
          return;
        }
      } catch (requestError) {
        setError(
          requestError instanceof Error ? requestError.message : "Unable to inspect workspaces.",
        );
      } finally {
        setCheckingWorkspaces(false);
      }
    }

    void checkExistingWorkspaces();
  }, [auth.status, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const workspace = await createWorkspace({
        organization_name: organizationName,
        name: workspaceName,
      });
      localStorage.setItem("veriflow_active_workspace", workspace.id);
      router.replace("/dashboard");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to create workspace.");
    } finally {
      setSubmitting(false);
    }
  }

  const loading = auth.status === "loading" || checkingWorkspaces;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Brand />
        <span>Secure workspace onboarding</span>
      </header>

      <div className={styles.content}>
        <section className={styles.intro}>
          <p className={styles.eyebrow}>Workspace foundation</p>
          <h1>Create the operating environment for your evidence.</h1>
          <p>
            Your organization contains one or more workspaces. Each workspace keeps its documents,
            evidence, reviews, findings, and audit history isolated.
          </p>

          <div className={styles.steps}>
            <article className={styles.activeStep}>
              <span>01</span>
              <div>
                <strong>Identity secured</strong>
                <p>Your account and encrypted session are active.</p>
              </div>
            </article>
            <article>
              <span>02</span>
              <div>
                <strong>Create workspace</strong>
                <p>Name your organization and first evidence workspace.</p>
              </div>
            </article>
            <article>
              <span>03</span>
              <div>
                <strong>Enter dashboard</strong>
                <p>Continue to the protected product environment.</p>
              </div>
            </article>
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.cardHeading}>
            <span>Step 2 of 3</span>
            <h2>Set up your first workspace</h2>
            <p>You will automatically become its owner.</p>
          </div>

          {loading ? (
            <div className={styles.loading}>Preparing your workspace…</div>
          ) : (
            <form className={styles.form} onSubmit={submit}>
              <div className={styles.field}>
                <label htmlFor="organization">Organization name</label>
                <input
                  id="organization"
                  type="text"
                  placeholder="Example: Northstar Advisory"
                  value={organizationName}
                  onChange={(event) => setOrganizationName(event.target.value)}
                  minLength={2}
                  required
                />
                <span>The company or team that owns this workspace.</span>
              </div>

              <div className={styles.field}>
                <label htmlFor="workspace">Workspace name</label>
                <input
                  id="workspace"
                  type="text"
                  placeholder="Example: Evidence Operations"
                  value={workspaceName}
                  onChange={(event) => setWorkspaceName(event.target.value)}
                  minLength={2}
                  required
                />
                <span>A focused environment for documents, findings, and decisions.</span>
              </div>

              {(error || auth.message) && <p className={styles.error}>{error ?? auth.message}</p>}

              <button type="submit" disabled={submitting}>
                {submitting ? "Creating workspace…" : "Create workspace and continue"}
              </button>
            </form>
          )}
        </section>
      </div>
    </div>
  );
}
