"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AuthShell } from "@/components/auth-shell";
import { useAuth } from "@/hooks/use-auth";
import { registerAccount } from "@/lib/api";

import styles from "@/components/auth-form.module.css";

export default function RegisterPage() {
  const router = useRouter();
  const auth = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (auth.status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [auth.status, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }

    setSubmitting(true);

    try {
      await registerAccount({ full_name: fullName, email, password });
      router.replace("/onboarding");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to create account.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Create your account"
      title="Start an evidence workspace"
      description="Create a secure identity, then establish your first organization and workspace."
    >
      {auth.status === "loading" || auth.status === "authenticated" ? (
        <div className={styles.loading}>Checking your secure session…</div>
      ) : (
        <form className={styles.form} onSubmit={submit}>
          <div className={styles.field}>
            <label htmlFor="full-name">Full name</label>
            <input
              id="full-name"
              name="full-name"
              type="text"
              autoComplete="name"
              placeholder="Your full name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              minLength={2}
              required
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="email">Work email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              placeholder="Create a secure password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={12}
              required
            />
          </div>

          <p className={styles.passwordHint}>Use at least 12 characters.</p>

          <div className={styles.field}>
            <label htmlFor="confirm-password">Confirm password</label>
            <input
              id="confirm-password"
              name="confirm-password"
              type="password"
              autoComplete="new-password"
              placeholder="Repeat your password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              minLength={12}
              required
            />
          </div>

          {(error || auth.message) && <p className={styles.error}>{error ?? auth.message}</p>}

          <button className={styles.submit} type="submit" disabled={submitting}>
            {submitting ? "Creating account…" : "Create secure account"}
          </button>

          <p className={styles.footerCopy}>
            Already registered? <Link href="/login">Sign in</Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}
