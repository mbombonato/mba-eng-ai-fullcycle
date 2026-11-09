import { generateVideoSlug } from './slug.util';
import { VIDEO_SLUG_LENGTH, VIDEO_SLUG_PATTERN } from './videos.constants';

describe('generateVideoSlug', () => {
  it('should produce an 11-character slug', () => {
    expect(generateVideoSlug()).toHaveLength(VIDEO_SLUG_LENGTH);
  });

  it('should only use URL-safe base64url characters', () => {
    for (let i = 0; i < 500; i++) {
      expect(generateVideoSlug()).toMatch(VIDEO_SLUG_PATTERN);
    }
  });

  it('should not repeat across many draws', () => {
    const slugs = new Set(
      Array.from({ length: 10_000 }, () => generateVideoSlug()),
    );
    expect(slugs.size).toBe(10_000);
  });
});
