"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, getCurrentUser, type User } from "@/lib/api";

type AuthState =
  | { status: "loading"; user: null; message: null }
  | { status: "authenticated"; user: User; message: null }
  | { status: "unauthenticated"; user: null; message: null }
  | { status: "error"; user: null; message: string };

const loadingState: AuthState = {
  status: "loading",
  user: null,
  message: null,
};

async function resolveAuthState(): Promise<AuthState> {
  try {
    const user = await getCurrentUser();

    return {
      status: "authenticated",
      user,
      message: null,
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return {
        status: "unauthenticated",
        user: null,
        message: null,
      };
    }

    return {
      status: "error",
      user: null,
      message:
        error instanceof Error
          ? error.message
          : "Unable to verify your session.",
    };
  }
}

export function useAuth() {
  const [state, setState] = useState<AuthState>(loadingState);

  const refresh = useCallback(async () => {
    setState(loadingState);

    const nextState = await resolveAuthState();
    setState(nextState);
  }, []);

  useEffect(() => {
    let cancelled = false;

    void resolveAuthState().then((nextState) => {
      if (!cancelled) {
        setState(nextState);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    ...state,
    refresh,
  };
}