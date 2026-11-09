import { ConfigModule } from '@nestjs/config';
import { Test } from '@nestjs/testing';
import { InvalidUploadPartsException } from '../common/exceptions/domain.exception';
import storageConfig from '../config/storage.config';
import {
  putPart,
  signPresignedUrlsWithInternalEndpoint,
  uniqueTestKey,
} from '../test/storage';
import { StorageModule } from './storage.module';
import { StorageService } from './storage.service';

const MIB = 1024 * 1024;

describe('StorageService (integration — MinIO)', () => {
  let storage: StorageService;
  const createdKeys: string[] = [];

  beforeAll(async () => {
    signPresignedUrlsWithInternalEndpoint();
    const moduleRef = await Test.createTestingModule({
      imports: [
        ConfigModule.forRoot({ isGlobal: true, load: [storageConfig] }),
        StorageModule,
      ],
    }).compile();
    storage = moduleRef.get(StorageService);
  });

  afterAll(async () => {
    await Promise.all(createdKeys.map((key) => storage.deleteObject(key)));
  });

  function newKey(): string {
    const key = uniqueTestKey('storage-spec');
    createdKeys.push(key);
    return key;
  }

  describe('multipart upload through presigned part URLs', () => {
    it('should assemble two parts and report the exact object size', async () => {
      const key = newKey();
      const first = Buffer.alloc(5 * MIB, 1);
      const second = Buffer.alloc(1024, 2);
      const uploadId = await storage.createMultipartUpload(key, 'video/mp4');
      const parts = await storage.presignUploadParts(key, uploadId, 2, 300);

      const etags = [
        await putPart(parts[0].url, first),
        await putPart(parts[1].url, second),
      ];
      await storage.completeMultipartUpload(key, uploadId, [
        { partNumber: 2, etag: etags[1] },
        { partNumber: 1, etag: etags[0] },
      ]);

      const info = await storage.headObject(key);
      expect(info.size).toBe(first.length + second.length);
      expect(info.contentType).toBe('video/mp4');
    });

    it('should return one presigned URL per part numbered from 1', async () => {
      const key = newKey();
      const uploadId = await storage.createMultipartUpload(key, 'video/mp4');

      const parts = await storage.presignUploadParts(key, uploadId, 3, 300);

      expect(parts.map((p) => p.partNumber)).toEqual([1, 2, 3]);
      expect(parts[0].url).toContain(`partNumber=1`);
      expect(parts[0].url).toContain(`uploadId=`);
      await storage.abortMultipartUpload(key, uploadId);
    });

    it('should raise InvalidUploadPartsException for an unknown ETag', async () => {
      const key = newKey();
      const uploadId = await storage.createMultipartUpload(key, 'video/mp4');
      const [part] = await storage.presignUploadParts(key, uploadId, 1, 300);
      await putPart(part.url, Buffer.from('tiny'));

      await expect(
        storage.completeMultipartUpload(key, uploadId, [
          { partNumber: 1, etag: '"00000000000000000000000000000000"' },
        ]),
      ).rejects.toBeInstanceOf(InvalidUploadPartsException);
      await storage.abortMultipartUpload(key, uploadId);
    });

    it('should raise InvalidUploadPartsException for an aborted upload', async () => {
      const key = newKey();
      const uploadId = await storage.createMultipartUpload(key, 'video/mp4');
      await storage.abortMultipartUpload(key, uploadId);

      await expect(
        storage.completeMultipartUpload(key, uploadId, [
          { partNumber: 1, etag: '"abc"' },
        ]),
      ).rejects.toBeInstanceOf(InvalidUploadPartsException);
    });
  });

  describe('objects and presigned downloads', () => {
    it('should put, head and delete an object', async () => {
      const key = newKey();
      await storage.putObject(key, Buffer.from('jpeg-bytes'), 'image/jpeg');

      const info = await storage.headObject(key);
      expect(info).toEqual({ size: 10, contentType: 'image/jpeg' });

      await storage.deleteObject(key);
      await expect(storage.headObject(key)).rejects.toThrow();
    });

    it('should answer a Range request on a presigned URL with 206 Partial Content', async () => {
      const key = newKey();
      const body = Buffer.from('0123456789abcdefghij');
      await storage.putObject(key, body, 'video/mp4');
      const url = await storage.presignDownloadUrl(key, {
        expiresIn: 60,
        contentType: 'video/mp4',
      });

      const response = await fetch(url, { headers: { Range: 'bytes=0-9' } });

      expect(response.status).toBe(206);
      expect(response.headers.get('content-range')).toBe('bytes 0-9/20');
      expect(response.headers.get('content-type')).toBe('video/mp4');
      expect(await response.text()).toBe('0123456789');
    });

    it('should serve a download URL as attachment with the original file name', async () => {
      const key = newKey();
      await storage.putObject(key, Buffer.from('data'), 'video/mp4');
      const url = await storage.presignDownloadUrl(key, {
        expiresIn: 60,
        downloadFileName: 'minha viagem.mp4',
      });

      const response = await fetch(url);

      expect(response.status).toBe(200);
      expect(response.headers.get('content-disposition')).toContain(
        'attachment; filename="minha viagem.mp4"',
      );
    });

    it('should presign internal download URLs reachable from the Compose network', async () => {
      const key = newKey();
      await storage.putObject(key, Buffer.from('internal'), 'video/mp4');

      const url = await storage.presignInternalDownloadUrl(key, 60);
      const response = await fetch(url);

      expect(
        url.startsWith(process.env.S3_ENDPOINT ?? 'http://minio:9000'),
      ).toBe(true);
      expect(await response.text()).toBe('internal');
    });
  });
});
