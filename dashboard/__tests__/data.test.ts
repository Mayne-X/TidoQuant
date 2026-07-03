import { fetchPipeline, clientFetch, serverFetch } from '../lib/data';

beforeEach(() => jest.resetAllMocks());

describe('clientFetch', () => {
  it('fetches from relative path and returns JSON', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ id: 1, equity: 100 }],
    });
    const result = await clientFetch('/api/pipeline');
    expect(global.fetch).toHaveBeenCalledWith('/api/pipeline');
    expect(result).toEqual([{ id: 1, equity: 100 }]);
  });

  it('throws on non-ok response', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(clientFetch('/api/bad')).rejects.toThrow('API 404');
  });
});

describe('serverFetch', () => {
  it('fetches from API_BASE + path', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok' }),
    });
    const result = await serverFetch('/api/health');
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:4900/api/health');
    expect(result).toEqual({ status: 'ok' });
  });
});

describe('fetchPipeline', () => {
  it('returns pipeline data', async () => {
    const mockData = [{ id: 1, equity: 100, timestamp: '2026-01-01', trades: [] }];
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    });
    const result = await fetchPipeline();
    expect(result).toEqual(mockData);
  });

  it('throws on network error', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('network'));
    await expect(fetchPipeline()).rejects.toThrow('network');
  });
});
