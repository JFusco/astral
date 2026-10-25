import type { z } from "zod";

export class ApiError extends Error {
  constructor(
    public readonly kind:
      "unavailable" | "timeout" | "invalid-response" | "rejected",
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export async function api<T>(
  path: string,
  schema: z.ZodType<T>,
  options: { body?: unknown; signal?: AbortSignal; timeout?: number } = {},
): Promise<T> {
  const timeout = AbortSignal.timeout(options.timeout ?? 15000);
  try {
    const response = await fetch(path, {
      method: options.body === undefined ? "GET" : "POST",
      cache: "no-store",
      credentials: "same-origin",
      headers:
        options.body === undefined
          ? {}
          : {
              "Content-Type": "application/json",
              "X-Astral-Intent": "paper-only",
            },
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal
        ? AbortSignal.any([options.signal, timeout])
        : timeout,
    });
    const result: unknown = await response.json().catch(() => {
      throw new ApiError("invalid-response", "Service returned invalid JSON");
    });
    if (!response.ok) {
      const detail =
        result &&
        typeof result === "object" &&
        "detail" in result &&
        typeof result.detail === "string"
          ? result.detail
          : `Service returned ${response.status}`;
      throw new ApiError("rejected", detail, response.status);
    }
    if (
      result &&
      typeof result === "object" &&
      "status" in result &&
      result.status === "unavailable"
    )
      throw new ApiError(
        "unavailable",
        "reason" in result && typeof result.reason === "string"
          ? result.reason
          : "Saved report unavailable",
      );
    const checked = schema.safeParse(result);
    if (!checked.success)
      throw new ApiError(
        "invalid-response",
        "Service response did not match the dashboard contract",
      );
    return checked.data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timeout.aborted)
      throw new ApiError(
        "timeout",
        options.body === undefined
          ? "Service request timed out."
          : "Service request timed out. Submission outcome may be uncertain; reconcile before taking further action.",
      );
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      "unavailable",
      options.body === undefined
        ? "Service unavailable."
        : "Service unavailable. Submission outcome may be uncertain; reconcile before taking further action.",
    );
  }
}
export const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Service unavailable";
