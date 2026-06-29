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

export type DocumentStatus =
  | "pending"
  | "uploaded"
  | "queued"
  | "processing"
  | "ready"
  | "failed";

export type DocumentRecord = {
  id: string;
  workspace_id: string;
  uploaded_by_id: string;
  display_name: string;
  original_filename: string;
  file_extension: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  status: DocumentStatus;
  status_message: string | null;
  processing_attempts: number;
  storage_provider: string | null;
  storage_bucket: string | null;
  storage_key: string | null;
  document_metadata: Record<string, unknown>;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ProcessingJobStatus =
  | "queued"
  | "processing"
  | "retrying"
  | "succeeded"
  | "failed";

export type DocumentProcessingJob = {
  id: string;
  document_id: string;
  requested_by_id: string;
  celery_task_id: string | null;
  job_type: string;
  status: ProcessingJobStatus;
  attempts: number;
  max_attempts: number;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  last_error: string | null;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type DocumentProcessingJobListResponse = {
  items: DocumentProcessingJob[];
};

export type DocumentListResponse = {
  items: DocumentRecord[];
  total: number;
  limit: number;
  offset: number;
};

type ValidationDetail = Array<{ msg?: string }>;
type StructuredDetail = { message?: string; document_id?: string | null };

type ErrorPayload = {
  detail?: string | ValidationDetail | StructuredDetail;
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

  if (payload?.detail && typeof payload.detail === "object") {
    const structuredDetail = payload.detail as StructuredDetail;
    if (structuredDetail.message) {
      return structuredDetail.message;
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
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  if (options.body && !isFormData && !headers.has("Content-Type")) {
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

export async function listDocuments(
  workspaceId: string,
  options: { limit?: number; offset?: number; status?: DocumentStatus } = {},
): Promise<DocumentListResponse> {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 25),
    offset: String(options.offset ?? 0),
  });

  if (options.status) {
    params.set("status", options.status);
  }

  return apiRequest<DocumentListResponse>(
    `/api/v1/workspaces/${workspaceId}/documents?${params.toString()}`,
  );
}

export async function uploadDocument(
  workspaceId: string,
  file: File,
): Promise<DocumentRecord> {
  const body = new FormData();
  body.append("file", file);

  return apiRequest<DocumentRecord>(
    `/api/v1/workspaces/${workspaceId}/documents`,
    {
      method: "POST",
      body,
    },
    true,
  );
}


export async function retryDocumentProcessing(
  workspaceId: string,
  documentId: string,
): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/retry`,
    { method: "POST" },
    true,
  );
}

export async function listDocumentProcessingJobs(
  workspaceId: string,
  documentId: string,
): Promise<DocumentProcessingJobListResponse> {
  return apiRequest<DocumentProcessingJobListResponse>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/jobs`,
  );
}
