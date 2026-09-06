const express = require('express');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const { spawn } = require('child_process');
const { DatabaseSync } = require('node:sqlite');
const https = require('https');
const nodemailer = require('nodemailer');
const cors = require('cors'); // Added for CORS support
require('dotenv').config();

const app = express();
app.disable('x-powered-by');

// ─── Configuration ──────────────────────────────────────────────────────────────
const ADMIN_KEY = process.env.BUILDER_ADMIN_KEY || '';
const ADMIN_KEY_REQUIRED = process.env.NODE_ENV === 'production' || process.env.BUILDER_REQUIRE_AUTH === '1';
const BUILDER_SECRET = process.env.BUILDER_SECRET || '';
const PUBLIC_BASE_URL = String(process.env.PUBLIC_BASE_URL || process.env.RENDER_EXTERNAL_URL || '').replace(/\/$/, '');
const GOOGLE_CLIENT_ID = String(process.env.GOOGLE_CLIENT_ID || '');
const GOOGLE_CLIENT_SECRET = String(process.env.GOOGLE_CLIENT_SECRET || '');
const TELEGRAM_CLIENT_ID = String(process.env.TELEGRAM_CLIENT_ID || '');
const TELEGRAM_CLIENT_SECRET = String(process.env.TELEGRAM_CLIENT_SECRET || '');
const OAUTH_STATE_SECRET = String(process.env.OAUTH_STATE_SECRET || BUILDER_SECRET);
const SMTP_HOST = String(process.env.SMTP_HOST || '');
const SMTP_PORT = Number(process.env.SMTP_PORT || 465);
const SMTP_SECURE = String(process.env.SMTP_SECURE || '1') === '1';
const SMTP_USER = String(process.env.SMTP_USER || '');
const SMTP_PASS = String(process.env.SMTP_PASS || '');
const MAIL_FROM = String(process.env.MAIL_FROM || SMTP_USER || '');
const PASSWORD_RESET_MINUTES = Math.min(Math.max(Number(process.env.PASSWORD_RESET_MINUTES || 30), 10), 120);
const EMAIL_RESET_ENABLED = Boolean(SMTP_HOST && SMTP_USER && SMTP_PASS && MAIL_FROM);

if (ADMIN_KEY_REQUIRED && ADMIN_KEY.length < 16) {
  console.error('BUILDER_ADMIN_KEY must be set and at least 16 characters in production.');
  process.exit(1);
}
if (ADMIN_KEY_REQUIRED && BUILDER_SECRET.length < 32) {
  console.error('BUILDER_SECRET must be set and at least 32 characters in production.');
  process.exit(1);
}
if (ADMIN_KEY_REQUIRED && !PUBLIC_BASE_URL) {
  console.warn('PUBLIC_BASE_URL or RENDER_EXTERNAL_URL is required for OAuth callbacks and gateway callbacks.');
}
if (ADMIN_KEY_REQUIRED && (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET))
  console.warn('Google OAuth is not configured: set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.');
if (ADMIN_KEY_REQUIRED && (!TELEGRAM_CLIENT_ID || !TELEGRAM_CLIENT_SECRET))
  console.warn('Telegram OAuth is not configured: set TELEGRAM_CLIENT_ID and TELEGRAM_CLIENT_SECRET.');
if (ADMIN_KEY_REQUIRED && !EMAIL_RESET_ENABLED)
  console.warn('Password reset email is not configured: set SMTP_HOST, SMTP_USER, SMTP_PASS and MAIL_FROM.');

// ─── Rate limiting store ─────────────────────────────────────────────────────────
const rate = new Map();
setInterval(() => {
  const cutoff = Date.now() - 120000;
  for (const [k, v] of rate) if (v.t < cutoff) rate.delete(k);
}, 60000).unref();

// ─── Helpers ─────────────────────────────────────────────────────────────────────
function clientIp(req) {
  return String(req.socket.remoteAddress || req.headers['x-forwarded-for'] || 'unknown').split(',')[0].trim();
}
function hashText(x) {
  return crypto.createHash('sha256').update(String(x)).digest('hex');
}
function passwordHash(password, salt) {
  return crypto.scryptSync(String(password), Buffer.from(salt, 'hex'), 64).toString('hex');
}
function verifyPassword(password, salt, stored) {
  try {
    const a = Buffer.from(passwordHash(password, salt), 'hex');
    const b = Buffer.from(stored, 'hex');
    return a.length === b.length && crypto.timingSafeEqual(a, b);
  } catch {
    return false;
  }
}
function now() {
  return new Date().toISOString();
}
function finiteMoney(x) {
  const n = Number(x);
  return Number.isFinite(n) && n >= 0 && n <= 100000000 ? n : null;
}
function intId(x) {
  const n = Number(x);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}
