"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/hooks/use-auth";
import {
  getDocument,
  getDocumentContent,
  listDocumentChunks,
  listDocumentProcessingJobs,
  listWorkspaces,
  queueStructuredIngestion,
  type ChunkSourceType,
  type DocumentChunk,
  type DocumentContentResponse,
  type DocumentProcessingJob,
  type DocumentRecord,
  type Workspace,
} from "@/lib/api";

import styles from "./document-inspection.module.css";

type InspectionTab =
  | "overview"
  | "pages"
  | "sections"
  | "tables"
  | "chunks"
  | "history";

type InspectionBundle = {
  document: DocumentRecord;
  content: DocumentContentResponse;
  chunks: DocumentChunk[];
  chunkTotal: number;
  jobs: DocumentProcessingJob[];
};

const ACTIVE_STATUSES = new Set(["pending", "uploaded", "queued", "processing"]);
const TAB_LABELS: Array<{ id: InspectionTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "pages", label: "Pages" },
  { id: "sections", label: "Sections" },
  { id: "tables", label: "Tables" },
  { id: "chunks", label: "Chunks" },
  { id: "history", label: "History" },
];

async function fetchInspectionBundle(
  workspaceId: string,
  documentId: string,
): Promise<InspectionBundle> {
  const [document, content, chunks, jobs] = await Promise.all([
    getDocument(workspaceId, documentId),
    getDocumentContent(workspaceId, documentId),
    listDocumentChunks(workspaceId, documentId, { limit: 500 }),
    listDocumentProcessingJobs(workspaceId, documentId),
  ]);

  return {
    document,
    content,
    chunks: chunks.items,
    chunkTotal: chunks.total,
    jobs: jobs.items,
  };
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

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

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en").format(value);
}

function pageRange(start: number | null, end: number | null): string {
  if (start === null && end === null) {
    return "No page reference";
  }

  if (start === end || end === null) {
    return `Page ${start ?? end}`;
  }

  return `Pages ${start}–${end}`;
}

function metadataValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }

  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value) ?? String(value);
}

