import {
  AbortMultipartUploadCommand,
  CompleteMultipartUploadCommand,
  CreateMultipartUploadCommand,
  DeleteObjectCommand,
  GetObjectCommand,
  HeadObjectCommand,
  PutObjectCommand,
  S3Client,
  S3ServiceException,
  UploadPartCommand,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { Inject, Injectable } from '@nestjs/common';
import type { ConfigType } from '@nestjs/config';
import { InvalidUploadPartsException } from '../common/exceptions/domain.exception';
import storageConfig from '../config/storage.config';
import {
  S3_CLIENT,
  S3_INVALID_PARTS_ERRORS,
  S3_PRESIGN_CLIENT,
} from './storage.constants';
import type {
  PresignDownloadOptions,
  PresignedPart,
  StoredObjectInfo,
  UploadedPart,
} from './storage.types';

@Injectable()
export class StorageService {
  private readonly bucket: string;

  constructor(
    @Inject(S3_CLIENT) private readonly client: S3Client,
    @Inject(S3_PRESIGN_CLIENT) private readonly presignClient: S3Client,
    @Inject(storageConfig.KEY) cfg: ConfigType<typeof storageConfig>,
  ) {
    this.bucket = cfg.bucket;
  }

  async createMultipartUpload(
    key: string,
    contentType: string,
  ): Promise<string> {
    const result = await this.client.send(
      new CreateMultipartUploadCommand({
        Bucket: this.bucket,
        Key: key,
        ContentType: contentType,
      }),
    );
    if (!result.UploadId) {
      throw new Error(`Storage did not return an UploadId for key ${key}`);
    }
    return result.UploadId;
  }

  async presignUploadParts(
    key: string,
    uploadId: string,
    partCount: number,
    expiresIn: number,
  ): Promise<PresignedPart[]> {
    const partNumbers = Array.from({ length: partCount }, (_, i) => i + 1);
    return Promise.all(
      partNumbers.map(async (partNumber) => ({
        partNumber,
        url: await getSignedUrl(
          this.presignClient,
          new UploadPartCommand({
            Bucket: this.bucket,
            Key: key,
            UploadId: uploadId,
            PartNumber: partNumber,
          }),
          { expiresIn },
        ),
      })),
    );
  }

  async completeMultipartUpload(
    key: string,
    uploadId: string,
    parts: UploadedPart[],
  ): Promise<void> {
    const sorted = [...parts].sort((a, b) => a.partNumber - b.partNumber);
    try {
      await this.client.send(
        new CompleteMultipartUploadCommand({
          Bucket: this.bucket,
          Key: key,
          UploadId: uploadId,
          MultipartUpload: {
            Parts: sorted.map((p) => ({
              ETag: p.etag,
              PartNumber: p.partNumber,
            })),
          },
        }),
      );
    } catch (err) {
      if (
        err instanceof S3ServiceException &&
        (S3_INVALID_PARTS_ERRORS as readonly string[]).includes(err.name)
      ) {
        throw new InvalidUploadPartsException();
      }
      throw err;
    }
  }

  async abortMultipartUpload(key: string, uploadId: string): Promise<void> {
    await this.client.send(
      new AbortMultipartUploadCommand({
        Bucket: this.bucket,
        Key: key,
        UploadId: uploadId,
      }),
    );
  }

  async headObject(key: string): Promise<StoredObjectInfo> {
    const result = await this.client.send(
      new HeadObjectCommand({ Bucket: this.bucket, Key: key }),
    );
    return {
      size: Number(result.ContentLength ?? 0),
      contentType: result.ContentType,
    };
  }

  async putObject(
    key: string,
    body: Buffer,
    contentType: string,
  ): Promise<void> {
    await this.client.send(
      new PutObjectCommand({
        Bucket: this.bucket,
        Key: key,
        Body: body,
        ContentType: contentType,
      }),
    );
  }

  async deleteObject(key: string): Promise<void> {
    await this.client.send(
      new DeleteObjectCommand({ Bucket: this.bucket, Key: key }),
    );
  }

  /** Presigned GET for clients (public endpoint). Storage serves Range → 206. */
  async presignDownloadUrl(
    key: string,
    options: PresignDownloadOptions,
  ): Promise<string> {
    return getSignedUrl(
      this.presignClient,
      new GetObjectCommand({
        Bucket: this.bucket,
        Key: key,
        ResponseContentType: options.contentType,
        ResponseContentDisposition: options.downloadFileName
          ? buildAttachmentDisposition(options.downloadFileName)
          : undefined,
      }),
      { expiresIn: options.expiresIn },
    );
  }

  /** Presigned GET on the internal endpoint — used by the worker (FFmpeg input). */
  async presignInternalDownloadUrl(
    key: string,
    expiresIn: number,
  ): Promise<string> {
    return getSignedUrl(
      this.client,
      new GetObjectCommand({ Bucket: this.bucket, Key: key }),
      { expiresIn },
    );
  }
}

export function buildAttachmentDisposition(fileName: string): string {
  const asciiFallback = fileName.replace(/[^\x20-\x7e]|["\\]/g, '_');
  return `attachment; filename="${asciiFallback}"; filename*=UTF-8''${encodeURIComponent(fileName)}`;
}
