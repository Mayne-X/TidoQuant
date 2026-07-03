import fs from 'fs';
import path from 'path';

export function getTrades() {
  const filePath = path.join('/journal', 'trades.jsonl');
  if (!fs.existsSync(filePath)) return [];
  
  const content = fs.readFileSync(filePath, 'utf-8');
  return content.split('\n').filter(Boolean).map(line => JSON.parse(line));
}
