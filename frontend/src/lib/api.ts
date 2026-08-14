// frontend/src/lib/api.ts
// Central API base URL.
// Dev:    NEXT_PUBLIC_API_HOST unset  -> http://localhost:8080
// Prod:   set NEXT_PUBLIC_API_HOST to the deployed backend URL
// Mobile: set NEXT_PUBLIC_API_HOST to your machine's LAN IP (e.g. http://192.168.1.50:8080)
export const API_BASE: string =
  process.env.NEXT_PUBLIC_API_HOST?.replace(/\/$/, '') || 'http://localhost:8080';

// WebSocket URL derived from API_BASE (http->ws, https->wss)
export const WS_BASE: string = API_BASE.replace(/^http/, 'ws');

export function deduplicateRepeatedSentences(transcript: string): string {
  const text = (transcript || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';

  const chunks = text
    .split(/(?<=[.!?。！？])\s*/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
  const uniqueChunks: string[] = [];
  let previousKey = '';
  for (const chunk of chunks) {
    const key = chunk.toLocaleLowerCase().replace(/[^\w\u0E00-\u0E7F]+/g, '');
    if (key && key === previousKey) continue;
    uniqueChunks.push(chunk);
    previousKey = key;
  }

  const tokens = uniqueChunks.join(' ').split(' ');
  const result: string[] = [];
  let index = 0;
  while (index < tokens.length) {
    const maxBlock = Math.min(Math.floor((tokens.length - index) / 2), 80);
    let duplicateSize = 0;
    for (let size = maxBlock; size > 1; size -= 1) {
      if (tokens.slice(index, index + size).join(' ') === tokens.slice(index + size, index + size * 2).join(' ')) {
        duplicateSize = size;
        break;
      }
    }
    if (duplicateSize) {
      result.push(...tokens.slice(index, index + duplicateSize));
      index += duplicateSize * 2;
    } else {
      result.push(tokens[index]);
      index += 1;
    }
  }
  return result.join(' ');
}
