/** S3 client used for server-to-server calls (Compose service name endpoint). */
export const S3_CLIENT = Symbol('S3_CLIENT');

/** S3 client used only to sign URLs handed to clients (public endpoint). */
export const S3_PRESIGN_CLIENT = Symbol('S3_PRESIGN_CLIENT');

/** S3 error names returned by CompleteMultipartUpload for an invalid part list. */
export const S3_INVALID_PARTS_ERRORS = [
  'InvalidPart',
  'InvalidPartOrder',
  'NoSuchUpload',
  'EntityTooSmall',
] as const;
