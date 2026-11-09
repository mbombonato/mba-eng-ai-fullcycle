export interface UploadedPart {
  partNumber: number;
  etag: string;
}

export interface PresignedPart {
  partNumber: number;
  url: string;
}

export interface StoredObjectInfo {
  size: number;
  contentType: string | undefined;
}

export interface PresignDownloadOptions {
  expiresIn: number;
  contentType?: string;
  downloadFileName?: string;
}
