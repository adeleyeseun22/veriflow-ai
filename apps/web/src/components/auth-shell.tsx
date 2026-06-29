import type { ReactNode } from "react";

import { Brand } from "@/components/brand";

import styles from "./auth-shell.module.css";

export function AuthShell({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className={styles.page}>
      <section className={styles.contextPanel}>
        <div className={styles.brandRow}>
          <Brand />
          <span className={styles.securityBadge}>Evidence-first workspace</span>
        </div>

        <div className={styles.contextCopy}>
          <p className={styles.eyebrow}>Defensible intelligence</p>
          <h1>Build decisions on evidence, not assumptions.</h1>
          <p>
            Organize documents, structured records, findings, and reviewer decisions inside one
            traceable operating environment.
          </p>
        </div>

        <div className={styles.proofGrid}>
          <article>
            <span>01</span>
            <strong>Source-linked</strong>
            <p>Every material output is designed to remain connected to its evidence.</p>
          </article>
          <article>
            <span>02</span>
            <strong>Reviewable</strong>
            <p>Human approval and audit history are part of the workflow from day one.</p>
          </article>
        </div>
      </section>

      <section className={styles.formPanel}>
        <div className={styles.mobileBrand}>
          <Brand />
        </div>

        <div className={styles.formCard}>
          <div className={styles.formHeading}>
            <p>{eyebrow}</p>
            <h2>{title}</h2>
            <span>{description}</span>
          </div>
          {children}
        </div>
      </section>
    </div>
  );
}
