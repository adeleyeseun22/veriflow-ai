"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/hooks/use-auth";
import {
  listDocuments,
  listWorkspaces,
  retryDocumentProcessing,
  uploadDocument,
  type DocumentRecord,
  type Workspace,
} from "@/lib/api";

import styles from "./documents.module.css";

const ACCEPTED_EXTENSIONS = ["pdf", "docx", "xlsx", "csv"];
const MAX_FILE_SIZE = 25 * 1024 * 1024;
const ACTIVE_STATUSES = new Set([
  "pending",
  "uploaded",
  "queued",
  "processing",
]);

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }

  const units = ["KB", "MB", "GB"];
  let size = value / 1024;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unitIndex]}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function fileExtension(filename: string): string {
  return filename.split(".").pop()?.toLowerCase() ?? "";
}

function validateSelectedFile(file: File): string | null {
  if (!ACCEPTED_EXTENSIONS.includes(fileExtension(file.name))) {
    return "Choose a PDF, DOCX, XLSX, or CSV file.";
  }

  if (file.size === 0) {
    return "The selected file is empty.";
  }

  if (file.size > MAX_FILE_SIZE) {
    return "The selected file exceeds the 25 MB limit.";
  }

  return null;
}

export default function DocumentsPage() {
  const router = useRouter();
  const auth = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState("");
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [retryingDocumentId, setRetryingDocumentId] = useState<
    string | null
  >(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (auth.status === "unauthenticated") {
      router.replace("/login");
      return;
    }

    if (auth.status !== "authenticated") {
      return;
    }

    let cancelled = false;

    void listWorkspaces()
      .then((result) => {
        if (cancelled) {
          return;
        }

        if (result.length === 0) {
          router.replace("/onboarding");
          return;
        }

        const storedWorkspaceId = localStorage.getItem(
          "veriflow_active_workspace",
        );
        const selectedWorkspaceId = result.some(
          (workspace) => workspace.id === storedWorkspaceId,
        )
          ? storedWorkspaceId!
          : result[0].id;

        localStorage.setItem(
          "veriflow_active_workspace",
          selectedWorkspaceId,
        );
        setLoadingDocuments(true);
        setWorkspaces(result);
        setActiveWorkspaceId(selectedWorkspaceId);
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load workspaces.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingWorkspace(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [auth.status, router]);

  const fetchWorkspaceDocuments = useCallback(
    (workspaceId: string) =>
      listDocuments(workspaceId, {
        limit: 100,
      }),
    [],
  );

  const refreshWorkspaceDocuments = useCallback(
    async (workspaceId: string, background = false) => {
      if (!background) {
        setLoadingDocuments(true);
      }

      try {
        const result = await fetchWorkspaceDocuments(workspaceId);

        setDocuments(result.items);
        setTotalDocuments(result.total);
      } catch (requestError) {
        if (!background) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load documents.",
          );
        }
      } finally {
        if (!background) {
          setLoadingDocuments(false);
        }
      }
    },
    [fetchWorkspaceDocuments],
  );

  useEffect(() => {
    if (!activeWorkspaceId) {
      return;
    }

    let cancelled = false;

    void fetchWorkspaceDocuments(activeWorkspaceId)
      .then((result) => {
        if (cancelled) {
          return;
        }

        setDocuments(result.items);
        setTotalDocuments(result.total);
      })
      .catch((requestError: unknown) => {
        if (cancelled) {
          return;
        }

        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to load documents.",
        );
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingDocuments(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId, fetchWorkspaceDocuments]);

  const hasActiveProcessing = documents.some((document) =>
    ACTIVE_STATUSES.has(document.status),
  );

  useEffect(() => {
    if (!activeWorkspaceId || !hasActiveProcessing) {
      return;
    }

    let cancelled = false;
    const interval = window.setInterval(() => {
      void fetchWorkspaceDocuments(activeWorkspaceId)
        .then((result) => {
          if (!cancelled) {
            setDocuments(result.items);
            setTotalDocuments(result.total);
          }
        })
        .catch(() => {
          // Preserve the current library during temporary polling failures.
        });
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [activeWorkspaceId, fetchWorkspaceDocuments, hasActiveProcessing]);

  const activeWorkspace = useMemo(
    () =>
      workspaces.find(
        (workspace) => workspace.id === activeWorkspaceId,
      ),
    [activeWorkspaceId, workspaces],
  );

  const canUpload = activeWorkspace
    ? activeWorkspace.role !== "reviewer"
    : false;

  function changeWorkspace(workspaceId: string) {
    localStorage.setItem("veriflow_active_workspace", workspaceId);
    setLoadingDocuments(true);
    setActiveWorkspaceId(workspaceId);
    setDocuments([]);
    setTotalDocuments(0);
    setSelectedFile(null);
    setSuccess(null);
    setError(null);
  }

  function chooseFile(file: File | null) {
    setSuccess(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const validationError = validateSelectedFile(file);

    if (validationError) {
      setSelectedFile(null);
      setError(validationError);
      return;
    }

    setError(null);
    setSelectedFile(file);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    chooseFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);

    if (canUpload) {
      chooseFile(event.dataTransfer.files?.[0] ?? null);
    }
  }

  async function submitUpload() {
    if (!selectedFile || !activeWorkspaceId || !canUpload) {
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const uploaded = await uploadDocument(
        activeWorkspaceId,
        selectedFile,
      );

      setSuccess(
        `${uploaded.original_filename} was queued for background verification.`,
      );
      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      await refreshWorkspaceDocuments(activeWorkspaceId);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Upload failed.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function retryProcessing(documentId: string) {
    if (!activeWorkspaceId) {
      return;
    }

    setRetryingDocumentId(documentId);
    setError(null);
    setSuccess(null);

    try {
      await retryDocumentProcessing(activeWorkspaceId, documentId);
      setSuccess(
        "The document was queued for another processing attempt.",
      );
      await refreshWorkspaceDocuments(activeWorkspaceId);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Retry failed.",
      );
    } finally {
      setRetryingDocumentId(null);
    }
  }

  if (
    auth.status === "loading" ||
    loadingWorkspace ||
    (auth.status === "authenticated" && !activeWorkspace)
  ) {
    return (
      <div className={styles.fullPageState}>
        Opening the document workspace…
      </div>
    );
  }

  if (auth.status === "error") {
    return <div className={styles.fullPageState}>{auth.message}</div>;
  }

  if (auth.status !== "authenticated" || !activeWorkspace) {
    return null;
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
          <p className={styles.eyebrow}>Evidence intake</p>
          <h1>
            Secure uploads with observable background processing.
          </h1>
          <p>
            Files are validated, stored privately, parsed, chunked,
            and tracked through a reviewable evidence lifecycle.
          </p>
        </div>

        <div className={styles.storageStatus}>
          <span />
          Worker polling active
        </div>
      </section>

      {error && <p className={styles.error}>{error}</p>}
      {success && <p className={styles.success}>{success}</p>}

      <section className={styles.layout}>
        <article className={styles.uploadCard}>
          <div className={styles.cardHeading}>
            <div>
              <p className={styles.eyebrow}>Private object storage</p>
              <h2>Upload a document</h2>
            </div>
          </div>

          <div
            className={`${styles.dropZone} ${
              dragActive ? styles.dropZoneActive : ""
            } ${!canUpload ? styles.dropZoneDisabled : ""}`}
            onDragEnter={() => setDragActive(true)}
            onDragLeave={() => setDragActive(false)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              id="document-file"
              type="file"
              accept=".pdf,.docx,.xlsx,.csv"
              onChange={handleFileChange}
              disabled={!canUpload || uploading}
            />

            <div className={styles.uploadIcon}>↑</div>
            <strong>Drop one document here</strong>
            <p>PDF, DOCX, XLSX, or UTF-8 CSV · maximum 25 MB</p>
            <label htmlFor="document-file">Choose file</label>
          </div>

          <div className={styles.formatGrid}>
            {ACCEPTED_EXTENSIONS.map((extension) => (
              <span key={extension}>.{extension}</span>
            ))}
          </div>

          {selectedFile && (
            <div className={styles.selectedFile}>
              <div>
                <span>
                  {fileExtension(selectedFile.name).toUpperCase()}
                </span>
                <div>
                  <strong>{selectedFile.name}</strong>
                  <small>{formatBytes(selectedFile.size)}</small>
                </div>
              </div>

              <button
                type="button"
                onClick={() => chooseFile(null)}
              >
                Remove
              </button>
            </div>
          )}

          <button
            className={styles.uploadButton}
            type="button"
            disabled={!selectedFile || uploading || !canUpload}
            onClick={submitUpload}
          >
            {uploading ? "Uploading…" : "Upload and queue"}
          </button>

          <div className={styles.securityNote}>
            <span>◇</span>
            <p>
              The API verifies the internal format and SHA-256
              fingerprint before the worker parses and chunks the
              stored object.
            </p>
          </div>
        </article>

        <article className={styles.libraryCard}>
          <div className={styles.cardHeading}>
            <div>
              <p className={styles.eyebrow}>Workspace files</p>
              <h2>Document library</h2>
            </div>

            <span>{totalDocuments} documents</span>
          </div>

          {loadingDocuments ? (
            <div className={styles.emptyState}>Loading documents…</div>
          ) : documents.length === 0 ? (
            <div className={styles.emptyState}>
              <div>□</div>
              <strong>No documents yet</strong>
              <p>
                Upload the first file to establish this workspace&apos;s
                evidence library.
              </p>
            </div>
          ) : (
            <div className={styles.documentList}>
              {documents.map((document) => (
                <DocumentItem
                  key={document.id}
                  document={document}
                  canRetry={canUpload}
                  retrying={retryingDocumentId === document.id}
                  onRetry={() => void retryProcessing(document.id)}
                />
              ))}
            </div>
          )}
        </article>
      </section>
    </AppShell>
  );
}

function DocumentItem({
  document,
  canRetry,
  retrying,
  onRetry,
}: {
  document: DocumentRecord;
  canRetry: boolean;
  retrying: boolean;
  onRetry: () => void;
}) {
  return (
    <article className={styles.documentItem}>
      <div className={styles.fileType}>
        {document.file_extension.toUpperCase()}
      </div>

      <div className={styles.fileDetails}>
        <strong>{document.display_name}</strong>
        <p>{document.original_filename}</p>

        <div>
          <span>{formatBytes(document.size_bytes)}</span>
          <span>{formatDate(document.created_at)}</span>
          <span>{document.chunk_count} chunks</span>
          <code>{document.sha256.slice(0, 10)}…</code>
        </div>

        {document.status_message && (
          <small className={styles.statusMessage}>
            {document.status_message}
          </small>
        )}
      </div>

      <div className={styles.statusColumn}>
        <span
          className={`${styles.status} ${
            styles[`status_${document.status}`]
          }`}
        >
          {document.status}
        </span>

        {document.processing_attempts > 0 && (
          <small>
            {document.processing_attempts} attempt
            {document.processing_attempts === 1 ? "" : "s"}
          </small>
        )}

        <Link
          className={styles.inspectLink}
          href={`/documents/${document.id}`}
        >
          Inspect
        </Link>

        {document.status === "failed" && canRetry && (
          <button
            type="button"
            onClick={onRetry}
            disabled={retrying}
          >
            {retrying ? "Retrying…" : "Retry"}
          </button>
        )}
      </div>
    </article>
  );
}
