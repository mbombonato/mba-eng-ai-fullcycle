import { randomUUID } from 'node:crypto';

/**
 * Tests run inside the Compose network, where the browser-facing
 * S3_PUBLIC_ENDPOINT (e.g. http://localhost:9000) is unreachable. Presigned
 * URLs embed the signed Host, so tests must sign with the internal endpoint.
 * Call before the ConfigModule loads `storageConfig`.
 */
export function signPresignedUrlsWithInternalEndpoint(): void {
  process.env.S3_PUBLIC_ENDPOINT =
    process.env.S3_ENDPOINT ?? 'http://minio:9000';
}

export function uniqueTestKey(prefix = 'test'): string {
  return `${prefix}/${randomUUID()}`;
}

/** PUTs a buffer to a presigned part URL and returns the part ETag. */
export async function putPart(url: string, body: Buffer): Promise<string> {
  const response = await fetch(url, {
    method: 'PUT',
    body: new Uint8Array(body),
  });
  if (!response.ok) {
    throw new Error(
      `Part upload failed: ${response.status} ${await response.text()}`,
    );
  }
  const etag = response.headers.get('etag');
  if (!etag) throw new Error('Storage did not return an ETag');
  return etag;
}
