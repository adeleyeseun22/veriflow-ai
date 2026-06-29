"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, getCurrentUser, type User } from "@/lib/api";

type AuthState =
  | { status: "loading"; user: null; message: null }
  | { status: "authenticated"; user: User; message: null }
  | { status: "unauthenticated"; user: null; message: null }
  | { status: "error"; user: null; message: string };

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    status: "loading",
    user: null,
    message: null,
  });

  const refresh = useCallback(async () => {
    setState({ status: "loading", user: null, message: null });

    try {
      const user = await getCurrentUser();
      setState({ status: "authenticated", user, message: null });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setState({ status: "unauthenticated", user: null, message: null });
        return;
      }

      setState({
        status: "error",
        user: null,
        message: error instanceof Error ? error.message : "Unable to verify your session.",
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { ...state, refresh };
}
