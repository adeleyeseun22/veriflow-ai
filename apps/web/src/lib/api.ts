export type ApiHealth = {
  status: "healthy" | "unhealthy";
  service: string;
  version: string;
  checks?: Record<string, "healthy" | "unhealthy">;
};

export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
};

export type AuthResponse = {
  user: User;
  expires_in_seconds: number;
};

export type WorkspaceRole = "owner" | "admin" | "member" | "reviewer";

export type Workspace = {
  id: string;
  organization_id: string;
  organization_name: string;
  name: string;
  slug: string;
  role: WorkspaceRole;
  created_at: string;
};

export type AuditLog = {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  actor_user_id: string | null;
  created_at: string;
};

type ErrorPayload = {
  detail?: string | Array<{ msg?: string }>;
  message?: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CSRF_COOKIE_NAME = process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? "veriflow_csrf";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith(prefix));

  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

function errorMessage(payload: ErrorPayload | null, status: number): string {
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail
      .map((item) => item.msg)
      .filter((message): message is string => Boolean(message));

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  if (payload?.message) {
    return payload.message;
  }

  return `Request failed with status ${status}.`;
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  requireCsrf = false,
): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (requireCsrf) {
    const csrfToken = readCookie(CSRF_COOKIE_NAME);

    if (!csrfToken) {
      throw new ApiError("Your secure session is missing a CSRF token. Sign in again.", 403);
    }

    headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
    cache: "no-store",
  });

  const hasJson = response.headers.get("content-type")?.includes("application/json");
  const payload = hasJson ? ((await response.json()) as T | ErrorPayload) : null;

  if (!response.ok) {
    throw new ApiError(errorMessage(payload as ErrorPayload | null, response.status), response.status);
  }

  return payload as T;
}

export async function getApiReadiness(): Promise<ApiHealth> {
  return apiRequest<ApiHealth>("/health/ready");
}

export async function registerAccount(input: {
  full_name: string;
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function loginAccount(input: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function logoutAccount(): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    "/api/v1/auth/logout",
    { method: "POST" },
    true,
  );
}

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/api/v1/auth/me");
}

export async function listWorkspaces(): Promise<Workspace[]> {
  return apiRequest<Workspace[]>("/api/v1/workspaces");
}

export async function createWorkspace(input: {
  organization_name: string;
  name: string;
}): Promise<Workspace> {
  return apiRequest<Workspace>(
    "/api/v1/workspaces",
    {
      method: "POST",
      body: JSON.stringify(input),
    },
    true,
  );
}

export async function listWorkspaceAuditLogs(
  workspaceId: string,
  limit = 8,
): Promise<AuditLog[]> {
  return apiRequest<AuditLog[]>(
    `/api/v1/workspaces/${workspaceId}/audit-logs?limit=${limit}`,
  );
}
