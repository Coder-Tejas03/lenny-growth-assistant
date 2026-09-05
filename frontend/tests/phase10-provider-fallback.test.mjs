/**
 * Phase 10 Frontend Tests: Visible Provider Selection, Model Provenance & Manual Fallback UX
 *
 * Verifies:
 * 1. ModelSelector provides visible choice between OpenAI Cloud and Ollama Local.
 * 2. ModelSelector documents 7B/8B hardware upgrade configuration without code changes.
 * 3. ChatPane renders actionable manual fallback buttons for BUDGET_EXCEEDED and PROVIDER_UNAVAILABLE errors.
 * 4. MessageItem renders per-message provenance badge (OpenAI / Ollama) on assistant messages.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';

describe('Phase 10 Frontend: Provider UX, Provenance & Manual Fallback UX', () => {
  const baseDir = fs.existsSync('frontend/src') ? 'frontend' : '.';
  const modelSelectorPath = path.resolve(baseDir, 'src/components/Chat/ModelSelector.tsx');
  const chatPanePath = path.resolve(baseDir, 'src/components/Chat/ChatPane.tsx');
  const messageItemPath = path.resolve(baseDir, 'src/components/Chat/MessageItem.tsx');


  test('Gate 1: ModelSelector exposes Cloud OpenAI default and Ollama Local demo', () => {
    const code = fs.readFileSync(modelSelectorPath, 'utf8');
    assert.match(code, /openai/i, 'Must configure openai provider');
    assert.match(code, /gpt-4o-mini/i, 'Must feature gpt-4o-mini as cloud default');
    assert.match(code, /ollama/i, 'Must configure ollama provider');
    assert.match(code, /qwen2\.5:1\.5b/i, 'Must feature qwen2.5:1.5b as local demo model');
    assert.match(code, /Never switches silently/i, 'Must inform user that provider never switches silently');
  });

  test('Gate 2: ModelSelector documents 7B/8B hardware swap configuration path', () => {
    const code = fs.readFileSync(modelSelectorPath, 'utf8');
    assert.match(code, /Hardware Upgrade Path/i, 'Must document hardware upgrade path');
    assert.match(code, /7B \/ 8B/i, 'Must indicate 7B/8B option');
    assert.match(code, /OLLAMA_MODEL/i, 'Must explain OLLAMA_MODEL env var swap');
  });

  test('Gate 3: ChatPane renders actionable manual fallback buttons on provider/budget error', () => {
    const code = fs.readFileSync(chatPanePath, 'utf8');
    assert.match(code, /BUDGET_EXCEEDED/, 'Must check for BUDGET_EXCEEDED code');
    assert.match(code, /PROVIDER_UNAVAILABLE/, 'Must check for PROVIDER_UNAVAILABLE code');
    assert.match(code, /Switch to Local Ollama/i, 'Must provide Switch to Local Ollama fallback button');
    assert.match(code, /Switch to Cloud OpenAI/i, 'Must provide Switch to Cloud OpenAI fallback button');
  });

  test('Gate 4: MessageItem renders per-message provider badge attribution', () => {
    const code = fs.readFileSync(messageItemPath, 'utf8');
    assert.match(code, /message\.provider/, 'Must inspect message.provider');
    assert.match(code, /ollama/, 'Must distinguish ollama provider');
    assert.match(code, /message\.model/, 'Must display model attribution badge');
  });
});
