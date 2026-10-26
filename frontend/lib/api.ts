import type { z } from "zod";
import { ApiError, parseResponse } from "./response";

export { ApiError };
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
    return await parseResponse(response, schema);
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
