const configuredNodes = (import.meta.env.VITE_NODE_URLS as string | undefined)
  ?.split(",")
  .filter(Boolean);

export const NODE_URLS = configuredNodes?.length
  ? configuredNodes
  : ["http://localhost:8001", "http://localhost:8002", "http://localhost:8003"];

export async function api<T>(
  baseUrl: string,
  path: string,
  options?: RequestInit,
): Promise<T> {
  const { headers, ...requestOptions } = options ?? {};
  const response = await fetch(`${baseUrl}${path}`, {
    ...requestOptions,
    headers: { "Content-Type": "application/json", ...headers },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : data.detail
          ? JSON.stringify(data.detail)
          : `Erro HTTP ${response.status}`;
    throw new Error(detail);
  }
  return data as T;
}

export function post<T>(
  baseUrl: string,
  path: string,
  body: unknown = {},
  accessToken?: string,
) {
  return api<T>(baseUrl, path, {
    method: "POST",
    body: JSON.stringify(body),
    headers: accessToken
      ? { Authorization: `Bearer ${accessToken}` }
      : undefined,
  });
}

export function authenticatedApi<T>(
  baseUrl: string,
  path: string,
  accessToken: string,
) {
  return api<T>(baseUrl, path, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export const shortHash = (hash?: string, size = 10) =>
  hash ? `${hash.slice(0, size)}…${hash.slice(-6)}` : "—";

export const formatDate = (date?: string) =>
  date
    ? new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "medium",
      }).format(new Date(date))
    : "—";
