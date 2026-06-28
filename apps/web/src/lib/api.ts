export type ApiHealth = {
  status: "healthy" | "unhealthy";
  service: string;
  version: string;
  checks?: Record<string, "healthy" | "unhealthy">;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getApiReadiness(): Promise<ApiHealth> {
  const response = await fetch(`${API_URL}/health/ready`, {
    cache: "no-store",
  });

  const payload = (await response.json()) as ApiHealth;

  if (!response.ok) {
    throw new Error(`API readiness failed with status ${response.status}`);
  }

  return payload;
}