export default function DocumentInspectionPage() {
  const params = useParams<{ documentId: string }>();
  const router = useRouter();
  const auth = useAuth();
  const documentId = params.documentId;

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState("");
  const [bundle, setBundle] = useState<InspectionBundle | null>(null);
  const [activeTab, setActiveTab] = useState<InspectionTab>("overview");
  const [chunkFilter, setChunkFilter] = useState<"all" | ChunkSourceType>("all");
  const [chunkSearch, setChunkSearch] = useState("");
  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [loadingInspection, setLoadingInspection] = useState(true);
  const [reingesting, setReingesting] = useState(false);
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

  useEffect(() => {
    if (!activeWorkspaceId || !documentId) {
      return;
    }

    let cancelled = false;

    void fetchInspectionBundle(activeWorkspaceId, documentId)
      .then((result) => {
        if (!cancelled) {
          setBundle(result);
          setError(null);
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load the document inspection view.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingInspection(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId, documentId]);

  const isActiveProcessing = bundle
    ? ACTIVE_STATUSES.has(bundle.document.status)
    : false;

  useEffect(() => {
    if (!activeWorkspaceId || !documentId || !isActiveProcessing) {
      return;
    }

    let cancelled = false;
    const interval = window.setInterval(() => {
      void fetchInspectionBundle(activeWorkspaceId, documentId)
        .then((result) => {
          if (!cancelled) {
            setBundle(result);
          }
        })
        .catch(() => {
          // Preserve the current inspection view during temporary polling failures.
        });
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [activeWorkspaceId, documentId, isActiveProcessing]);

  const activeWorkspace = useMemo(
    () =>
      workspaces.find(
        (workspace) => workspace.id === activeWorkspaceId,
      ),
    [activeWorkspaceId, workspaces],
  );

  const filteredChunks = useMemo(() => {
    if (!bundle) {
      return [];
    }

    const query = chunkSearch.trim().toLowerCase();

    return bundle.chunks.filter((chunk) => {
      const matchesType =
        chunkFilter === "all" || chunk.source_type === chunkFilter;
      const matchesSearch =
        query.length === 0 ||
        chunk.content.toLowerCase().includes(query) ||
        chunk.source_label?.toLowerCase().includes(query) ||
        chunk.heading_path.join(" ").toLowerCase().includes(query);

      return matchesType && matchesSearch;
    });
  }, [bundle, chunkFilter, chunkSearch]);

  const canReingest = activeWorkspace
    ? activeWorkspace.role !== "reviewer"
    : false;

  function changeWorkspace(workspaceId: string) {
    localStorage.setItem("veriflow_active_workspace", workspaceId);
    setActiveWorkspaceId(workspaceId);
    setBundle(null);
    setLoadingInspection(true);
    setError(null);
    setSuccess(null);
    router.replace("/documents");
  }

  async function reingestDocument() {
    if (!activeWorkspaceId || !bundle || !canReingest) {
      return;
    }

    setReingesting(true);
    setError(null);
    setSuccess(null);

    try {
      const document = await queueStructuredIngestion(
        activeWorkspaceId,
        bundle.document.id,
      );

      setBundle((current) =>
        current
          ? {
              ...current,
              document,
            }
          : current,
      );
      setSuccess("Structured ingestion was queued successfully.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to queue structured ingestion.",
      );
    } finally {
      setReingesting(false);
    }
  }

  if (
    auth.status === "loading" ||
    loadingWorkspace ||
    loadingInspection ||
    (auth.status === "authenticated" && !activeWorkspace)
  ) {
    return (
      <div className={styles.fullPageState}>
        Building the evidence inspection view…
      </div>
    );
  }

  if (auth.status === "error") {
    return <div className={styles.fullPageState}>{auth.message}</div>;
  }

  if (
    auth.status !== "authenticated" ||
    !activeWorkspace ||
    !bundle
  ) {
    return (
      <div className={styles.fullPageError}>
        <strong>Document inspection is unavailable.</strong>
        <p>{error ?? "The document could not be loaded."}</p>
        <Link href="/documents">Return to documents</Link>
      </div>
    );
  }

  const { document, content, jobs } = bundle;

  return (
    <AppShell
      user={auth.user}
      workspaces={workspaces}
      activeWorkspaceId={activeWorkspaceId}
      onWorkspaceChange={changeWorkspace}
    >
      <div className={styles.breadcrumbs}>
        <Link href="/documents">Documents</Link>
        <span>/</span>
        <span>{document.original_filename}</span>
      </div>

      <section className={styles.hero}>
        <div className={styles.heroIdentity}>
          <div className={styles.fileBadge}>
            {document.file_extension.toUpperCase()}
          </div>
          <div>
            <p className={styles.eyebrow}>Structured evidence inspection</p>
            <h1>{document.display_name}</h1>
            <p>{document.original_filename}</p>
          </div>
        </div>

        <div className={styles.heroActions}>
          <span
            className={`${styles.status} ${styles[`status_${document.status}`]}`}
          >
            {document.status}
          </span>
          <button
            type="button"
            onClick={reingestDocument}
            disabled={!canReingest || reingesting || isActiveProcessing}
          >
            {reingesting ? "Queueing…" : "Re-run ingestion"}
          </button>
        </div>
      </section>

      {error && <p className={styles.error}>{error}</p>}
      {success && <p className={styles.success}>{success}</p>}

      <section className={styles.summaryGrid}>
        <SummaryCard
          label="Pages"
          value={formatNumber(document.page_count)}
          detail={`${formatNumber(document.extracted_text_chars)} extracted characters`}
        />
        <SummaryCard
          label="Sections"
          value={formatNumber(document.section_count)}
          detail={document.parser_name ?? "Parser pending"}
        />
        <SummaryCard
          label="Tables"
          value={formatNumber(document.table_count)}
          detail={`${content.returned_table_count} available in this view`}
        />
        <SummaryCard
          label="Chunks"
          value={formatNumber(document.chunk_count)}
          detail={`${formatNumber(document.chunk_token_estimate)} estimated tokens`}
        />
      </section>

      <nav className={styles.tabs} aria-label="Document inspection sections">
        {TAB_LABELS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? styles.activeTab : undefined}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            <span>{tabCount(tab.id, bundle)}</span>
          </button>
        ))}
      </nav>

      <section className={styles.panel}>
        {activeTab === "overview" && (
          <OverviewTab document={document} jobs={jobs} />
        )}

        {activeTab === "pages" && (
          <PagesTab pages={content.pages} total={document.page_count} />
        )}

        {activeTab === "sections" && (
          <SectionsTab
            sections={content.sections}
            total={document.section_count}
          />
        )}

        {activeTab === "tables" && (
          <TablesTab tables={content.tables} total={document.table_count} />
        )}

        {activeTab === "chunks" && (
          <ChunksTab
            chunks={filteredChunks}
            total={bundle.chunkTotal}
            filter={chunkFilter}
            search={chunkSearch}
            onFilterChange={setChunkFilter}
            onSearchChange={setChunkSearch}
          />
        )}

        {activeTab === "history" && <HistoryTab jobs={jobs} />}
      </section>
    </AppShell>
  );
}

function tabCount(tab: InspectionTab, bundle: InspectionBundle): number {
  if (tab === "pages") {
    return bundle.document.page_count;
  }

  if (tab === "sections") {
    return bundle.document.section_count;
  }

  if (tab === "tables") {
    return bundle.document.table_count;
  }

  if (tab === "chunks") {
    return bundle.chunkTotal;
  }

  if (tab === "history") {
    return bundle.jobs.length;
  }

  return 1;
}

function SummaryCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article className={styles.summaryCard}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function OverviewTab({
  document,
  jobs,
}: {
  document: DocumentRecord;
  jobs: DocumentProcessingJob[];
}) {
  const latestJob = jobs[0] ?? null;
  const metadataEntries = Object.entries(document.document_metadata);

  return (
    <div className={styles.overviewGrid}>
      <article className={styles.detailCard}>
        <CardHeading
          eyebrow="Document identity"
          title="Source and integrity"
        />
        <DefinitionList
          items={[
            ["Original filename", document.original_filename],
            ["Media type", document.mime_type],
            ["File size", formatBytes(document.size_bytes)],
            ["SHA-256", document.sha256],
            ["Uploaded", formatDate(document.created_at)],
            ["Last updated", formatDate(document.updated_at)],
          ]}
        />
      </article>

      <article className={styles.detailCard}>
        <CardHeading
          eyebrow="Processing pipeline"
          title="Parser and chunker"
        />
        <DefinitionList
          items={[
            [
              "Parser",
              document.parser_name
                ? `${document.parser_name} ${document.parser_version ?? ""}`.trim()
                : "Not run",
            ],
            ["Parsed", formatDate(document.parsed_at)],
            [
              "Chunker",
              document.chunker_name
                ? `${document.chunker_name} ${document.chunker_version ?? ""}`.trim()
                : "Not run",
            ],
            ["Chunked", formatDate(document.chunked_at)],
            ["Processing attempts", String(document.processing_attempts)],
            ["Status message", document.status_message ?? "—"],
          ]}
        />
      </article>

      <article className={styles.detailCard}>
        <CardHeading
          eyebrow="Latest background job"
          title={latestJob ? latestJob.job_type : "No job history"}
        />
        {latestJob ? (
          <DefinitionList
            items={[
              ["Status", latestJob.status],
              ["Attempts", `${latestJob.attempts}/${latestJob.max_attempts}`],
              ["Queued", formatDate(latestJob.queued_at)],
              ["Started", formatDate(latestJob.started_at)],
              ["Completed", formatDate(latestJob.completed_at)],
              ["Last error", latestJob.last_error ?? "—"],
            ]}
          />
        ) : (
          <EmptyState>No processing job has been recorded.</EmptyState>
        )}
      </article>

      <article className={styles.detailCard}>
        <CardHeading eyebrow="Metadata" title="Captured attributes" />
        {metadataEntries.length > 0 ? (
          <DefinitionList
            items={metadataEntries.map(([key, value]) => [
              key.replaceAll("_", " "),
              metadataValue(value),
            ])}
          />
        ) : (
          <EmptyState>No document metadata was captured.</EmptyState>
        )}
      </article>
    </div>
  );
}

function PagesTab({
  pages,
  total,
}: {
  pages: DocumentContentResponse["pages"];
  total: number;
}) {
  if (pages.length === 0) {
    return (
      <EmptyState>
        No page records are available. DOCX, XLSX, and CSV sources may be
        represented primarily as sections and tables.
      </EmptyState>
    );
  }

  return (
    <div className={styles.stack}>
      <PanelIntro
        title="Extracted pages"
        description={`Showing ${pages.length} of ${total} page records with exact source numbering.`}
      />
      {pages.map((page) => (
        <details className={styles.contentCard} key={page.id}>
          <summary>
            <div>
              <strong>Page {page.page_number}</strong>
              <span>
                {formatNumber(page.word_count)} words · {formatNumber(page.char_count)} characters
              </span>
            </div>
            <span>Inspect</span>
          </summary>
          <pre>{page.text_content || "No extractable text was found on this page."}</pre>
        </details>
      ))}
    </div>
  );
}

function SectionsTab({
  sections,
  total,
}: {
  sections: DocumentContentResponse["sections"];
  total: number;
}) {
  if (sections.length === 0) {
    return <EmptyState>No structured sections were detected.</EmptyState>;
  }

  return (
    <div className={styles.stack}>
      <PanelIntro
        title="Document sections"
        description={`Showing ${sections.length} of ${total} detected sections with heading and page provenance.`}
      />
      {sections.map((section) => (
        <details className={styles.contentCard} key={section.id}>
          <summary>
            <div>
              <strong>{section.title ?? `Section ${section.ordinal + 1}`}</strong>
              <span>
                {section.section_path.join(" / ") || "Unlabelled section"} · {pageRange(section.page_start, section.page_end)}
              </span>
            </div>
            <span>Level {section.heading_level ?? "—"}</span>
          </summary>
          <pre>{section.content || "This section contains no extractable narrative text."}</pre>
        </details>
      ))}
    </div>
  );
}

function TablesTab({
  tables,
  total,
}: {
  tables: DocumentContentResponse["tables"];
  total: number;
}) {
  if (tables.length === 0) {
    return <EmptyState>No tables were detected in this document.</EmptyState>;
  }

  return (
    <div className={styles.stack}>
      <PanelIntro
        title="Extracted tables"
        description={`Showing ${tables.length} of ${total} tables. Each preview is capped by the API row limit.`}
      />
      {tables.map((table) => (
        <article className={styles.tableCard} key={table.id}>
          <div className={styles.tableHeading}>
            <div>
              <strong>
                {table.title ?? table.source_label ?? `Table ${table.ordinal + 1}`}
              </strong>
              <span>
                {formatNumber(table.row_count)} rows · {formatNumber(table.column_count)} columns
                {table.page_number ? ` · Page ${table.page_number}` : ""}
              </span>
            </div>
            {table.is_truncated && <small>Preview truncated</small>}
          </div>

          <div className={styles.tableViewport}>
            <table>
              {table.column_names.length > 0 && (
                <thead>
                  <tr>
                    {table.column_names.map((column, index) => (
                      <th key={`${table.id}-column-${index}`}>{column || `Column ${index + 1}`}</th>
                    ))}
                  </tr>
                </thead>
              )}
              <tbody>
                {table.rows.map((row, rowIndex) => (
                  <tr key={`${table.id}-row-${rowIndex}`}>
                    {row.map((cell, cellIndex) => (
                      <td key={`${table.id}-${rowIndex}-${cellIndex}`}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ))}
    </div>
  );
}

function ChunksTab({
  chunks,
  total,
  filter,
  search,
  onFilterChange,
  onSearchChange,
}: {
  chunks: DocumentChunk[];
  total: number;
  filter: "all" | ChunkSourceType;
  search: string;
  onFilterChange: (value: "all" | ChunkSourceType) => void;
  onSearchChange: (value: string) => void;
}) {
  return (
    <div className={styles.stack}>
      <div className={styles.chunkToolbar}>
        <div>
          <PanelIntro
            title="Retrieval chunks"
            description={`${formatNumber(total)} stable chunks generated with source provenance and deterministic fingerprints.`}
          />
        </div>
        <input
          aria-label="Search chunks"
          placeholder="Search chunk content…"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </div>

      <div className={styles.filterRow}>
        {(["all", "section", "page", "table"] as const).map((value) => (
          <button
            key={value}
            type="button"
            className={filter === value ? styles.activeFilter : undefined}
            onClick={() => onFilterChange(value)}
          >
            {value}
          </button>
        ))}
      </div>

      {chunks.length === 0 ? (
        <EmptyState>No chunks match the selected filter.</EmptyState>
      ) : (
        <div className={styles.chunkList}>
          {chunks.map((chunk) => (
            <article className={styles.chunkCard} key={chunk.id}>
              <div className={styles.chunkHeader}>
                <div>
                  <span className={styles.sourceBadge}>{chunk.source_type}</span>
                  <strong>Chunk {chunk.ordinal + 1}</strong>
                </div>
                <span>{formatNumber(chunk.token_estimate)} tokens</span>
              </div>

              <div className={styles.provenance}>
                <span>{chunk.source_label ?? "Unlabelled source"}</span>
                <span>{chunk.heading_path.join(" / ") || "No heading path"}</span>
                <span>{pageRange(chunk.page_start, chunk.page_end)}</span>
              </div>

              <pre>{chunk.content}</pre>

              <footer>
                <code>{chunk.fingerprint}</code>
                <span>{formatNumber(chunk.overlap_chars)} overlap characters</span>
              </footer>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function HistoryTab({ jobs }: { jobs: DocumentProcessingJob[] }) {
  if (jobs.length === 0) {
    return <EmptyState>No processing history is available.</EmptyState>;
  }

  return (
    <div className={styles.stack}>
      <PanelIntro
        title="Processing history"
        description="Every queued ingestion attempt is retained for operational review and troubleshooting."
      />
      <div className={styles.historyList}>
        {jobs.map((job) => (
          <article className={styles.historyCard} key={job.id}>
            <div className={styles.timelineMarker} />
            <div>
              <div className={styles.historyHeading}>
                <div>
                  <strong>{job.job_type.replaceAll("_", " ")}</strong>
                  <span>{formatDate(job.queued_at)}</span>
                </div>
                <span className={`${styles.jobStatus} ${styles[`job_${job.status}`]}`}>
                  {job.status}
                </span>
              </div>

              <dl>
                <div>
                  <dt>Attempts</dt>
                  <dd>{job.attempts}/{job.max_attempts}</dd>
                </div>
                <div>
                  <dt>Started</dt>
                  <dd>{formatDate(job.started_at)}</dd>
                </div>
                <div>
                  <dt>Completed</dt>
                  <dd>{formatDate(job.completed_at)}</dd>
                </div>
              </dl>

              {job.last_error && <p className={styles.jobError}>{job.last_error}</p>}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function CardHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className={styles.cardHeading}>
      <span>{eyebrow}</span>
      <h2>{title}</h2>
    </div>
  );
}

function DefinitionList({ items }: { items: string[][] }) {
  return (
    <dl className={styles.definitionList}>
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function PanelIntro({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className={styles.panelIntro}>
      <h2>{title}</h2>
      <p>{description}</p>
    </div>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return <div className={styles.emptyState}>{children}</div>;
}
