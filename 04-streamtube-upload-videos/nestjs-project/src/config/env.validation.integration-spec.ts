import { envValidationSchema } from './env.validation';

const requiredEnv = {
  DB_USERNAME: 'user',
  DB_PASSWORD: 'pass',
  DB_NAME: 'db',
  JWT_SECRET: 'secret',
  JWT_REFRESH_SECRET: 'refresh-secret',
  S3_ACCESS_KEY_ID: 'access-key',
  S3_SECRET_ACCESS_KEY: 'secret-key',
};

const validate = (env: Record<string, string>) =>
  envValidationSchema.validate(
    { ...requiredEnv, ...env },
    { allowUnknown: true, abortEarly: false },
  );

describe('envValidationSchema — SWAGGER_ENABLED', () => {
  it('should reject SWAGGER_ENABLED with an invalid value', () => {
    const { error } = validate({ SWAGGER_ENABLED: 'invalid' });
    expect(error).toBeDefined();
    expect(error!.message).toContain('SWAGGER_ENABLED');
  });

  it('should accept SWAGGER_ENABLED=true', () => {
    const { error } = validate({ SWAGGER_ENABLED: 'true' });
    expect(error).toBeUndefined();
  });

  it('should accept SWAGGER_ENABLED=false', () => {
    const { error } = validate({ SWAGGER_ENABLED: 'false' });
    expect(error).toBeUndefined();
  });

  it('should apply default false when SWAGGER_ENABLED is not set', () => {
    const { value, error } = validate({});
    expect(error).toBeUndefined();
    expect(value.SWAGGER_ENABLED).toBe('false');
  });
});

describe('envValidationSchema — storage, queue and videos (phase 03)', () => {
  it('should require S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY', () => {
    const { error } = envValidationSchema.validate(
      {
        ...requiredEnv,
        S3_ACCESS_KEY_ID: undefined,
        S3_SECRET_ACCESS_KEY: undefined,
      },
      { allowUnknown: true, abortEarly: false },
    );
    expect(error).toBeDefined();
    expect(error!.message).toContain('S3_ACCESS_KEY_ID');
    expect(error!.message).toContain('S3_SECRET_ACCESS_KEY');
  });

  it('should apply Compose service-name defaults for storage and queue hosts', () => {
    const { value, error } = validate({});
    expect(error).toBeUndefined();
    expect(value.S3_ENDPOINT).toBe('http://minio:9000');
    expect(value.S3_BUCKET).toBe('streamtube');
    expect(value.REDIS_HOST).toBe('redis');
    expect(value.REDIS_PORT).toBe(6379);
  });

  it('should apply default upload and processing settings', () => {
    const { value } = validate({});
    expect(value.UPLOAD_PART_SIZE_MB).toBe(100);
    expect(value.UPLOAD_URL_EXPIRATION_SECONDS).toBe(86400);
    expect(value.STREAM_URL_EXPIRATION_SECONDS).toBe(3600);
    expect(value.VIDEO_PROCESSING_ATTEMPTS).toBe(3);
  });

  it('should reject UPLOAD_PART_SIZE_MB below the S3 multipart minimum of 5 MiB', () => {
    const { error } = validate({ UPLOAD_PART_SIZE_MB: '4' });
    expect(error).toBeDefined();
    expect(error!.message).toContain('UPLOAD_PART_SIZE_MB');
  });

  it('should reject presigned URL expirations above the SigV4 limit of 7 days', () => {
    const { error } = validate({ UPLOAD_URL_EXPIRATION_SECONDS: '604801' });
    expect(error).toBeDefined();
  });
});
