import type { z } from "zod";

export class ApiError extends Error {
  constructor(
    public readonly kind:
      | "unavailable"
      | "timeout"
      | "invalid-response"
      | "rejected",
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
/** Shared by the browser and server read paths so their contracts cannot drift. */
export async function parseResponse<T>(
  response: Response,
  schema: z.ZodType<T>,
): Promise<T> {
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
}
