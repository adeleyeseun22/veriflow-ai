"use client";

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
  uploadDocument,
  type DocumentListResponse,
  type DocumentRecord,
  type Workspace,
} from "@/lib/api";

import styles from "./documents.module.css";

const ACCEPTED_EXTENSIONS = ["pdf", "docx", "xlsx", "csv"];
const MAX_FILE_SIZE = 25 * 1024 * 1024;

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

    async function loadWorkspaceOptions() {
      try {
        const result = await listWorkspaces();

        if (result.length === 0) {
          router.replace("/onboarding");
          return;
        }

        const storedWorkspaceId = localStorage.getItem("veriflow_active_workspace");
        const selected = result.some((workspace) => workspace.id === storedWorkspaceId)
          ? storedWorkspaceId!
          : result[0].id;

        localStorage.setItem("veriflow_active_workspace", selected);
        setWorkspaces(result);
        setActiveWorkspaceId(selected);
      } catch (requestError) {
        setError(
          requestError instanceof Error ? requestError.message : "Unable to load workspaces.",
        );
      } finally {
        setLoadingWorkspace(false);
      }
    }

    void loadWorkspaceOptions();
  }, [auth.status, router]);

  const loadWorkspaceDocuments = useCallback(async (workspaceId: string) => {
    setLoadingDocuments(true);
    setError(null);

    try {
      const result: DocumentListResponse = await listDocuments(workspaceId, { limit: 100 });
      setDocuments(result.items);
      setTotalDocuments(result.total);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Unable to load documents.",
      );
    } finally {
      setLoadingDocuments(false);
    }
  }, []);

  useEffect(() => {
    if (activeWorkspaceId) {
      void loadWorkspaceDocuments(activeWorkspaceId);
    }
  }, [activeWorkspaceId, loadWorkspaceDocuments]);

  const activeWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === activeWorkspaceId),
    [activeWorkspaceId, workspaces],
  );

  const canUpload = activeWorkspace?.role !== "reviewer";

  function changeWorkspace(workspaceId: string) {
    localStorage.setItem("veriflow_active_workspace", workspaceId);
    setActiveWorkspaceId(workspaceId);
    setDocuments([]);
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

    if (!canUpload) {
      return;
    }

    chooseFile(event.dataTransfer.files?.[0] ?? null);
  }

  async function submitUpload() {
    if (!selectedFile || !activeWorkspaceId || !canUpload) {
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const uploaded = await uploadDocument(activeWorkspaceId, selectedFile);
      setSuccess(`${uploaded.original_filename} was stored securely.`);
      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      await loadWorkspaceDocuments(activeWorkspaceId);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  if (
    auth.status === "loading" ||
    loadingWorkspace ||
    (auth.status === "authenticated" && !activeWorkspace)
  ) {
    return <div className={styles.fullPageState}>Opening the document workspace…</div>;
  }

  if (auth.status === "error") {
    return <div className={styles.fullPageState}>{auth.message}</div>;
  }

  if (auth.status !== "authenticated" || !activeWorkspace) {
    return <div className={styles.fullPageState}>Redirecting…</div>;
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
          <p className={styles.eyebrow}>Document library</p>
          <h1>Bring your evidence into one controlled workspace.</h1>
          <p>
            Files are validated, fingerprinted, checked for duplicates, and stored privately before
            they enter the processing pipeline.
          </p>
        </div>
        <div className={styles.storageStatus}>
          <span />
          MinIO private storage active
        </div>
      </section>

      {error && <p className={styles.error}>{error}</p>}
      {success && <p className={styles.success}>{success}</p>}

      <section className={styles.layout}>
        <article className={styles.uploadCard}>
          <div className={styles.cardHeading}>
            <div>
              <p className={styles.eyebrow}>Secure upload</p>
              <h2>Add a document</h2>
            </div>
            <span>25 MB maximum</span>
          </div>

          <div
            className={`${styles.dropZone} ${dragActive ? styles.dropZoneActive : ""} ${
              !canUpload ? styles.dropZoneDisabled : ""
            }`}
            onDragEnter={(event) => {
              event.preventDefault();
              if (canUpload) setDragActive(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragActive(false)}
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
            <strong>{canUpload ? "Drop one file here" : "Reviewer access is read-only"}</strong>
            <p>
              {canUpload
                ? "or browse your computer for a supported document"
                : "Owners, administrators, and members can upload documents."}
            </p>
            {canUpload && <label htmlFor="document-file">Browse files</label>}
          </div>

          <div className={styles.formatGrid} aria-label="Supported file formats">
            {ACCEPTED_EXTENSIONS.map((extension) => (
              <span key={extension}>{extension.toUpperCase()}</span>
            ))}
          </div>

          {selectedFile && (
            <div className={styles.selectedFile}>
              <div>
                <span>{fileExtension(selectedFile.name).toUpperCase()}</span>
                <div>
                  <strong>{selectedFile.name}</strong>
                  <small>{formatBytes(selectedFile.size)}</small>
                </div>
              </div>
              <button type="button" onClick={() => chooseFile(null)} disabled={uploading}>
                Remove
              </button>
            </div>
          )}

          <button
            className={styles.uploadButton}
            type="button"
            onClick={submitUpload}
            disabled={!selectedFile || uploading || !canUpload}
          >
            {uploading ? "Validating and storing…" : "Upload document"}
          </button>

          <div className={styles.securityNote}>
            <span>✓</span>
            <p>
              The API verifies the internal file structure and calculates a SHA-256 fingerprint. The
              browser-provided MIME type is never trusted on its own.
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
              <p>Upload the first file to establish this workspace&apos;s evidence library.</p>
            </div>
          ) : (
            <div className={styles.documentList}>
              {documents.map((document) => (
                <DocumentItem document={document} key={document.id} />
              ))}
            </div>
          )}
        </article>
      </section>
    </AppShell>
  );
}

function DocumentItem({ document }: { document: DocumentRecord }) {
  return (
    <article className={styles.documentItem}>
      <div className={styles.fileType}>{document.file_extension.toUpperCase()}</div>
      <div className={styles.fileDetails}>
        <strong>{document.display_name}</strong>
        <p>{document.original_filename}</p>
        <div>
          <span>{formatBytes(document.size_bytes)}</span>
          <span>{formatDate(document.created_at)}</span>
          <code>{document.sha256.slice(0, 10)}…</code>
        </div>
      </div>
      <span className={`${styles.status} ${styles[`status_${document.status}`]}`}>
        {document.status}
      </span>
    </article>
  );
}
