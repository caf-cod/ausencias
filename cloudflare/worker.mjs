import { sign } from 'node:crypto';
import { Buffer } from 'node:buffer';

const origin = 'https://caf-cod.github.io';
const repo = '/repos/caf-cod/ausencias';
const cgcafFile = repo + '/contents/dados/ausencias.json';
const cgmcafFile = repo + '/contents/dados/ausencias-cgmcaf.json';
const limit = 750_000;

function reply(status, data) {
  const headers = {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Cache-Control': 'no-store',
  };
  return data === undefined
    ? new Response(null, { status, headers })
    : Response.json(data, { status, headers });
}

async function github(path, token, method = 'GET', data) {
  const stage = path.endsWith('/installation') ? 'installation' :
    path.endsWith('/access_tokens') ? 'token' : 'file';
  return fetch('https://api.github.com' + path, {
    method,
    redirect: 'manual',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: 'Bearer ' + token,
      'User-Agent': 'caf-ausencias-api',
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
    },
    body: data === undefined ? undefined : JSON.stringify(data),
  }).catch(() => { throw new Error(stage + '_network'); });
}

async function installationToken(env) {
  if (!env.GITHUB_APP_ID || !env.GITHUB_PRIVATE_KEY) throw new Error('missing_bindings');
  const now = Math.floor(Date.now() / 1000);
  const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url');
  const payload = encode({ alg: 'RS256', typ: 'JWT' }) + '.' +
    encode({ iat: now - 60, exp: now + 480, iss: String(env.GITHUB_APP_ID) });
  const key = env.GITHUB_PRIVATE_KEY.trim();
  let signature;
  try {
    signature = sign('RSA-SHA256', Buffer.from(payload), key).toString('base64url');
  } catch {
    throw new Error('invalid_private_key');
  }
  const jwt = payload + '.' + signature;
  const installation = await github(repo + '/installation', jwt);
  if (!installation.ok) throw new Error('installation_http_' + installation.status);
  const { id } = await installation.json().catch(() => { throw new Error('installation_invalid_response'); });
  if (!Number.isSafeInteger(id)) throw new Error('installation_invalid_response');
  const response = await github('/app/installations/' + id + '/access_tokens', jwt, 'POST', {
    repositories: ['ausencias'],
    permissions: { contents: 'write' },
  });
  if (!response.ok) throw new Error('token_http_' + response.status);
  const { token } = await response.json().catch(() => { throw new Error('token_invalid_response'); });
  if (!token) throw new Error('token_invalid_response');
  return token;
}

async function parseBody(request) {
  if (!request.body || Number(request.headers.get('Content-Length')) > limit) throw new Error();
  const reader = request.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let bytes = 0;
  let text = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > limit) throw new Error();
      text += decoder.decode(value, { stream: true });
    }
    return JSON.parse(text + decoder.decode());
  } finally {
    await reader.cancel().catch(() => {});
  }
}

function validDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value + 'T00:00:00Z');
  return Number.isFinite(+date) && date.toISOString().slice(0, 10) === value;
}

function normalizedState(data) {
  const named = (value, max) => typeof value === 'string' && value.trim() && value.length <= max;
  const identified = rows => rows.every(row => row && named(row.id, 200)) &&
    new Set(rows.map(row => row.id)).size === rows.length;
  if (!data || data.version !== 1) return null;
  const { people, records, absenceTypes, holidays } = data;
  if (!Array.isArray(people) || people.length > 1000 || !identified(people) ||
      !people.every(p => named(p.name, 100))) return null;
  if (!Array.isArray(absenceTypes) || absenceTypes.length > 100 ||
      !absenceTypes.every(t => named(t, 60) && t === t.trim())) return null;
  const normalize = t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
  if (new Set(absenceTypes.map(normalize)).size !== absenceTypes.length) return null;
  if (!Array.isArray(holidays) || holidays.length > 1000 || !identified(holidays) ||
      !holidays.every(h => named(h.name, 100) && validDate(h.date) &&
        ['Feriado local', 'Ponto facultativo'].includes(h.kind))) return null;
  const ids = new Set(people.map(p => p.id));
  const types = new Set(absenceTypes);
  if (!Array.isArray(records) || records.length > 20000 || !identified(records) ||
      !records.every(r => ids.has(r.person) && types.has(r.type) &&
        validDate(r.start) && validDate(r.end) && r.start <= r.end)) return null;
  return {
    version: 1,
    people: people.map(({ id, name }) => ({ id, name })),
    records: records.map(({ id, person, type, start, end }) => ({ id, person, type, start, end })),
    absenceTypes,
    holidays: holidays.map(({ id, name, date, kind }) => ({ id, name, date, kind })),
  };
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    const file = path === '/save/cgmcaf' || path === '/health/cgmcaf' ? cgmcafFile : cgcafFile;
    if ((path === '/health' || path === '/health/cgmcaf') && request.method === 'GET') {
      try {
        const response = await github(file + '?ref=main', await installationToken(env));
        if (response.ok) return reply(200, { ready: true });
        return reply(503, { ready: false, check: 'file_http_' + response.status });
      } catch (error) {
        const code = error?.message;
        const check = /^(missing_bindings|invalid_private_key|(?:installation|token|file)_(?:network|invalid_response|http_[1-5][0-9]{2}))$/.test(code)
          ? code
          : 'github_request_failed';
        return reply(503, { ready: false, check });
      }
    }
    if (path !== '/save' && path !== '/save/cgmcaf') return reply(404, { error: 'Rota inexistente.' });
    if (request.headers.get('Origin') !== origin) return reply(403, { error: 'Origem inválida.' });
    if (request.method === 'OPTIONS') return reply(204);
    if (request.method !== 'POST') return reply(405, { error: 'Método inválido.' });
    if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get('Content-Type') || '')) {
      return reply(415, { error: 'Envie JSON.' });
    }
    let body;
    try { body = await parseBody(request); } catch {
      return reply(400, { error: 'JSON inválido ou acima do limite de tamanho.' });
    }
    const data = normalizedState(body?.data);
    const sha = body?.sha;
    if (!data || typeof sha !== 'string' || !/^[0-9a-f]{40}$/.test(sha)) {
      return reply(400, { error: 'Dados ou versão da base inválidos.' });
    }
    const content = Buffer.from(JSON.stringify(data, null, 2));
    if (content.byteLength > limit) return reply(413, { error: 'Base acima do limite de tamanho.' });
    try {
      const response = await github(file, await installationToken(env), 'PUT', {
        branch: 'main',
        message: 'Atualizar planejamento de ausências',
        content: content.toString('base64'),
        sha,
      });
      if (response.status === 409 || response.status === 422) {
        return reply(409, { error: 'A base mudou. Exporte um backup e recarregue antes de tentar novamente.' });
      }
      if (!response.ok) throw new Error('File update failed');
      const result = await response.json();
      return reply(200, { sha: result.content.sha });
    } catch {
      return reply(502, { error: 'O GitHub não confirmou o salvamento. Seus dados continuam na tela.' });
    }
  },
};
