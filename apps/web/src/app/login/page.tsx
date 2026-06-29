"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AuthShell } from "@/components/auth-shell";
import { useAuth } from "@/hooks/use-auth";
import { loginAccount } from "@/lib/api";

import styles from "@/components/auth-form.module.css";

export default function LoginPage() {
  const router = useRouter();
  const auth = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (auth.status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [auth.status, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await loginAccount({ email, password });
      router.replace("/dashboard");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Welcome back"
      title="Sign in to VeriFlow"
      description="Continue to your evidence workspace and review activity."
    >
      {auth.status === "loading" || auth.status === "authenticated" ? (
        <div className={styles.loading}>Checking your secure session…</div>
      ) : (
        <form className={styles.form} onSubmit={submit}>
          <div className={styles.field}>
            <label htmlFor="email">Email address</label>
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
              autoComplete="current-password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {(error || auth.message) && <p className={styles.error}>{error ?? auth.message}</p>}

          <button className={styles.submit} type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in securely"}
          </button>

          <p className={styles.footerCopy}>
            New to VeriFlow? <Link href="/register">Create an account</Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}
