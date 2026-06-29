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
  parser_name: string | null;
  parser_version: string | null;
  parsed_at: string | null;
  page_count: number;
  section_count: number;
  table_count: number;
  extracted_text_chars: number;
  chunker_name: string | null;
  chunker_version: string | null;
  chunked_at: string | null;
  chunk_count: number;
  chunk_token_estimate: number;
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

export type DocumentPage = {
  id: string;
  page_number: number;
  text_content: string;
  char_count: number;
  word_count: number;
  page_metadata: Record<string, unknown>;
};

export type DocumentSection = {
  id: string;
  ordinal: number;
  title: string | null;
  heading_level: number | null;
  section_path: string[];
  content: string;
  page_start: number | null;
  page_end: number | null;
  char_count: number;
  word_count: number;
  section_metadata: Record<string, unknown>;
};

export type DocumentTable = {
  id: string;
  section_id: string | null;
  ordinal: number;
  title: string | null;
  source_label: string | null;
  page_number: number | null;
  column_names: string[];
  rows: string[][];
  row_count: number;
  column_count: number;
  is_truncated: boolean;
  table_metadata: Record<string, unknown>;
};

export type DocumentContentResponse = {
  document: DocumentRecord;
  pages: DocumentPage[];
  sections: DocumentSection[];
  tables: DocumentTable[];
  returned_page_count: number;
  returned_section_count: number;
  returned_table_count: number;
  table_row_limit: number;
};

export type ChunkSourceType = "section" | "page" | "table";

export type DocumentChunk = {
  id: string;
  document_id: string;
  section_id: string | null;
  table_id: string | null;
  ordinal: number;
  source_type: ChunkSourceType;
  source_label: string | null;
  heading_path: string[];
  page_start: number | null;
  page_end: number | null;
  content: string;
  char_count: number;
  word_count: number;
  token_estimate: number;
  overlap_chars: number;
  fingerprint: string;
  chunk_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type DocumentChunkListResponse = {
  items: DocumentChunk[];
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
const CSRF_COOKIE_NAME =
  process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? "veriflow_csrf";

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
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  if (options.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (requireCsrf) {
    const csrfToken = readCookie(CSRF_COOKIE_NAME);

    if (!csrfToken) {
      throw new ApiError(
        "Your secure session is missing a CSRF token. Sign in again.",
        403,
      );
    }

    headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
    cache: "no-store",
  });

  const hasJson = response.headers
    .get("content-type")
    ?.includes("application/json");
  const payload = hasJson
    ? ((await response.json()) as T | ErrorPayload)
    : null;

  if (!response.ok) {
    throw new ApiError(
      errorMessage(payload as ErrorPayload | null, response.status),
      response.status,
    );
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

export async function getDocument(
  workspaceId: string,
  documentId: string,
): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}`,
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

export async function getDocumentContent(
  workspaceId: string,
  documentId: string,
  options: {
    pageLimit?: number;
    sectionLimit?: number;
    tableLimit?: number;
    tableRowLimit?: number;
  } = {},
): Promise<DocumentContentResponse> {
  const params = new URLSearchParams({
    page_limit: String(options.pageLimit ?? 200),
    section_limit: String(options.sectionLimit ?? 200),
    table_limit: String(options.tableLimit ?? 100),
    table_row_limit: String(options.tableRowLimit ?? 50),
  });

  return apiRequest<DocumentContentResponse>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/content?${params.toString()}`,
  );
}

export async function listDocumentChunks(
  workspaceId: string,
  documentId: string,
  options: {
    limit?: number;
    offset?: number;
    sourceType?: ChunkSourceType;
  } = {},
): Promise<DocumentChunkListResponse> {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 500),
    offset: String(options.offset ?? 0),
  });

  if (options.sourceType) {
    params.set("source_type", options.sourceType);
  }

  return apiRequest<DocumentChunkListResponse>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/chunks?${params.toString()}`,
  );
}

export async function queueStructuredIngestion(
  workspaceId: string,
  documentId: string,
): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(
    `/api/v1/workspaces/${workspaceId}/documents/${documentId}/ingest`,
    { method: "POST" },
    true,
  );
}
