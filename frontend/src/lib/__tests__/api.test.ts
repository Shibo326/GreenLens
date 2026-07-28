import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { quickScan, scanUrl, sendVisionMessage, API_BASE_URL } from '../api';

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
  vi.spyOn(console, 'log').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── quickScan ────────────────────────────────────────────────────────────────

describe('quickScan', () => {
  const mockResponse = {
    verdict: 'This claim lacks specificity and verifiable metrics.',
    whatToLookFor: ['Third-party certification', 'Timeline for carbon neutrality'],
    confidence: 'MEDIUM' as const,
  };

  it('sends a POST request with the claim in the body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    await quickScan('Our packaging is 100% carbon neutral by 2025');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/quick-scan`);
    expect(options.method).toBe('POST');
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(JSON.parse(options.body)).toEqual({
      claim: 'Our packaging is 100% carbon neutral by 2025',
    });
  });

  it('returns the parsed QuickScanResponse on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await quickScan('We are eco-friendly');

    expect(result).toEqual(mockResponse);
    expect(result.verdict).toBe(mockResponse.verdict);
    expect(result.whatToLookFor).toHaveLength(2);
    expect(result.confidence).toBe('MEDIUM');
  });

  it('throws an error with server message when response is not ok', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ error: 'Claim is too short' }),
    });

    await expect(quickScan('hi')).rejects.toThrow('Claim is too short');
  });

  it('throws a fallback error when server returns no parseable error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => { throw new Error('not json'); },
    });

    await expect(quickScan('test claim')).rejects.toThrow('Quick scan failed');
  });

  it('throws a timeout error when the request takes too long', async () => {
    // Simulate AbortError from timeout
    mockFetch.mockRejectedValueOnce(
      Object.assign(new Error('The operation was aborted'), { name: 'AbortError' }),
    );

    await expect(quickScan('slow claim')).rejects.toThrow('Request timed out');
  });
});

// ─── scanUrl ──────────────────────────────────────────────────────────────────

describe('scanUrl', () => {
  const mockResponse = {
    verdict: 'The page makes unsubstantiated sustainability claims.',
    whatToLookFor: ['Specific emission data', 'Supply chain transparency'],
    confidence: 'HIGH' as const,
  };

  it('sends a POST request with the URL in the body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    await scanUrl('https://example.com/sustainability');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/url-scan`);
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
      url: 'https://example.com/sustainability',
    });
  });

  it('returns the parsed QuickScanResponse on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await scanUrl('https://greenwash.example.com');

    expect(result).toEqual(mockResponse);
    expect(result.confidence).toBe('HIGH');
  });

  it('throws an error with server message on failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: 'Invalid URL format' }),
    });

    await expect(scanUrl('not-a-url')).rejects.toThrow('Invalid URL format');
  });

  it('throws a fallback error when server error is not parseable', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => { throw new Error('not json'); },
    });

    await expect(scanUrl('https://example.com')).rejects.toThrow('URL scan failed');
  });
});

// ─── sendVisionMessage ────────────────────────────────────────────────────────

describe('sendVisionMessage', () => {
  const mockChatResponse = {
    messageId: 'msg-123',
    role: 'assistant',
    structuredResponse: {
      answer: 'This label contains a vague "eco-friendly" claim without certification.',
      evidence: [{ quote: 'eco-friendly', sourceDocument: 'image', documentType: 'label' }],
      risks: 'Unverified claim',
      recommendation: 'Look for specific certifications like FSC or EU Ecolabel.',
    },
    processingTimeMs: 2500,
  };

  it('sends a multipart POST with sessionId, image, and optional question', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockChatResponse,
    });

    const fakeImage = new File(['fake-image-data'], 'label.png', { type: 'image/png' });

    await sendVisionMessage('session-abc', fakeImage, 'Is this greenwashing?');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/chat/vision`);
    expect(options.method).toBe('POST');

    // Verify FormData contents
    const formData = options.body as FormData;
    expect(formData.get('sessionId')).toBe('session-abc');
    expect(formData.get('image')).toBeInstanceOf(File);
    expect((formData.get('image') as File).name).toBe('label.png');
    expect(formData.get('question')).toBe('Is this greenwashing?');
  });

  it('does not include question field when not provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockChatResponse,
    });

    const fakeImage = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    await sendVisionMessage('session-xyz', fakeImage);

    const [, options] = mockFetch.mock.calls[0];
    const formData = options.body as FormData;
    expect(formData.get('sessionId')).toBe('session-xyz');
    expect(formData.get('image')).toBeInstanceOf(File);
    expect(formData.get('question')).toBeNull();
  });

  it('returns a valid ChatResponse on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockChatResponse,
    });

    const fakeImage = new File(['img'], 'product.png', { type: 'image/png' });
    const result = await sendVisionMessage('s1', fakeImage);

    expect(result.messageId).toBe('msg-123');
    expect(result.role).toBe('assistant');
    expect(result.structuredResponse.answer).toContain('eco-friendly');
    expect(result.processingTimeMs).toBe(2500);
  });

  it('throws an error with server message on failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 413,
      json: async () => ({ error: 'Image too large' }),
    });

    const bigImage = new File(['x'.repeat(100)], 'big.png', { type: 'image/png' });

    await expect(sendVisionMessage('s1', bigImage)).rejects.toThrow('Image too large');
  });

  it('throws a fallback error when server error is not parseable', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => { throw new Error('not json'); },
    });

    const img = new File(['x'], 'img.png', { type: 'image/png' });

    await expect(sendVisionMessage('s1', img)).rejects.toThrow('Vision analysis failed');
  });
});
