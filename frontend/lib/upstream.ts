import { request as httpRequest } from "node:http";
import { Readable } from "node:stream";

/** Node Fetch replaces Host; the local relay must retain the validated browser authority. */
export const upstreamFetch: typeof fetch = async (input, options = {}) => {
  const url = new URL(input instanceof Request ? input.url : String(input));
  if (url.protocol !== "http:") throw new Error("Local HTTP service required");
  return new Promise<Response>((resolve, reject) => {
    const request = httpRequest(
      url,
      {
        method: options.method,
        headers: Object.fromEntries(new Headers(options.headers)),
        signal: options.signal ?? undefined,
      },
      (response) => {
        const headers = new Headers();
        for (const [key, value] of Object.entries(response.headers))
          if (value !== undefined)
            headers.set(key, Array.isArray(value) ? value.join(", ") : value);
        const status = response.statusCode ?? 502;
        const body = [204, 205, 304].includes(status)
          ? null
          : (Readable.toWeb(response) as ReadableStream<Uint8Array>);
        if (body === null) response.resume();
        resolve(new Response(body, { status, headers }));
      },
    );
    request.on("error", reject);
    request.end(options.body ?? undefined);
  });
};