function safeName(x) {
  return String(x || '').trim().replace(/[\x00-\x1f\x7f]/g, '').slice(0, 120);
}
function validOwner(x) {
  return /^\d{5,20}$/.test(String(x || ''));
}
function validToken(t) {
  return /^\d{5,20}:[A-Za-z0-9_-]{20,}$/.test(String(t || ''));
}
function publicBot(b) {
  return {
    id: b.id,
    name: b.name,
    username: b.username,
    owner_id: b.owner_id,
    created_at: b.created_at,
    status: b.status,
    uptime_started: b.uptime_started,
    last_error: b.last_error || ''
  };
}
function publicError(e, fallback = 'Request failed') {
  const m = String(e?.message || '').replace(/[\r\n]+/g, ' ').slice(0, 240);
  return m || fallback;
}
function redactLog(s) {
  return String(s || '')
    .replace(/\b\d{5,20}:[A-Za-z0-9_-]{20,}\b/g, '[BOT_TOKEN_REDACTED]')
    .replace(/(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,}]+/gi, '$1=[REDACTED]');
}
function key() {
  return crypto.createHash('sha256').update(BUILDER_SECRET).digest();
}
function enc(s) {
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', key(), iv);
  const d = Buffer.concat([c.update(s, 'utf8'), c.final()]);
  return [iv.toString('base64'), c.getAuthTag().toString('base64'), d.toString('base64')].join('.');
}
function dec(x) {
  const [iv, t, d] = x.split('.');
  const c = crypto.createDecipheriv('aes-256-gcm', key(), Buffer.from(iv, 'base64'));
  c.setAuthTag(Buffer.from(t, 'base64'));
  return Buffer.concat([c.update(Buffer.from(d, 'base64')), c.final()]).toString();
}
function tg(token, method, body = {}) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const r = https.request(
      `https://api.telegram.org/bot${token}/${method}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data)
        },
        timeout: 15000
      },
      (x) => {
        let s = '';
        x.on('data', d => s += d);
        x.on('end', () => {
          try { resolve(JSON.parse(s)); } catch (e) { reject(e); }
        });
      }
    );
    r.on('error', reject);
    r.on('timeout', () => r.destroy(new Error('Telegram API timeout')));
    r.write(data);
    r.end();
  });
}
function dbFor(bot) {
  return new DatabaseSync(bot.db_path);
}
function rows(bot, sql, args = []) {
  const d = dbFor(bot);
  try { return d.prepare(sql).all(...args); } finally { d.close(); }
}
function run(bot, sql, args = []) {
  const d = dbFor(bot);
  try { return d.prepare(sql).run(...args); } finally { d.close(); }
}
function one(bot, sql, args = []) {
  const d = dbFor(bot);
  try { return d.prepare(sql).get(...args); } finally { d.close(); }
}
function getBot(id) {
  return builderDb.prepare('SELECT * FROM bots WHERE id=?').get(Number(id));
}
function accessibleBot(req, id) {
  const b = getBot(id);
  if (!b) return null;
  if (isSuper(req)) return b;
  return b.seller_id && Number(b.seller_id) === Number(req.user.id) ? b : null;
}
function denyBot(req, res, id) {
  const b = getBot(id);
  if (!b) return res.status(404).json({ ok: false, message: 'Bot not found' });
  return res.status(403).json({ ok: false, message: 'You do not have access to this bot.' });
}
function isSuper(req) {
  return req.user?.role === 'superadmin' || req.authMode === 'admin';
}
function activeSubscription(sellerId) {
  const sub = builderDb
    .prepare(
      `SELECT s.*, p.name plan_name, p.days, p.max_bots, p.max_products_per_bot, p.max_stock_keys_per_bot, p.price
       FROM subscriptions s
       JOIN saas_plans p ON p.id = s.plan_id
       WHERE s.seller_id = ? AND s.status = 'active' AND s.expires_at > ?
       ORDER BY s.expires_at DESC LIMIT 1`
    )
    .get(Number(sellerId), now());
  return sub || null;
}
function sellerLimits(sellerId) {
  const sub = activeSubscription(sellerId);
  const ov = builderDb.prepare('SELECT * FROM seller_limits WHERE seller_id=?').get(Number(sellerId));
  return {
    subscription: sub,
    limits: {
      max_bots: ov?.max_bots ?? sub?.max_bots ?? 0,
      max_products_per_bot: ov?.max_products_per_bot ?? sub?.max_products_per_bot ?? 0,
      max_stock_keys_per_bot: ov?.max_stock_keys_per_bot ?? sub?.max_stock_keys_per_bot ?? 0
    }
  };
}
function enforceSellerSubscription(req, res) {
  if (isSuper(req)) return true;
  const x = sellerLimits(req.user.id);
  if (!x.subscription) {
    res.status(402).json({ ok: false, message: 'Active subscription required.', code: 'SUBSCRIPTION_REQUIRED' });
    return false;
  }
  return true;
}
function countBotProducts(b) {
  return Number(one(b, 'SELECT COUNT(*) c FROM products').c || 0);
}
function countBotKeys(b) {
  return Number(one(b, 'SELECT COUNT(*) c FROM stock_keys').c || 0);
}
function newSession(sellerId) {
  const raw = crypto.randomBytes(32).toString('base64url');
  const csrf = crypto.randomBytes(24).toString('base64url');
  builderDb
    .prepare(
      'INSERT INTO sessions(seller_id, token_hash, csrf_hash, created_at, expires_at) VALUES(?,?,?,?,?)'
    )
    .run(sellerId, hashText(raw), hashText(csrf), now(), new Date(Date.now() + 7 * 86400000).toISOString());
  return { raw, csrf };
}
function clearExpiredSessions() {
  builderDb.prepare("DELETE FROM sessions WHERE expires_at<? OR revoked_at IS NOT NULL").run(now());
}
function sessionFrom(req) {
  const raw = String((req.headers.cookie || '').split(';').map(x => x.trim()).find(x => x.startsWith('sb_session=')) || '').slice(11);
  if (!raw) return null;
  clearExpiredSessions();
  const row = builderDb
    .prepare(
      'SELECT s.*, a.username, a.email, a.role, a.active FROM sessions s JOIN sellers a ON a.id = s.seller_id WHERE s.token_hash = ? AND s.expires_at > ? AND s.revoked_at IS NULL AND a.active = 1'
    )
    .get(hashText(raw), now());
  if (!row) return null;
  return { id: row.seller_id, username: row.username, email: row.email || '', role: row.role, csrfHash: row.csrf_hash };
}
function cookieForSession(sess) {
  return `sb_session=${sess.raw}; Path=/; HttpOnly; SameSite=Strict${ADMIN_KEY_REQUIRED ? '; Secure' : ''}; Max-Age=604800`;
}
function redirectBase() {
  return PUBLIC_BASE_URL || '';
}
function randomState() {
  return crypto.randomBytes(32).toString('base64url');
}
function pkceVerifier() {
  return crypto.randomBytes(32).toString('base64url');
}
function pkceChallenge(v) {
  return crypto.createHash('sha256').update(v).digest('base64url');
}
function saveOAuthState(provider, verifier = '') {
  const raw = randomState();
  builderDb
    .prepare(
      'INSERT INTO oauth_states(provider, state_hash, code_verifier, created_at, expires_at) VALUES(?,?,?,?,?)'
    )
    .run(provider, hashText(raw), verifier, now(), new Date(Date.now() + 10 * 60 * 1000).toISOString());
  builderDb.prepare('DELETE FROM oauth_states WHERE expires_at<?').run(now());
  return raw;
}
function takeOAuthState(provider, raw) {
  const row = builderDb
    .prepare('SELECT * FROM oauth_states WHERE provider=? AND state_hash=? AND expires_at>?')
    .get(provider, hashText(raw), now());
  if (row) builderDb.prepare('DELETE FROM oauth_states WHERE id=?').run(row.id);
  return row || null;
}
function oauthUrl(pathname, params) {
  const u = new URL(pathname);
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null && v !== '') u.searchParams.set(k, String(v));
  return u.toString();
}
async function httpJson(url, options = {}) {
  const r = await fetch(url, {
    ...options,
    redirect: 'manual',
    signal: AbortSignal.timeout(15000),
    headers: { accept: 'application/json', ...(options.headers || {}) }
  });
  const text = await r.text();
  let data = {};
  try { data = JSON.parse(text); } catch {}
  if (!r.ok) return { ok: false, status: r.status, data, text };
  return { ok: true, status: r.status, data, text };
}
function providerUsernameBase(provider, profile) {
  const raw = provider === 'telegram'
    ? (profile.username || `telegram_${profile.id}`)
    : (profile.email || `google_${profile.sub}`);
  return String(raw).toLowerCase().replace(/[^a-z0-9_.-]/g, '_').slice(0, 24) || `${provider}_user`;
}
function uniqueUsername(base) {
  let b = String(base).slice(0, 32);
  if (!builderDb.prepare('SELECT 1 FROM sellers WHERE username=?').get(b)) return b;
  for (let i = 1; i < 10000; i++) {
    const suffix = String(i);
    const x = b.slice(0, 32 - suffix.length - 1) + '_' + suffix;
    if (!builderDb.prepare('SELECT 1 FROM sellers WHERE username=?').get(x)) return x;
  }
  return `${b.slice(0, 24)}_${crypto.randomBytes(4).toString('hex')}`;
}
function ensureSellerForSocial(provider, profile) {
  const sub = String(profile.sub || profile.id || '');
  if (!sub) throw new Error('OAuth identity is missing a stable user ID.');
  let s = builderDb
    .prepare(
      'SELECT s.* FROM sellers s JOIN social_identities i ON i.seller_id = s.id WHERE i.provider = ? AND i.provider_sub = ? AND s.active = 1'
    )
    .get(provider, sub);
  if (s) {
    builderDb
      .prepare(
        'UPDATE social_identities SET provider_username=?, provider_email=?, last_login=? WHERE provider=? AND provider_sub=?'
      )
      .run(profile.username || profile.preferred_username || '', profile.email || '', now(), provider, sub);
    builderDb.prepare('UPDATE sellers SET last_login=? WHERE id=?').run(now(), s.id);
    return s;
  }
  const email = String(profile.email || '').trim().toLowerCase();
  if (email) {
    const byEmail = builderDb.prepare('SELECT * FROM sellers WHERE lower(email)=? AND active=1 LIMIT 1').get(email);
    if (byEmail) {
      builderDb
        .prepare(
          'INSERT INTO social_identities(seller_id, provider, provider_sub, provider_username, provider_email, created_at, last_login) VALUES(?,?,?,?,?,?,?)'
        )
        .run(byEmail.id, provider, sub, profile.username || profile.preferred_username || '', email, now(), now());
      builderDb.prepare('UPDATE sellers SET last_login=? WHERE id=?').run(now(), byEmail.id);
      return byEmail;
    }
  }
  const username = uniqueUsername(providerUsernameBase(provider, profile));
  const salt = crypto.randomBytes(16).toString('hex');
  const randomPassword = crypto.randomBytes(32).toString('base64url');
  const id = builderDb
    .prepare(
      'INSERT INTO sellers(username, email, password_hash, password_salt, role, active, created_at, last_login) VALUES(?,?,?,?,?,?,?,?)'
    )
    .run(username, email, passwordHash(randomPassword, salt), salt, 'seller', 1, now(), now()).lastInsertRowid;
  builderDb
    .prepare(
      'INSERT INTO social_identities(seller_id, provider, provider_sub, provider_username, provider_email, created_at, last_login) VALUES(?,?,?,?,?,?,?)'
    )
    .run(id, provider, sub, profile.username || profile.preferred_username || '', email, now(), now());
  const trial = builderDb.prepare("SELECT id FROM saas_plans WHERE name='3 Days' LIMIT 1").get();
  if (trial) {
    builderDb
      .prepare(
        "INSERT INTO subscriptions(seller_id, plan_id, starts_at, expires_at, status, created_at) VALUES(?,?,?,?,?,?)"
      )
      .run(id, trial.id, now(), new Date(Date.now() + 3 * 86400000).toISOString(), 'active', now());
  }
  return builderDb.prepare('SELECT * FROM sellers WHERE id=?').get(id);
}
async function sendResetEmail(to, username, resetUrl) {
  if (!EMAIL_RESET_ENABLED) throw new Error('Password reset email service is not configured.');
  const transporter = nodemailer.createTransport({
    host: SMTP_HOST,
    port: SMTP_PORT,
    secure: SMTP_SECURE,
    auth: { user: SMTP_USER, pass: SMTP_PASS },
    connectionTimeout: 15000,
    greetingTimeout: 15000,
    socketTimeout: 20000
  });
  await transporter.sendMail({
    from: MAIL_FROM,
    to,
    subject: 'Reset your SHIVAM Bot Builder password',
    text: `Hello ${username},\n\nUse this secure link to reset your SHIVAM Bot Builder password:\n${resetUrl}\n\nThis link expires in ${PASSWORD_RESET_MINUTES} minutes and can only be used once.\n\nIf you did not request this, you can ignore this email.`,
    html: `<div style="font-family:Arial,sans-serif;background:#070b16;color:#eaf4ff;padding:28px"><div style="max-width:560px;margin:auto;background:#0e1628;border:1px solid #263c5a;border-radius:18px;padding:28px"><h2 style="margin-top:0;color:#62dcff">SHIVAM BOT BUILDER</h2><p>Hello ${String(username).replace(/[&<>]/g,'')}</p><p>We received a request to reset your password.</p><p><a href="${resetUrl}" style="display:inline-block;padding:12px 20px;border-radius:10px;background:linear-gradient(100deg,#078eff,#5854ff,#b53dff);color:#fff;text-decoration:none;font-weight:700">Reset Password</a></p><p style="color:#8293ad;font-size:13px">This link expires in ${PASSWORD_RESET_MINUTES} minutes and can only be used once.</p></div></div>`
  });
}
async function googleProfileFromCode(code, stateRow) {
  if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) throw new Error('Google OAuth is not configured.');
  const redirect = `${redirectBase()}/api/auth/google/callback`;
  const body = new URLSearchParams({
    code,
    client_id: GOOGLE_CLIENT_ID,
    client_secret: GOOGLE_CLIENT_SECRET,
    redirect_uri: redirect,
    grant_type: 'authorization_code'
  });
  const token = await httpJson('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body
  });
  if (!token.ok || !token.data.access_token) throw new Error('Google authorization failed.');
  const u = await httpJson('https://openidconnect.googleapis.com/v1/userinfo', {
    headers: { authorization: `Bearer ${token.data.access_token}` }
  });
  if (!u.ok || !u.data.sub) throw new Error('Google profile verification failed.');
  if (u.data.email_verified !== true) throw new Error('Google account email is not verified.');
  return { sub: u.data.sub, email: u.data.email, preferred_username: u.data.email, name: u.data.name };
}
let telegramJwks = { at: 0, keys: [] };
async function telegramKeys() {
  if (Date.now() - telegramJwks.at < 5 * 60 * 1000 && telegramJwks.keys.length) return telegramJwks.keys;
  const r = await httpJson('https://oauth.telegram.org/.well-known/jwks.json');
  if (!r.ok || !Array.isArray(r.data.keys)) throw new Error('Telegram signing keys could not be loaded.');
  telegramJwks = { at: Date.now(), keys: r.data.keys };
  return telegramJwks.keys;
}
function decodeJwtPart(s) {
  return Buffer.from(String(s).replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8');
}
async function verifyTelegramIdToken(jwt) {
  const parts = String(jwt).split('.');
  if (parts.length !== 3) throw new Error('Telegram identity token is invalid.');
  let header, payload;
  try {
    header = JSON.parse(decodeJwtPart(parts[0]));
    payload = JSON.parse(decodeJwtPart(parts[1]));
  } catch {
    throw new Error('Telegram identity token is invalid.');
  }
  const key = (await telegramKeys()).find(k => k.kid === header.kid && (!header.alg || k.alg === header.alg));
  if (!key) throw new Error('Telegram signing key not found.');
  function joseEcSigToDer(sig) {
    if (sig.length !== 64) throw new Error('Invalid ES256 signature.');
    const trim = (b) => {
      let x = Buffer.from(b);
      while (x.length > 1 && x[0] === 0) x = x.subarray(1);
      if (x[0] & 0x80) x = Buffer.concat([Buffer.from([0]), x]);
      return x;
    };
    const r = trim(sig.subarray(0, 32));
    const ss = trim(sig.subarray(32));
    const body = Buffer.concat([Buffer.from([0x02, r.length]), r, Buffer.from([0x02, ss.length]), ss]);
    return Buffer.concat([Buffer.from([0x30, body.length]), body]);
  }
  const publicKey = crypto.createPublicKey({ key, format: 'jwk' });
  const data = `${parts[0]}.${parts[1]}`;
  const sig = Buffer.from(parts[2].replace(/-/g, '+').replace(/_/g, '/'), 'base64');
  let valid = false;
  if (header.alg === 'RS256') valid = crypto.verify('RSA-SHA256', Buffer.from(data), publicKey, sig);
  else if (header.alg === 'ES256') valid = crypto.verify('sha256', Buffer.from(data), publicKey, joseEcSigToDer(sig));
  else if (header.alg === 'EdDSA') valid = crypto.verify(null, Buffer.from(data), publicKey, sig);
  if (!valid) throw new Error('Telegram identity signature verification failed.');
  const nowSec = Math.floor(Date.now() / 1000);
  if (
    payload.iss !== 'https://oauth.telegram.org' ||
    String(payload.aud) !== String(TELEGRAM_CLIENT_ID) ||
    Number(payload.exp || 0) <= nowSec ||
    Number(payload.iat || 0) > nowSec + 120
  ) {
    throw new Error('Telegram identity verification failed.');
  }
  return payload;
}
async function telegramProfileFromCode(code, stateRow) {
  if (!TELEGRAM_CLIENT_ID || !TELEGRAM_CLIENT_SECRET) throw new Error('Telegram OAuth is not configured.');
  const redirect = `${redirectBase()}/api/auth/telegram/callback`;
  const body = new URLSearchParams({
    code,
    client_id: TELEGRAM_CLIENT_ID,
    client_secret: TELEGRAM_CLIENT_SECRET,
    redirect_uri: redirect,
    grant_type: 'authorization_code',
    code_verifier: stateRow.code_verifier
  });
  const token = await httpJson('https://oauth.telegram.org/token', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body
  });
  if (!token.ok || !token.data.id_token) throw new Error('Telegram authorization failed.');
  const profile = await verifyTelegramIdToken(token.data.id_token);
  return { sub: profile.sub || profile.id, id: profile.id, username: profile.preferred_username, name: profile.name };
}
function finishOAuthLogin(res, provider, profile) {
  try {
    const a = ensureSellerForSocial(provider, profile);
    const sess = newSession(a.id);
    res.setHeader('Set-Cookie', cookieForSession(sess));
    return res.redirect('/?auth=success');
  } catch (e) {
    return res.redirect('/?auth_error=' + encodeURIComponent(e.message || 'OAuth login failed'));
  }
}
function diskFreeBytes(p) {
  try {
    return Number(fs.statfsSync(p).bavail) * Number(fs.statfsSync(p).bsize);
  } catch {
    return null;
  }
}
function startBot(id) {
  const bot = builderDb.prepare('SELECT * FROM bots WHERE id=?').get(id);
  if (!bot) return false;
  const existing = children.get(id);
  if (existing && existing.exitCode === null) return true;
  if (existing) children.delete(id);
  ensureBotDb(bot);
  const dir = path.dirname(bot.db_path);
  const token = dec(bot.token_enc);
  const base = String(process.env.PUBLIC_BASE_URL || process.env.RENDER_EXTERNAL_URL || '').replace(/\/$/, '');
  const callbackUrl = base ? `${base}/api/gateway/callback/${id}/${bot.gateway_callback_secret}` : '';
  const generation = crypto.randomBytes(8).toString('hex');
  childGeneration.set(id, generation);
  const child = spawn(
    py,
    ['bot.py'],
    {
      cwd: dir,
      env: {
        ...process.env,
        BOT_TOKEN: token,
        ADMIN_USER_ID: String(bot.owner_id),
        DB_PATH: bot.db_path,
        STORE_TIMEZONE: 'Asia/Kolkata',
        BOT_HEARTBEAT_PATH: path.join(dir, 'heartbeat'),
        GATEWAY_CALLBACK_URL: callbackUrl,
        IMAP_ENABLED: '0',
        IMAP_REQUIRE_TRUSTED_SENDER: '1',
        IMAP_REQUIRE_RECIPIENT_MATCH: '1',
        PYTHONUNBUFFERED: '1'
      },
      stdio: ['ignore', 'pipe', 'pipe']
    }
  );
  const log = path.join(dir, 'bot.log');
  const MAX_BOT_LOG_BYTES = 2 * 1024 * 1024;
  const append = (d) => {
    try {
      fs.appendFileSync(log, redactLog(d));
      const st = fs.statSync(log);
      if (st.size > MAX_BOT_LOG_BYTES) {
        const buf = fs.readFileSync(log);
        fs.writeFileSync(log, buf.subarray(Math.max(0, buf.length - MAX_BOT_LOG_BYTES)));
      }
    } catch {}
  };
  child.stdout.on('data', d => append(d));
  child.stderr.on('data', d => {
    const safe = redactLog(d);
    append(safe);
    try {
      builderDb.prepare('UPDATE bots SET last_error=? WHERE id=?').run(safe.slice(-1500), id);
    } catch {}
  });
  child.on('exit', (code, signal) => {
    const current = childGeneration.get(id) === generation && children.get(id) === child;
    if (current) children.delete(id);
    if (!current) return;
    const b = builderDb.prepare('SELECT status FROM bots WHERE id=?').get(id);
    const shouldRestart = Boolean(b && b.status === 'online');
    builderDb
      .prepare("UPDATE bots SET status='offline',last_error=? WHERE id=?")
      .run(`Bot process exited (code=${code}, signal=${signal || 'none'})`.slice(0, 1500), id);
    if (shouldRestart) {
      setTimeout(() => {
        try {
          const latest = builderDb.prepare('SELECT status FROM bots WHERE id=?').get(id);
          if (latest && latest.status === 'offline') startBot(id);
        } catch (e) {
          try { builderDb.prepare('UPDATE bots SET last_error=? WHERE id=?').run(publicError(e), id); } catch {}
        }
      }, 3000);
    }
  });
  children.set(id, child);
  builderDb.prepare("UPDATE bots SET status='online', uptime_started=?, last_error='' WHERE id=?").run(now(), id);
  restartState.set(id, { startedAt: Date.now(), attempt: 0, nextAt: 0 });
  return true;
}
function stopBot(id) {
  const c = children.get(id);
  if (c) { c.kill('SIGTERM'); children.delete(id); }
  builderDb.prepare("UPDATE bots SET status='offline' WHERE id=?").run(id);
  return true;
}
function restartBot(id) {
  stopBot(id);
  return startBot(id);
}
function enforceExpiry() {
  const expired = builderDb.prepare("SELECT DISTINCT seller_id FROM subscriptions WHERE status='active' AND expires_at<=?").all(now());
  for (const x of expired) {
    builderDb
      .prepare("UPDATE subscriptions SET status='expired' WHERE seller_id=? AND status='active' AND expires_at<=?")
      .run(x.seller_id, now());
    const bs = builderDb.prepare('SELECT id FROM bots WHERE seller_id=?').all(x.seller_id);
    for (const b of bs) stopBot(b.id);
  }
}
function ensureBotDb(bot) {
  const dir = path.dirname(bot.db_path);
  fs.mkdirSync(dir, { recursive: true });
  try { fs.rmSync(path.join(dir, '.env'), { force: true }); } catch {}
}

// ─── Data directories ────────────────────────────────────────────────────────────
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const BOT_DIR = path.join(DATA_DIR, 'bots');
fs.mkdirSync(BOT_DIR, { recursive: true });

// ─── SQLite Database (builder) ──────────────────────────────────────────────────
const builderDb = new DatabaseSync(path.join(DATA_DIR, 'builder.sqlite'));
builderDb.exec(`PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS bots(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  username TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  token_enc TEXT NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'offline',
  uptime_started TEXT,
  last_error TEXT DEFAULT '',
  db_path TEXT NOT NULL,
  gateway_callback_secret TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sellers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  password_salt TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'seller',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  last_login TEXT
);
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seller_id INTEGER NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  csrf_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  FOREIGN KEY(seller_id) REFERENCES sellers(id)
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
CREATE TABLE IF NOT EXISTS saas_plans(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  days INTEGER NOT NULL,
  max_bots INTEGER NOT NULL,
  max_products_per_bot INTEGER NOT NULL,
  max_stock_keys_per_bot INTEGER NOT NULL,
  price REAL NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subscriptions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seller_id INTEGER NOT NULL,
  plan_id INTEGER NOT NULL,
  starts_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  FOREIGN KEY(seller_id) REFERENCES sellers(id),
  FOREIGN KEY(plan_id) REFERENCES saas_plans(id)
);
CREATE TABLE IF NOT EXISTS invoices(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seller_id INTEGER NOT NULL,
  plan_id INTEGER,
  amount REAL NOT NULL,
  commission_rate REAL NOT NULL DEFAULT 0,
  commission_amount REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  external_ref TEXT,
  created_at TEXT NOT NULL,
  paid_at TEXT,
  FOREIGN KEY(seller_id) REFERENCES sellers(id),
  FOREIGN KEY(plan_id) REFERENCES saas_plans(id)
);
CREATE TABLE IF NOT EXISTS commission_ledger(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seller_id INTEGER NOT NULL,
  invoice_id INTEGER,
  amount REAL NOT NULL,
  type TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(seller_id) REFERENCES sellers(id),
  FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);
CREATE TABLE IF NOT EXISTS seller_limits(
  seller_id INTEGER PRIMARY KEY,
  max_bots INTEGER,
  max_products_per_bot INTEGER,
  max_stock_keys_per_bot INTEGER,
  FOREIGN KEY(seller_id) REFERENCES sellers(id)
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_seller ON subscriptions(seller_id, status, expires_at);
CREATE INDEX IF NOT EXISTS idx_invoices_seller ON invoices(seller_id, created_at);
`);
// Seed plans
const seedPlans = [
  ['3 Days', 3, 1, 25, 500, 99],
  ['1 Month', 30, 3, 100, 2000, 299],
  ['3 Months', 90, 10, 500, 10000, 699],
  ['12 Months', 365, 50, 2000, 50000, 1499]
];
for (const z of seedPlans) {
  try {
    builderDb
      .prepare(
        'INSERT OR IGNORE INTO saas_plans(name, days, max_bots, max_products_per_bot, max_stock_keys_per_bot, price, active, created_at) VALUES(?,?,?,?,?,?,?,?)'
      )
      .run(z[0], z[1], z[2], z[3], z[4], z[5], 1, now());
  } catch {}
}
// Migrations
try {
  const cols = builderDb.prepare('PRAGMA table_info(bots)').all().map(x => x.name);
  if (!cols.includes('seller_id')) builderDb.exec('ALTER TABLE bots ADD COLUMN seller_id INTEGER');
  if (!cols.includes('gateway_callback_secret')) builderDb.exec("ALTER TABLE bots ADD COLUMN gateway_callback_secret TEXT DEFAULT ''");
  builderDb.exec('CREATE INDEX IF NOT EXISTS idx_bots_seller_id ON bots(seller_id)');
  for (const b of builderDb.prepare("SELECT id FROM bots WHERE gateway_callback_secret IS NULL OR gateway_callback_secret=''").all()) {
    builderDb.prepare('UPDATE bots SET gateway_callback_secret=? WHERE id=?').run(crypto.randomBytes(24).toString('hex'), b.id);
  }
} catch (e) {
  console.error('SELLER_MIGRATION_ERROR', e.message);
  process.exit(1);
}
try { builderDb.exec("ALTER TABLE sellers ADD COLUMN email TEXT"); } catch {}
try { builderDb.exec("CREATE UNIQUE INDEX IF NOT EXISTS idx_sellers_email ON sellers(email) WHERE email IS NOT NULL AND email!=''"); } catch {}
builderDb.exec(`
CREATE TABLE IF NOT EXISTS social_identities(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seller_id INTEGER NOT NULL,
  provider TEXT NOT NULL,
  provider_sub TEXT NOT NULL,
  provider_username TEXT,
  provider_email TEXT,
  created_at TEXT NOT NULL,
  last_login TEXT,
  UNIQUE(provider, provider_sub),
  FOREIGN KEY(seller_id) REFERENCES sellers(id)
);
CREATE INDEX IF NOT EXISTS idx_social_seller ON social_identities(seller_id);
CREATE TABLE IF NOT EXISTS oauth_states(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  state_hash TEXT NOT NULL UNIQUE,
  code_verifier TEXT,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_oauth_state_exp ON oauth_states(expires_at);
CREATE TABLE IF NOT EXISTS password_reset_tokens(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seller_id INTEGER NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_at TEXT,
  FOREIGN KEY(seller_id) REFERENCES sellers(id)
);
CREATE INDEX IF NOT EXISTS idx_reset_token ON password_reset_tokens(token_hash, expires_at);
`);

// ─── Process state ──────────────────────────────────────────────────────────────
const children = new Map();
const childGeneration = new Map();
const restartState = new Map();
const STARTUP_GRACE_MS = 180000;
const HEARTBEAT_STALE_MS = 150000;
const py = process.env.PYTHON_BIN || 'python3';

// ─── Middleware ──────────────────────────────────────────────────────────────────
app.use(cors()); // Enable CORS
app.use(express.json({ limit: '2mb' }));
app.use(express.urlencoded({ extended: true, limit: '2mb' }));
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  next();
});

// Rate limiting
function rateLimit(max, windowMs, prefix) {
  return (req, res, next) => {
    const k = prefix + ':' + clientIp(req);
    const nowMs = Date.now();
    const x = rate.get(k) || { t: nowMs, n: 0 };
    if (nowMs - x.t > windowMs) { x.t = nowMs; x.n = 0; }
    x.n++;
    rate.set(k, x);
    if (x.n > max) return res.status(429).json({ ok: false, message: 'Too many requests. Try again shortly.' });
    next();
  };
}
app.use((req, res, next) => {
  if (!req.path.startsWith('/api/')) return next();
  return rateLimit(240, 60000, 'api')(req, res, next);
});
app.use((req, res, next) => {
  if (!req.path.startsWith('/api/auth/')) return next();
  return rateLimit(12, 60000, 'auth')(req, res, next);
});

// ─── Authentication middleware ──────────────────────────────────────────────────
function auth(req, res, next) {
  // Public paths: health, auth endpoints, gateway callbacks
  if (req.path === '/api/health' ||
      (req.method === 'GET' && req.path === '/') ||
      req.path === '/api/auth/login' ||
      req.path === '/api/auth/register' ||
      req.path === '/api/auth/logout' ||
      req.path === '/api/auth/forgot' ||
      req.path === '/api/auth/reset' ||
      req.path === '/api/auth/google/start' ||
      req.path === '/api/auth/google/callback' ||
      req.path === '/api/auth/telegram/start' ||
      req.path === '/api/auth/telegram/callback' ||
      req.path.startsWith('/api/gateway/callback/')) {
    return next();
  }
  // Allow all non-API routes (static assets, frontend) without authentication
  if (!req.path.startsWith('/api/')) {
    return next();
  }
  // Admin key authentication (if required)
  if (ADMIN_KEY_REQUIRED) {
    const supplied = String(req.headers['x-builder-key'] || '');
    if (ADMIN_KEY && supplied.length >= 16 && supplied.length === ADMIN_KEY.length &&
        crypto.timingSafeEqual(Buffer.from(supplied), Buffer.from(ADMIN_KEY))) {
      req.authMode = 'admin';
      req.user = { role: 'superadmin', username: 'admin' };
      return next();
    }
  } else if (!ADMIN_KEY_REQUIRED) {
    req.authMode = 'admin';
    req.user = { role: 'superadmin', username: 'admin' };
    return next();
  }
  // Session-based authentication
  const u = sessionFrom(req);
  if (!u) return res.status(401).json({ ok: false, message: 'Authentication required.' });
  if (req.method !== 'GET' && req.method !== 'HEAD' && req.method !== 'OPTIONS') {
    const csrf = String(req.headers['x-csrf-token'] || '');
    if (!csrf || hashText(csrf) !== u.csrfHash) {
      return res.status(403).json({ ok: false, message: 'CSRF validation failed.' });
    }
  }
  req.user = u;
  req.authMode = 'seller';
  next();
}
app.use(auth);

// ─── Static files and frontend routes (served before auth? Actually auth skips non-API) ──
app.use(express.static(path.join(__dirname, 'public')));

// Root route – serve index.html
app.get('/', (req, res) => {
  const file = path.join(__dirname, 'public', 'index.html');
  if (!fs.existsSync(file)) return res.status(500).type('text/plain').send('Frontend file missing: public/index.html');
  res.sendFile(file);
});

// Catch-all for SPA – serve index.html for any non-API GET request
app.get('*', (req, res) => {
  if (req.path.startsWith('/api/')) return next(); // Should not reach here for API
  const file = path.join(__dirname, 'public', 'index.html');
  if (!fs.existsSync(file)) return res.status(500).type('text/plain').send('Frontend file missing: public/index.html');
  res.sendFile(file);
});

// ─── API Routes ──────────────────────────────────────────────────────────────────

// Health
app.get('/api/health', (q, r) => {
  const free = diskFreeBytes(DATA_DIR || __dirname);
  r.json({
    ok: true,
    status: 'online',
    bots: children.size,
    time: now(),
    storage_free_mb: free === null ? null : Math.floor(free / 1048576),
    storage_ok: free === null ? true : free > 100 * 1048576,
    oauth: {
      google: Boolean(GOOGLE_CLIENT_ID && GOOGLE_CLIENT_SECRET),
      telegram: Boolean(TELEGRAM_CLIENT_ID && TELEGRAM_CLIENT_SECRET),
      password_reset: EMAIL_RESET_ENABLED
    }
  });
});

// ─── Auth endpoints ──────────────────────────────────────────────────────────────
app.post('/api/auth/register', (req, res) => {
  const username = safeName(req.body?.username).toLowerCase();
  const email = String(req.body?.email || '').trim().toLowerCase();
  const password = String(req.body?.password || '');
  if (!/^[a-z0-9_.-]{3,32}$/.test(username) ||
      !/^\S+@\S+\.\S+$/.test(email) ||
      password.length < 10 || password.length > 200) {
    return res.status(400).json({
      ok: false,
      message: 'Enter a valid email, username 3-32 characters, and password of at least 10 characters.'
    });
  }
  const salt = crypto.randomBytes(16).toString('hex');
  try {
    const id = builderDb
      .prepare(
        'INSERT INTO sellers(username, email, password_hash, password_salt, role, active, created_at) VALUES(?,?,?,?,?,?,?)'
      )
      .run(username, email, passwordHash(password, salt), salt, 'seller', 1, now()).lastInsertRowid;
    const trial = builderDb.prepare("SELECT id FROM saas_plans WHERE name='3 Days' LIMIT 1").get();
    if (trial) {
      builderDb
        .prepare(
          "INSERT INTO subscriptions(seller_id, plan_id, starts_at, expires_at, status, created_at) VALUES(?,?,?,?,?,?)"
        )
        .run(id, trial.id, now(), new Date(Date.now() + 3 * 86400000).toISOString(), 'active', now());
    }
    const sess = newSession(id);
    res.setHeader('Set-Cookie', cookieForSession(sess));
    res.json({ ok: true, user: { id, username, email, role: 'seller' }, csrf: sess.csrf });
  } catch (e) {
    res.status(409).json({ ok: false, message: 'Username or email is already in use.' });
  }
});

app.post('/api/auth/login', (req, res) => {
  const identity = String(req.body?.username || '').trim().toLowerCase();
  const password = String(req.body?.password || '');
  const a = builderDb
    .prepare("SELECT * FROM sellers WHERE (username=? OR lower(COALESCE(email,''))=?) AND active=1 LIMIT 1")
    .get(identity, identity);
  if (!a || !verifyPassword(password, a.password_salt, a.password_hash)) {
    return res.status(401).json({ ok: false, message: 'Invalid username/email or password.' });
  }
  builderDb.prepare('UPDATE sellers SET last_login=? WHERE id=?').run(now(), a.id);
  const sess = newSession(a.id);
  res.setHeader('Set-Cookie', cookieForSession(sess));
  res.json({ ok: true, user: { id: a.id, username: a.username, email: a.email || '', role: a.role }, csrf: sess.csrf });
});

app.get('/api/auth/google/start', (req, res) => {
  if (!PUBLIC_BASE_URL) return res.status(503).json({ ok: false, message: 'PUBLIC_BASE_URL is required for Google OAuth.' });
  if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) return res.status(503).json({ ok: false, message: 'Google OAuth is not configured.' });
  const state = saveOAuthState('google');
  const redirect = `${redirectBase()}/api/auth/google/callback`;
  res.redirect(oauthUrl('https://accounts.google.com/o/oauth2/v2/auth', {
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: redirect,
    response_type: 'code',
    scope: 'openid email profile',
    state,
    access_type: 'online',
    prompt: 'select_account'
  }));
});

app.get('/api/auth/google/callback', async (req, res) => {
  try {
    const state = String(req.query.state || '');
    const code = String(req.query.code || '');
    const row = takeOAuthState('google', state);
    if (!row || !code) return res.redirect('/?auth_error=Invalid+Google+OAuth+state');
    const profile = await googleProfileFromCode(code, row);
    finishOAuthLogin(res, 'google', profile);
  } catch (e) {
    res.redirect('/?auth_error=' + encodeURIComponent(e.message || 'Google login failed'));
  }
});

app.get('/api/auth/telegram/start', (req, res) => {
  if (!PUBLIC_BASE_URL) return res.status(503).json({ ok: false, message: 'PUBLIC_BASE_URL is required for Telegram OAuth.' });
  if (!TELEGRAM_CLIENT_ID || !TELEGRAM_CLIENT_SECRET) return res.status(503).json({ ok: false, message: 'Telegram OAuth is not configured.' });
  const verifier = pkceVerifier();
  const state = saveOAuthState('telegram', verifier);
  const challenge = pkceChallenge(verifier);
  const redirect = `${redirectBase()}/api/auth/telegram/callback`;
  res.redirect(oauthUrl('https://oauth.telegram.org/auth', {
    client_id: TELEGRAM_CLIENT_ID,
    redirect_uri: redirect,
    response_type: 'code',
    scope: 'openid profile',
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256'
  }));
});

app.get('/api/auth/telegram/callback', async (req, res) => {
  try {
    const state = String(req.query.state || '');
    const code = String(req.query.code || '');
    const row = takeOAuthState('telegram', state);
    if (!row || !code) return res.redirect('/?auth_error=Invalid+Telegram+OAuth+state');
    const profile = await telegramProfileFromCode(code, row);
    finishOAuthLogin(res, 'telegram', profile);
  } catch (e) {
    res.redirect('/?auth_error=' + encodeURIComponent(e.message || 'Telegram login failed'));
  }
});

app.post('/api/auth/forgot', async (req, res) => {
  const identity = String(req.body?.identity || req.body?.email || '').trim().toLowerCase();
  if (!identity) return res.status(400).json({ ok: false, message: 'Enter your username or email address.' });
  const a = builderDb
    .prepare("SELECT * FROM sellers WHERE (lower(username)=? OR lower(COALESCE(email,''))=?) AND active=1 LIMIT 1")
    .get(identity, identity);
  if (a && a.email && EMAIL_RESET_ENABLED) {
    builderDb.prepare("DELETE FROM password_reset_tokens WHERE seller_id=? OR expires_at<?").run(a.id, now());
    const raw = crypto.randomBytes(32).toString('base64url');
    builderDb
      .prepare(
        'INSERT INTO password_reset_tokens(seller_id, token_hash, created_at, expires_at) VALUES(?,?,?,?)'
      )
      .run(a.id, hashText(raw), now(), new Date(Date.now() + PASSWORD_RESET_MINUTES * 60000).toISOString());
    const resetUrl = `${redirectBase()}/?reset=${encodeURIComponent(raw)}`;
    try {
      await sendResetEmail(a.email, a.username, resetUrl);
    } catch (e) {
      builderDb.prepare('DELETE FROM password_reset_tokens WHERE token_hash=?').run(hashText(raw));
      console.error('PASSWORD_RESET_EMAIL_ERROR', e.message);
    }
  }
  res.json({ ok: true, message: 'If the account exists and has a verified email, a password reset link has been sent.' });
});

app.post('/api/auth/reset', async (req, res) => {
  const token = String(req.body?.token || '');
  const password = String(req.body?.password || '');
  if (!token || password.length < 10 || password.length > 200) {
    return res.status(400).json({ ok: false, message: 'Invalid reset request or password must be at least 10 characters.' });
  }
  const row = builderDb
    .prepare('SELECT * FROM password_reset_tokens WHERE token_hash=? AND expires_at>? AND used_at IS NULL')
    .get(hashText(token), now());
  if (!row) return res.status(400).json({ ok: false, message: 'This reset link is invalid or expired.' });
  const salt = crypto.randomBytes(16).toString('hex');
  builderDb
    .prepare('UPDATE sellers SET password_hash=?, password_salt=? WHERE id=? AND active=1')
    .run(passwordHash(password, salt), salt, row.seller_id);
  builderDb.prepare('UPDATE password_reset_tokens SET used_at=? WHERE id=?').run(now(), row.id);
  builderDb.prepare('UPDATE sessions SET revoked_at=? WHERE seller_id=? AND revoked_at IS NULL').run(now(), row.seller_id);
  const sess = newSession(row.seller_id);
  const a = builderDb.prepare('SELECT id, username, email, role FROM sellers WHERE id=?').get(row.seller_id);
  res.setHeader('Set-Cookie', cookieForSession(sess));
  res.json({ ok: true, user: a, csrf: sess.csrf });
});

app.post('/api/auth/logout', (req, res) => {
  const u = sessionFrom(req);
  if (u) {
    const cookie = String((req.headers.cookie || '').split(';').map(x => x.trim()).find(x => x.startsWith('sb_session=')) || '').slice(11);
    builderDb.prepare('UPDATE sessions SET revoked_at=? WHERE token_hash=?').run(now(), hashText(cookie));
  }
  res.setHeader('Set-Cookie', 'sb_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0');
  res.json({ ok: true });
});

app.get('/api/auth/me', (req, res) => {
  if (req.authMode === 'admin') {
    return res.json({ ok: true, user: { username: 'admin', role: 'superadmin' }, auth: 'admin' });
  }
  if (req.user) {
    const raw = crypto.randomBytes(24).toString('base64url');
    const cookie = String((req.headers.cookie || '').split(';').map(x => x.trim()).find(x => x.startsWith('sb_session=')) || '').slice(11);
    if (cookie) {
      builderDb
        .prepare('UPDATE sessions SET csrf_hash=? WHERE token_hash=? AND revoked_at IS NULL')
        .run(hashText(raw), hashText(cookie));
    }
    return res.json({
      ok: true,
      user: { id: req.user.id, username: req.user.username, email: req.user.email || '', role: req.user.role },
      auth: 'seller',
      csrf: raw
    });
  }
  res.status(401).json({ ok: false, message: 'Authentication required.' });
});

// ─── SAAS & billing ─────────────────────────────────────────────────────────────
app.get('/api/saas/me', (q, r) => {
  if (isSuper(q)) return r.json({ ok: true, role: 'superadmin' });
  const x = sellerLimits(q.user.id);
  r.json({
    ok: true,
    user: { id: q.user.id, username: q.user.username, role: q.user.role },
    subscription: x.subscription ? {
      id: x.subscription.id,
      plan: x.subscription.plan_name,
      starts_at: x.subscription.starts_at,
      expires_at: x.subscription.expires_at,
      status: x.subscription.status,
      price: x.subscription.price
    } : null,
    limits: x.limits
  });
});

app.get('/api/saas/plans', (q, r) => {
  r.json({
    ok: true,
    plans: builderDb
      .prepare(
        'SELECT id, name, days, max_bots, max_products_per_bot, max_stock_keys_per_bot, price, active FROM saas_plans WHERE active=1 ORDER BY days'
      )
      .all()
  });
});

app.post('/api/billing/invoices', (q, r) => {
  const planId = intId(q.body?.plan_id);
  const p = builderDb.prepare('SELECT * FROM saas_plans WHERE id=? AND active=1').get(planId);
  if (!p) return r.status(404).json({ ok: false, message: 'Plan not found.' });
  const amount = finiteMoney(p.price);
  const ref = safeName(q.body?.external_ref || '').slice(0, 200);
  const id = builderDb
    .prepare(
      "INSERT INTO invoices(seller_id, plan_id, amount, commission_rate, commission_amount, status, external_ref, created_at) VALUES(?,?,?,?,?,?,?,?)"
    )
    .run(q.user.id, p.id, amount, 0, 0, 'pending', ref, now()).lastInsertRowid;
  r.json({ ok: true, invoice: { id, plan: p.name, amount, status: 'pending' } });
});

app.get('/api/billing/invoices', (q, r) => {
  const rows = builderDb
    .prepare(
      'SELECT i.*, p.name plan_name FROM invoices i LEFT JOIN saas_plans p ON p.id=i.plan_id WHERE i.seller_id=? ORDER BY i.id DESC LIMIT 100'
    )
    .all(q.user.id);
  r.json({ ok: true, invoices: rows });
});

// ─── Admin routes ───────────────────────────────────────────────────────────────
app.post('/api/admin/plans', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  const x = q.body || {};
  const name = safeName(x.name);
  const days = Math.floor(Number(x.days));
  const maxBots = Math.floor(Number(x.max_bots));
  const maxProducts = Math.floor(Number(x.max_products_per_bot));
  const maxKeys = Math.floor(Number(x.max_stock_keys_per_bot));
  const price = finiteMoney(x.price);
  if (!name || !Number.isInteger(days) || days < 1 || days > 36500 ||
      ![maxBots, maxProducts, maxKeys].every(v => Number.isInteger(v) && v >= 0) ||
      price === null) {
    return r.status(400).json({ ok: false, message: 'Invalid plan fields.' });
  }
  try {
    const id = builderDb
      .prepare(
        'INSERT INTO saas_plans(name, days, max_bots, max_products_per_bot, max_stock_keys_per_bot, price, active, created_at) VALUES(?,?,?,?,?,?,?,?)'
      )
      .run(name, days, maxBots, maxProducts, maxKeys, price, 1, now()).lastInsertRowid;
    r.json({ ok: true, plan: { id, name, days, max_bots: maxBots, max_products_per_bot: maxProducts, max_stock_keys_per_bot: maxKeys, price } });
  } catch {
    r.status(409).json({ ok: false, message: 'Plan name already exists.' });
  }
});

app.put('/api/admin/plans/:id', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  const id = intId(q.params.id);
  if (!id) return r.status(400).json({ ok: false, message: 'Invalid plan ID.' });
  const x = q.body || {};
  const fields = [];
  const args = [];
  for (const [k, sql] of [
    ['name', 'name'],
    ['days', 'days'],
    ['max_bots', 'max_bots'],
    ['max_products_per_bot', 'max_products_per_bot'],
    ['max_stock_keys_per_bot', 'max_stock_keys_per_bot'],
    ['price', 'price'],
    ['active', 'active']
  ]) {
    if (x[k] === undefined) continue;
    let v = x[k];
    if (k === 'name') v = safeName(v);
    else if (k === 'price') v = finiteMoney(v);
    else v = Math.floor(Number(v));
    if ((k === 'name' && !v) ||
        (k === 'price' && v === null) ||
        (['days', 'max_bots', 'max_products_per_bot', 'max_stock_keys_per_bot'].includes(k) && (!Number.isInteger(v) || v < 0)) ||
        (k === 'active' && !([0, 1, '0', '1'].includes(v)))) {
      return r.status(400).json({ ok: false, message: 'Invalid plan field.' });
    }
    fields.push(`${sql}=?`);
    args.push(k === 'active' ? Number(v) : v);
  }
  if (!fields.length) return r.status(400).json({ ok: false, message: 'No fields to update.' });
  args.push(id);
  try {
    builderDb.prepare(`UPDATE saas_plans SET ${fields.join(',')} WHERE id=?`).run(...args);
    r.json({ ok: true });
  } catch {
    r.status(409).json({ ok: false, message: 'Plan update failed.' });
  }
});

app.get('/api/admin/sellers', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  const sellers = builderDb
    .prepare(
      `SELECT a.id, a.username, a.active, a.created_at, a.last_login,
              s.id subscription_id, p.name plan, s.starts_at, s.expires_at, s.status,
              COUNT(b.id) bot_count
       FROM sellers a
       LEFT JOIN subscriptions s ON s.id = (SELECT s2.id FROM subscriptions s2 WHERE s2.seller_id = a.id ORDER BY s2.expires_at DESC LIMIT 1)
       LEFT JOIN saas_plans p ON p.id = s.plan_id
       LEFT JOIN bots b ON b.seller_id = a.id
       GROUP BY a.id
       ORDER BY a.id DESC`
    )
    .all();
  r.json({ ok: true, sellers });
});

app.post('/api/admin/sellers/:id/status', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  const id = intId(q.params.id);
  if (!id) return r.status(400).json({ ok: false, message: 'Invalid seller ID.' });
  const active = Number(q.body?.active ? 1 : 0);
  builderDb.prepare('UPDATE sellers SET active=? WHERE id=?').run(active, id);
  if (!active) builderDb.prepare('UPDATE sessions SET revoked_at=? WHERE seller_id=? AND revoked_at IS NULL').run(now(), id);
  r.json({ ok: true });
});

app.post('/api/admin/subscriptions', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  const sellerId = intId(q.body?.seller_id);
  const planId = intId(q.body?.plan_id);
  if (!sellerId || !planId) return r.status(400).json({ ok: false, message: 'seller_id and plan_id required.' });
  const p = builderDb.prepare('SELECT * FROM saas_plans WHERE id=? AND active=1').get(planId);
  if (!p) return r.status(404).json({ ok: false, message: 'Plan not found.' });
  const days = Math.min(Math.max(Number(q.body?.days || p.days), 1), 36500);
  const start = new Date();
  const base = activeSubscription(sellerId);
  if (base) {
    const t = Math.max(Date.now(), Date.parse(base.expires_at));
    start.setTime(t);
  }
  const exp = new Date(start.getTime() + days * 86400000);
  builderDb.prepare("UPDATE subscriptions SET status='replaced' WHERE seller_id=? AND status='active'").run(sellerId);
  const id = builderDb
    .prepare(
      "INSERT INTO subscriptions(seller_id, plan_id, starts_at, expires_at, status, created_at) VALUES(?,?,?,?,?,?)"
    )
    .run(sellerId, planId, start.toISOString(), exp.toISOString(), 'active', now()).lastInsertRowid;
  r.json({ ok: true, subscription: { id, expires_at: exp.toISOString(), plan: p.name } });
});

app.post('/api/admin/limits', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  const sellerId = intId(q.body?.seller_id);
  if (!sellerId) return r.status(400).json({ ok: false, message: 'Invalid seller ID.' });
  const vals = ['max_bots', 'max_products_per_bot', 'max_stock_keys_per_bot'].map(k =>
    q.body?.[k] == null ? null : Math.max(0, Math.floor(Number(q.body[k])))
  );
  if (vals.some(v => v !== null && !Number.isFinite(v))) return r.status(400).json({ ok: false, message: 'Invalid limits.' });
  builderDb
    .prepare(
      `INSERT INTO seller_limits(seller_id, max_bots, max_products_per_bot, max_stock_keys_per_bot)
       VALUES(?,?,?,?) ON CONFLICT(seller_id) DO UPDATE SET
       max_bots=excluded.max_bots, max_products_per_bot=excluded.max_products_per_bot, max_stock_keys_per_bot=excluded.max_stock_keys_per_bot`
    )
    .run(sellerId, ...vals);
  r.json({ ok: true });
});

app.get('/api/admin/invoices', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  r.json({
    ok: true,
    invoices: builderDb
      .prepare(
        `SELECT i.*, s.username, p.name plan_name
         FROM invoices i
         JOIN sellers s ON s.id = i.seller_id
         LEFT JOIN saas_plans p ON p.id = i.plan_id
         ORDER BY i.id DESC LIMIT 500`
      )
      .all()
  });
});

app.post('/api/admin/invoices', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  const sellerId = intId(q.body?.seller_id);
  const planId = intId(q.body?.plan_id);
  if (!sellerId || !planId) return r.status(400).json({ ok: false, message: 'seller_id and plan_id required.' });
  const p = builderDb.prepare('SELECT * FROM saas_plans WHERE id=?').get(planId);
  if (!p) return r.status(404).json({ ok: false, message: 'Plan not found.' });
  const amount = finiteMoney(q.body?.amount ?? p.price);
  const rate = Math.min(Math.max(Number(q.body?.commission_rate ?? 0), 0), 100);
  if (amount === null) return r.status(400).json({ ok: false, message: 'Invalid amount.' });
  const comm = Number((amount * rate / 100).toFixed(2));
  const id = builderDb
    .prepare(
      "INSERT INTO invoices(seller_id, plan_id, amount, commission_rate, commission_amount, status, external_ref, created_at) VALUES(?,?,?,?,?,?,?,?)"
    )
    .run(sellerId, planId, amount, rate, comm, 'paid', String(q.body?.external_ref || '').slice(0, 200), now())
    .lastInsertRowid;
  builderDb
    .prepare('INSERT INTO commission_ledger(seller_id, invoice_id, amount, type, created_at) VALUES(?,?,?,?,?)')
    .run(sellerId, id, comm, 'commission', now());
  const days = Math.min(Math.max(Number(q.body?.days || p.days), 1), 36500);
  const base = activeSubscription(sellerId);
  const startMs = base ? Math.max(Date.now(), Date.parse(base.expires_at)) : Date.now();
  const exp = new Date(startMs + days * 86400000);
  builderDb.prepare("UPDATE subscriptions SET status='replaced' WHERE seller_id=? AND status='active'").run(sellerId);
  builderDb
    .prepare("INSERT INTO subscriptions(seller_id, plan_id, starts_at, expires_at, status, created_at) VALUES(?,?,?,?,?,?)")
    .run(sellerId, planId, new Date(startMs).toISOString(), exp.toISOString(), 'active', now());
  r.json({
    ok: true,
    invoice: { id, amount, commission_amount: comm, status: 'paid' },
    subscription: { plan: p.name, expires_at: exp.toISOString() }
  });
});

app.get('/api/admin/commissions', (q, r) => {
  if (!isSuper(q)) return r.status(403).json({ ok: false, message: 'Super admin only.' });
  r.json({
    ok: true,
    total: builderDb.prepare("SELECT COALESCE(SUM(amount),0) x FROM commission_ledger WHERE type='commission'").get().x,
    ledger: builderDb
      .prepare(
        `SELECT c.*, s.username
         FROM commission_ledger c
         JOIN sellers s ON s.id = c.seller_id
         ORDER BY c.id DESC LIMIT 500`
      )
      .all()
  });
});

// ─── Bot endpoints ──────────────────────────────────────────────────────────────
app.get('/api/bots', (q, r) => {
  const sql = isSuper(q)
    ? 'SELECT id, name, username, owner_id, created_at, status, uptime_started, last_error FROM bots ORDER BY id DESC'
    : 'SELECT id, name, username, owner_id, created_at, status, uptime_started, last_error FROM bots WHERE seller_id=? ORDER BY id DESC';
  const data = isSuper(q)
    ? builderDb.prepare(sql).all()
    : builderDb.prepare(sql).all(q.user.id);
  r.json({ ok: true, bots: data.map(publicBot) });
});

app.post('/api/bots/validate', async (q, r) => {
  const { token, ownerId } = q.body || {};
  if (!validToken(token) || !validOwner(ownerId)) {
    return r.status(400).json({ ok: false, message: 'Invalid Bot Token or Telegram Owner ID.' });
  }
  try {
    const x = await tg(token, 'getMe');
    if (!x.ok) return r.status(400).json({ ok: false, message: x.description || 'Telegram rejected the token.' });
    r.json({ ok: true, bot: x.result });
  } catch (e) {
    r.status(502).json({ ok: false, message: publicError(e, 'Telegram API request failed.') });
  }
});

app.post('/api/bots/deploy', async (q, r) => {
  if (!enforceSellerSubscription(q, r)) return;
  const { token, ownerId, name } = q.body || {};
  if (!isSuper(q)) {
    const lim = sellerLimits(q.user.id);
    const c = builderDb.prepare('SELECT COUNT(*) c FROM bots WHERE seller_id=?').get(q.user.id).c;
    if (c >= lim.limits.max_bots) {
      return r.status(403).json({ ok: false, message: 'Your plan bot limit has been reached.', code: 'BOT_LIMIT_REACHED' });
    }
  }
  if (!validToken(token) || !validOwner(ownerId) || (!safeName(name) && !token)) {
    return r.status(400).json({ ok: false, message: 'Invalid Bot Token or Owner ID.' });
  }
  try {
    const x = await tg(token, 'getMe');
    if (!x.ok) return r.status(400).json({ ok: false, message: x.description || 'Token invalid.' });
    const exists = builderDb.prepare('SELECT id FROM bots WHERE username=?').get(x.result.username);
    if (exists) return r.status(409).json({ ok: false, message: 'This bot is already deployed in this builder.' });
    const callbackSecret = crypto.randomBytes(24).toString('hex');
    const id = builderDb
      .prepare(
        `INSERT INTO bots(name, username, owner_id, token_enc, created_at, status, db_path, seller_id, gateway_callback_secret)
         VALUES(?,?,?,?,?,?,?,?,?)`
      )
      .run(
        safeName(name) || safeName(x.result.first_name) || 'SHIVAM STORE',
        x.result.username,
        String(ownerId),
        enc(token),
        now(),
        'offline',
        path.join(BOT_DIR, String(Date.now()) + '-' + crypto.randomBytes(3).toString('hex'), 'shivam_store.sqlite3'),
        isSuper(q) ? null : q.user.id,
        callbackSecret
      ).lastInsertRowid;
    const bot = getBot(id);
    const dir = path.dirname(bot.db_path);
    fs.mkdirSync(dir, { recursive: true });
    fs.copyFileSync(path.join(__dirname, 'bot_template.py'), path.join(dir, 'bot.py'));
    const started = startBot(id);
    if (!started) {
      builderDb.prepare('DELETE FROM bots WHERE id=?').run(id);
      try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
      return r.status(503).json({ ok: false, message: 'Bot could not be started.' });
    }
    r.json({ ok: true, bot: { id, username: x.result.username, name: bot.name, owner_id: bot.owner_id, status: 'online' } });
  } catch (e) {
    r.status(500).json({ ok: false, message: publicError(e, 'Unable to deploy bot.') });
  }
});

app.post('/api/bots/:id/:action', (q, r) => {
  const id = intId(q.params.id);
  if ((q.params.action === 'start' || q.params.action === 'restart') && !enforceSellerSubscription(q, r)) return;
  if (!id) return r.status(400).json({ ok: false, message: 'Invalid bot ID.' });
  if (!accessibleBot(q, id)) return denyBot(q, r, id);
  if (q.params.action === 'start') startBot(id);
  else if (q.params.action === 'stop') stopBot(id);
  else if (q.params.action === 'restart') restartBot(id);
  else return r.status(400).json({ ok: false, message: 'Unknown action' });
  r.json({ ok: true });
});

// ─── Gateway callback ───────────────────────────────────────────────────────────
function gatewayCallbackValue(body, names) {
  const wanted = new Set(names.map(x => x.toLowerCase()));
  const walk = (v) => {
    if (v && typeof v === 'object') {
      for (const [k, x] of Object.entries(v)) {
        if (wanted.has(String(k).toLowerCase()) && x !== null && x !== undefined && String(x).trim() !== '') {
          return String(x).trim();
        }
        const z = walk(x);
        if (z) return z;
      }
    }
    return '';
  };
  return walk(body) || '';
}
function gatewaySuccess(v) {
  return /^(true|success|successful|paid|completed|complete|approved|verified|ok)$/i.test(String(v || '').trim());
}
async function handleGatewayCallback(req, res) {
  const botId = intId(req.params.id);
  const secret = String(req.params.secret || '');
  const b = getBot(botId);
  if (!b || !secret || secret !== String(b.gateway_callback_secret || '')) {
    return res.status(404).json({ ok: false, message: 'Not found' });
  }
  const body = { ...(req.query || {}), ...(req.body || {}) };
  const orderNo = gatewayCallbackValue(body, ['order_id', 'orderid', 'order', 'merchant_order_id', 'client_order_id', 'orderId']);
  const status = gatewayCallbackValue(body, ['status', 'payment_status', 'state', 'result']);
  const amountRaw = gatewayCallbackValue(body, ['amount', 'paid_amount', 'payment_amount', 'txn_amount', 'price_amount', 'amount_paid']);
  const eventId = gatewayCallbackValue(body, ['event_id', 'eventid', 'transaction_id', 'transactionId', 'txn_id', 'utr', 'rrn', 'gateway_txn_id']) || hashText(JSON.stringify(body));
  if (!orderNo || !gatewaySuccess(status)) return res.json({ ok: true, received: true, ignored: true });
  const d = dbFor(b);
  try {
    d.exec('BEGIN IMMEDIATE');
    const order = d.prepare('SELECT * FROM orders WHERE order_no=?').get(orderNo);
    if (!order) { d.exec('ROLLBACK'); return res.status(404).json({ ok: false, message: 'Order not found' }); }
    if (amountRaw && Number.isFinite(Number(amountRaw)) && Math.abs(Number(amountRaw) - Number(order.amount)) > 0.01) {
      d.exec('ROLLBACK');
      return res.status(400).json({ ok: false, message: 'Amount mismatch' });
    }
    try {
      d.prepare(
        'INSERT INTO payment_events(provider, provider_event_id, order_id, event_type, received_at, details) VALUES(?,?,?,?,?,?)'
      ).run('gateway', String(eventId).slice(0, 200), order.id, 'payment_callback', now(), JSON.stringify(body).slice(0, 2000));
    } catch {
      d.exec('COMMIT');
      return res.json({ ok: true, duplicate: true });
    }
    if (['awaiting_utr', 'pending'].includes(order.status)) {
      d.prepare(
        "UPDATE orders SET status='pending', payment_method='gateway', approved_at=NULL, rejected_at=NULL WHERE id=? AND payment_method='gateway' AND status IN ('awaiting_utr','pending')"
      ).run(order.id);
    }
    d.exec('COMMIT');
    return res.json({ ok: true, received: true, order_id: orderNo });
  } catch (e) {
    try { d.exec('ROLLBACK'); } catch {}
    console.error('GATEWAY_CALLBACK_ERROR', e);
    return res.status(500).json({ ok: false, message: 'Callback processing failed' });
  } finally {
    d.close();
  }
}
app.all('/api/gateway/callback/:id/:secret', handleGatewayCallback);

// ─── Bot data endpoints ─────────────────────────────────────────────────────────
app.get('/api/summary/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const s = {
    members: one(b, 'SELECT COUNT(*) c FROM users').c,
    products: one(b, 'SELECT COUNT(*) c FROM products WHERE active=1').c,
    keys: one(b, "SELECT COUNT(*) c FROM stock_keys WHERE status='available'").c,
    orders: one(b, 'SELECT COUNT(*) c FROM orders').c,
    delivered: one(b, "SELECT COUNT(*) c FROM orders WHERE delivery_status='delivered'").c,
    revenue: one(b, "SELECT COALESCE(SUM(amount),0) x FROM orders WHERE status='approved' AND order_type='product'").x,
    topups: one(b, "SELECT COALESCE(SUM(amount),0) x FROM wallet_transactions WHERE type IN ('deposit','topup') AND amount>0").x
  };
  r.json({ ok: true, bot: publicBot(b), stats: s });
});

app.post('/api/products/:botId/:productId/maintenance', (q, r) => {
  const botId = intId(q.params.botId);
  const productId = intId(q.params.productId);
  const b = accessibleBot(q, botId);
  if (!b || !productId) return r.status(400).json({ ok: false, message: 'Valid bot and product ID required.' });
  const p = one(b, 'SELECT id, maintenance_mode FROM products WHERE id=?', [productId]);
  if (!p) return r.status(404).json({ ok: false, message: 'Product not found' });
  const enabled = q.body?.enabled === undefined ? !Number(p.maintenance_mode) : Boolean(Number(q.body.enabled));
  run(b, 'UPDATE products SET maintenance_mode=? WHERE id=?', [enabled ? 1 : 0, productId]);
  return r.json({ ok: true, maintenance: enabled });
});

app.get('/api/payments/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const d = dbFor(b);
  try {
    const orders = d
      .prepare(
        `SELECT o.id, o.order_no, o.user_id, o.order_type, o.amount, o.topup_amount, o.payment_method, o.status, o.created_at, o.expiry_at, o.approved_at, o.rejected_at, o.delivery_status, o.delivery_error,
                u.username, u.first_name, p.name product, pl.name plan,
                COALESCE((SELECT COUNT(*) FROM payment_events pe WHERE pe.order_id = o.id),0) event_count,
                COALESCE((SELECT MAX(pe.received_at) FROM payment_events pe WHERE pe.order_id = o.id),NULL) last_event_at
         FROM orders o
         LEFT JOIN users u ON u.id = o.user_id
         LEFT JOIN plans pl ON pl.id = o.plan_id
         LEFT JOIN products p ON p.id = pl.product_id
         WHERE o.payment_method = 'gateway'
         ORDER BY o.id DESC LIMIT 500`
      )
      .all();
    r.json({
      ok: true,
      payments: orders.map(o => ({
        ...o,
        payment_status: o.status === 'approved' ? 'success' :
                        o.status === 'pending' ? 'pending' :
                        (o.expiry_at && Date.parse(o.expiry_at) <= Date.now() && o.status === 'awaiting_utr' ? 'expired' :
                         o.status === 'awaiting_utr' ? 'created' : o.status),
        user_label: o.username ? `@${o.username}` : (o.first_name || String(o.user_id)),
        kind: o.order_type === 'balance' ? 'Top-up' : 'Product'
      }))
    });
  } finally {
    d.close();
  }
});

app.get('/api/products/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const ps = rows(
    b,
    `SELECT p.*,
            COUNT(pl.id) plan_count,
            (SELECT COUNT(*) FROM stock_keys sk JOIN plans spl ON spl.id = sk.plan_id WHERE spl.product_id = p.id AND sk.status='available') stock
     FROM products p
     LEFT JOIN plans pl ON pl.product_id = p.id
     GROUP BY p.id
     ORDER BY p.id DESC`
  );
  r.json({ ok: true, products: ps.map(p => ({ ...p, status: p.active ? 'active' : 'disabled', maintenance: p.maintenance_mode })) });
});

function defaultCategory(b) {
  let c = one(b, 'SELECT * FROM categories ORDER BY id LIMIT 1');
  if (!c) {
    run(b, 'INSERT INTO categories(name, description, active) VALUES(?,?,?)', ['General', 'Default product category', 1]);
    c = one(b, 'SELECT * FROM categories ORDER BY id LIMIT 1');
  }
  return c.id;
}

app.post('/api/products/:id', (q, r) => {
  if (!enforceSellerSubscription(q, r)) return;
  const b = accessibleBot(q, q.params.id);
  const x = q.body || {};
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  if (!isSuper(q)) {
    const lim = sellerLimits(q.user.id);
    if (countBotProducts(b) >= lim.limits.max_products_per_bot) {
      return r.status(403).json({ ok: false, message: 'Product limit for your plan has been reached.', code: 'PRODUCT_LIMIT_REACHED' });
    }
  }
  let d;
  try {
    const cat = x.category_id || defaultCategory(b);
    d = new DatabaseSync(b.db_path);
    d.exec('BEGIN IMMEDIATE');
    const productName = safeName(x.name);
    if (!productName) throw new Error('Product name is required.');
    const p = d
      .prepare(
        'INSERT INTO products(category_id, name, description, channel_link, maintenance_mode, active, created_at) VALUES(?,?,?,?,?,?,?)'
      )
      .run(
        cat,
        productName,
        String(x.description || '').slice(0, 5000),
        String(x.channel_link || '').slice(0, 1000),
        Number(x.maintenance ? 1 : 0),
        1,
        now()
      );
    for (const pl of (x.plans || [])) {
      d
        .prepare(
          'INSERT INTO plans(product_id, name, description, days, customer_price, reseller_price, active) VALUES(?,?,?,?,?,?,?)'
        )
        .run(
          p.lastInsertRowid,
          String(pl.name || pl.duration || 'Plan'),
          String(pl.description || ''),
          Number(pl.days || parseInt(pl.duration) || 0),
          finiteMoney(pl.price) || 0,
          finiteMoney(pl.reseller_price) || 0,
          1
        );
    }
    d.exec('COMMIT');
    d.close();
    r.json({ ok: true });
  } catch (e) {
    try { d?.exec('ROLLBACK'); } catch {}
    try { d?.close(); } catch {}
    r.status(400).json({ ok: false, message: e.message });
  }
});

app.put('/api/products/:botId/:productId', (q, r) => {
  const x = q.body || {};
  const botId = intId(q.params.botId);
  const productId = intId(q.params.productId);
  const b = accessibleBot(q, botId);
  if (!b || !productId) return r.status(400).json({ ok: false, message: 'Valid bot and product ID required.' });
  const p = one(b, 'SELECT id FROM products WHERE id=?', [productId]);
  if (!p) return r.status(404).json({ ok: false, message: 'Product not found' });
  const name = x.name == null ? null : safeName(x.name);
  if (x.name != null && !name) return r.status(400).json({ ok: false, message: 'Product name cannot be empty.' });
  run(
    b,
    'UPDATE products SET name=COALESCE(?,name), description=COALESCE(?,description), channel_link=COALESCE(?,channel_link), active=COALESCE(?,active), maintenance_mode=COALESCE(?,maintenance_mode) WHERE id=?',
    [
      name,
      x.description == null ? null : String(x.description).slice(0, 5000),
      x.channel_link == null ? null : String(x.channel_link).slice(0, 1000),
      x.status === 'disabled' ? 0 : (x.status === 'active' ? 1 : null),
      x.maintenance == null ? null : (String(x.maintenance) === '1' ? 1 : 0),
      productId
    ]
  );
  r.json({ ok: true });
});

app.delete('/api/products/:botId/:productId', (q, r) => {
  const botId = intId(q.params.botId);
  const productId = intId(q.params.productId);
  const b = accessibleBot(q, botId);
  if (!b || !productId) return r.status(400).json({ ok: false, message: 'Valid bot and product ID required.' });
  const p = one(b, 'SELECT id FROM products WHERE id=?', [productId]);
  if (!p) return r.status(404).json({ ok: false, message: 'Product not found' });
  run(b, 'UPDATE products SET active=0 WHERE id=?', [productId]);
  r.json({ ok: true });
});

app.get('/api/plans/:id', (q, r) => {
  const botId = Number(q.query.bot_id || q.headers['x-bot-id'] || 0);
  const b = accessibleBot(q, botId);
  if (!b) return r.status(400).json({ ok: false, message: 'bot_id required' });
  const ps = rows(b, 'SELECT * FROM plans WHERE product_id=? ORDER BY id', [q.params.id]);
  r.json({ ok: true, plans: ps });
});

app.post('/api/plans/:id', (q, r) => {
  const b = accessibleBot(q, intId(q.body?.bot_id || q.headers['x-bot-id']));
  if (!b) return r.status(400).json({ ok: false, message: 'bot_id required' });
  const x = q.body || {};
  const productId = intId(q.params.id);
  if (!productId) return r.status(400).json({ ok: false, message: 'Invalid product ID.' });
  if (!one(b, 'SELECT id FROM products WHERE id=?', [productId])) {
    return r.status(404).json({ ok: false, message: 'Product not found.' });
  }
  const days = Number(x.days || parseInt(x.duration) || 0);
  if (!Number.isInteger(days) || days < 0 || days > 36500) {
    return r.status(400).json({ ok: false, message: 'Invalid duration.' });
  }
  const name = safeName(x.name || x.duration || 'Plan');
  if (!name) return r.status(400).json({ ok: false, message: 'Plan name is required.' });
  run(
    b,
    'INSERT INTO plans(product_id, name, description, days, customer_price, reseller_price, active) VALUES(?,?,?,?,?,?,?)',
    [
      productId,
      name,
      String(x.description || '').slice(0, 5000),
      days,
      finiteMoney(x.price) || 0,
      finiteMoney(x.reseller_price) || 0,
      1
    ]
  );
  r.json({ ok: true });
});

app.get('/api/keys/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const ks = rows(
    b,
    `SELECT sk.*, p.name product, pl.name plan
     FROM stock_keys sk
     LEFT JOIN plans pl ON pl.id = sk.plan_id
     LEFT JOIN products p ON p.id = pl.product_id
     ORDER BY sk.id DESC`
  );
  r.json({ ok: true, keys: ks });
});

app.post('/api/keys/:id/bulk', (q, r) => {
  if (!enforceSellerSubscription(q, r)) return;
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const list = String(q.body?.keys || '').split(/\r?\n/).map(x => x.trim()).filter(Boolean);
  if (!list.length) return r.status(400).json({ ok: false, message: 'No keys supplied.' });
  const planId = Number(q.body?.plan_id || 0);
  const plans = rows(b, 'SELECT id FROM plans WHERE id=?', [planId]);
  if (!plans.length) return r.status(400).json({ ok: false, message: 'Select a valid plan before adding stock.' });
  if (!isSuper(q)) {
    const lim = sellerLimits(q.user.id);
    if (countBotKeys(b) + list.length > lim.limits.max_stock_keys_per_bot) {
      return r.status(403).json({ ok: false, message: 'Stock key limit for your plan has been reached.', code: 'KEY_LIMIT_REACHED' });
    }
  }
  let added = 0;
  const d = new DatabaseSync(b.db_path);
  try {
    d.exec('BEGIN IMMEDIATE');
    for (const v of list) {
      try {
        d.prepare('INSERT INTO stock_keys(plan_id, key_value, status, created_at) VALUES(?,?,?,?)')
          .run(plans[0].id, v, 'available', now());
        added++;
      } catch {}
    }
    d.exec('COMMIT');
    d.close();
    r.json({ ok: true, added });
  } catch (e) {
    try { d.exec('ROLLBACK'); } catch {}
    d.close();
    r.status(400).json({ ok: false, message: e.message });
  }
});

app.get('/api/orders/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const o = rows(
    b,
    `SELECT o.*, u.username, u.first_name, p.name product, pl.name plan
     FROM orders o
     LEFT JOIN users u ON u.id = o.user_id
     LEFT JOIN plans pl ON pl.id = o.plan_id
     LEFT JOIN products p ON p.id = pl.product_id
     ORDER BY o.id DESC LIMIT 500`
  );
  r.json({
    ok: true,
    orders: o.map(x => ({ ...x, user_id: x.user_id, payment: x.status, delivery: x.delivery_status }))
  });
});

app.get('/api/users/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const u = rows(
    b,
    `SELECT id telegram_id, username, first_name, balance,
            CASE WHEN is_reseller=1 THEN 'reseller' ELSE 'user' END role,
            created_at joined_at
     FROM users ORDER BY id DESC LIMIT 1000`
  );
  r.json({ ok: true, users: u });
});

app.post('/api/wallet/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  const x = q.body || {};
  const amt = finiteMoney(x.amount);
  if (!b || !/^\d+$/.test(String(x.telegram_id || '')) || !Number.isFinite(amt) || amt <= 0) {
    return r.status(400).json({ ok: false, message: 'Valid Telegram ID and positive amount required.' });
  }
  const d = new DatabaseSync(b.db_path);
  try {
    d.exec('BEGIN IMMEDIATE');
    let u = d.prepare('SELECT * FROM users WHERE telegram_id=?').get(String(x.telegram_id));
    if (!u) {
      d.exec('ROLLBACK');
      d.close();
      return r.status(404).json({ ok: false, message: 'User not found in this bot.' });
    }
    const before = Number(u.balance);
    const after = before + amt;
    d.prepare('UPDATE users SET balance=?, updated_at=? WHERE id=?').run(after, now(), u.id);
    d.prepare(
      'INSERT INTO wallet_transactions(user_id, type, amount, balance_before, balance_after, note, created_at) VALUES(?,?,?,?,?,?,?)'
    ).run(u.id, 'topup', amt, before, after, String(x.reason || 'Admin top-up'), now());
    d.exec('COMMIT');
    d.close();
    r.json({ ok: true, balance: after });
  } catch (e) {
    try { d.exec('ROLLBACK'); } catch {}
    d.close();
    r.status(400).json({ ok: false, message: e.message });
  }
});

app.get('/api/broadcasts/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const x = rows(
    b,
    'SELECT id, message text, status, sent_count sent, error_count failed, created_at FROM scheduled_broadcasts ORDER BY id DESC LIMIT 100'
  );
  r.json({ ok: true, broadcasts: x });
});

app.post('/api/broadcast/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  const text = String(q.body?.text || '').trim();
  if (!b || !text) return r.status(400).json({ ok: false, message: 'Message required.' });
  run(b, 'INSERT INTO scheduled_broadcasts(message, run_at, created_at, status) VALUES(?,?,?,?)', [text, now(), now(), 'scheduled']);
  r.json({ ok: true });
});

app.get('/api/logs/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const f = path.join(path.dirname(b.db_path), 'bot.log');
  let logs = '';
  try { logs = fs.readFileSync(f, 'utf8').slice(-50000); } catch {}
  r.json({ ok: true, logs });
});

app.get('/api/config/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const settings = rows(b, 'SELECT key, value FROM settings ORDER BY key').map(x => {
    if (x.key === 'payment_gateway_api_key' && x.value) {
      const v = String(x.value);
      return { ...x, value: '••••••••' + v.slice(-4), secret: true };
    }
    return x;
  });
  r.json({ ok: true, settings });
});

app.get('/api/gateway/callback-url/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const base = String(process.env.PUBLIC_BASE_URL || process.env.RENDER_EXTERNAL_URL || '').replace(/\/$/, '');
  if (!base) return r.status(503).json({ ok: false, message: 'Public callback URL is not configured.' });
  r.json({ ok: true, callback_url: `${base}/api/gateway/callback/${b.id}/${b.gateway_callback_secret}` });
});

app.put('/api/config/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  const d = new DatabaseSync(b.db_path);
  try {
    d.exec('BEGIN IMMEDIATE');
    for (const [k, v] of Object.entries(q.body || {})) {
      if (!/^[A-Za-z0-9_.-]{1,80}$/.test(k)) continue;
      const value = String(v ?? '');
      if (k === 'payment_gateway_url' && value && !/^https:\/\//i.test(value)) {
        throw new Error('Payment gateway URL must use HTTPS.');
      }
      if (k === 'payment_gateway_api_key' && value.length > 512) {
        throw new Error('Payment gateway API key is too long.');
      }
      if (k === 'payment_gateway_enabled' && !['0', '1'].includes(value)) {
        throw new Error('Invalid payment gateway status.');
      }
      d.prepare('INSERT INTO settings(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').run(k, value);
    }
    d.exec('COMMIT');
    d.close();
    r.json({ ok: true });
  } catch (e) {
    try { d.exec('ROLLBACK'); } catch {}
    d.close();
    r.status(400).json({ ok: false, message: e.message });
  }
});

app.get('/api/resellers/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  if (!b) return r.status(404).json({ ok: false, message: 'Bot not found' });
  r.json({ ok: true, resellers: rows(b, 'SELECT id, username, first_name, balance, created_at FROM users WHERE is_reseller=1 ORDER BY id DESC') });
});

app.post('/api/resellers/:id', (q, r) => {
  const b = accessibleBot(q, q.params.id);
  const uid = Number(q.body?.user_id);
  if (!b || !Number.isInteger(uid)) return r.status(400).json({ ok: false, message: 'Valid internal user ID required.' });
  run(b, 'UPDATE users SET is_reseller=1, updated_at=? WHERE id=?', [now(), uid]);
  r.json({ ok: true });
});

// ─── Restore running bots on startup ────────────────────────────────────────────
for (const b of builderDb.prepare("SELECT id FROM bots WHERE status='online'").all()) {
  try { startBot(b.id); } catch (e) {
    builderDb.prepare('UPDATE bots SET status=?, last_error=? WHERE id=?').run('offline', e.message, b.id);
  }
}

// ─── Health monitoring for bots ─────────────────────────────────────────────────
setInterval(() => {
  for (const b of builderDb.prepare('SELECT id, status, db_path, uptime_started FROM bots').all()) {
    if (b.status !== 'online') continue;
    const c = children.get(b.id);
    const state = restartState.get(b.id) || { startedAt: Date.parse(b.uptime_started || '') || Date.now(), attempt: 0, nextAt: 0 };
    const inGrace = Date.now() - state.startedAt < STARTUP_GRACE_MS;
    const dir = path.dirname(b.db_path);
    const hb = path.join(dir, 'heartbeat');
    const thb = path.join(dir, 'telegram_heartbeat');
    let stale = false, telegramStale = false;
    try { stale = Date.now() - fs.statSync(hb).mtimeMs > HEARTBEAT_STALE_MS; } catch { stale = !inGrace; }
    try { telegramStale = Date.now() - fs.statSync(thb).mtimeMs > HEARTBEAT_STALE_MS; } catch { telegramStale = !inGrace; }
    const dead = !c || c.exitCode !== null;
    if ((dead || stale || telegramStale) && !inGrace) {
      if (c && c.exitCode === null) { try { c.kill('SIGTERM'); } catch {} }
      if (c === children.get(b.id)) children.delete(b.id);
      if (Date.now() < state.nextAt) continue;
      const attempt = Math.min((state.attempt || 0) + 1, 8);
      const delay = Math.min(3000 * Math.pow(2, attempt - 1), 60000);
      restartState.set(b.id, { startedAt: Date.now(), attempt, nextAt: Date.now() + delay });
      setTimeout(() => {
        try {
          const latest = builderDb.prepare('SELECT status FROM bots WHERE id=?').get(b.id);
          if (latest && latest.status === 'online') startBot(b.id);
        } catch (e) {
          try { builderDb.prepare('UPDATE bots SET last_error=? WHERE id=?').run(publicError(e), b.id); } catch {}
        }
      }, delay).unref();
    }
  }
}, 15000).unref();

// ─── Expiry enforcement ──────────────────────────────────────────────────────────
setInterval(enforceExpiry, 30000).unref();

// ─── Log rotation ───────────────────────────────────────────────────────────────
setInterval(() => {
  try {
    for (const b of builderDb.prepare('SELECT db_path FROM bots').all()) {
      const f = path.join(path.dirname(b.db_path), 'bot.log');
      try {
        const st = fs.statSync(f);
        if (st.size > 2 * 1024 * 1024) {
          const buf = fs.readFileSync(f);
          fs.writeFileSync(f, buf.subarray(Math.max(0, buf.length - 2 * 1024 * 1024)));
        }
      } catch {}
    }
  } catch {}
}, 300000).unref();

// ─── Error handler ──────────────────────────────────────────────────────────────
app.use((err, req, res, next) => {
  console.error('HTTP_ERROR', publicError(err, 'Unhandled request error'));
  if (res.headersSent) return next(err);
  const status = Number.isInteger(err?.status) && err.status >= 400 && err.status < 600 ? err.status : 500;
  res.status(status).json({ ok: false, message: status === 500 ? 'Internal server error' : publicError(err) });
});

// ─── Start server ──────────────────────────────────────────────────────────────
const PORT = Number(process.env.PORT || 3000);
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`SHIVAM BOT BUILDER listening on ${PORT}`);
});

// ─── Graceful shutdown ─────────────────────────────────────────────────────────
function shutdown() {
  console.log('Shutting down...');
  for (const [id, c] of children) {
    try { c.kill('SIGTERM'); } catch {}
  }
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 8000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
process.on('uncaughtException', e => console.error('UNCAUGHT_EXCEPTION', e));
process.on('unhandledRejection', e => console.error('UNHANDLED_REJECTION', e));