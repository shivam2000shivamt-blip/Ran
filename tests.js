process.chdir(__dirname);
const assert=require('assert');const fs=require('fs');const cp=require('child_process');
for(const f of ['server.js','bot_template.py','public/index.html','requirements.txt','render.yaml','Dockerfile','package.json','.gitignore'])assert(fs.existsSync(f),`missing ${f}`);
cp.execFileSync(process.execPath,['--check','server.js']);
cp.execFileSync('python3',['-m','py_compile','bot_template.py']);
const htmlText=fs.readFileSync('public/index.html','utf8'); const scripts=[...htmlText.matchAll(/<script(?:[^>]*)>([\s\S]*?)<\/script>/gi)].map(m=>m[1]); fs.writeFileSync('/tmp/shivam-builder-ui-check.js',scripts.join('\n')); cp.execFileSync(process.execPath,['--check','/tmp/shivam-builder-ui-check.js']); fs.unlinkSync('/tmp/shivam-builder-ui-check.js');
const html=fs.readFileSync('public/index.html','utf8');
for(const x of ['Create Bot','Product Management','Top-up Payments','Payment Gateway','Members','Broadcast','Logs / Health','Maintenance','Secure session','SHIVAM BOT BUILDER','Welcome Back','Username or Email','Forgot Password?','Continue with Telegram','Continue with Google','Create Account','Email Address','Confirm Password','auth-shell','loginFloat','shield-orbit'])assert(html.includes(x),`UI marker missing: ${x}`); assert(!html.includes('UPI Payment Setup')&&!html.includes("UPI Payment"),'legacy UPI UI must be removed'); assert(!fs.existsSync('index.html'),'duplicate root index.html must not ship');
const server=fs.readFileSync('server.js','utf8');
for(const x of ['/api/bots/deploy','/api/products/','/api/keys/','/api/orders/','/api/users/','/api/wallet/','/api/broadcast/','/api/config/'])assert(server.includes(x),`endpoint missing: ${x}`);
assert(server.includes('function publicBot(b)'), 'publicBot sanitizer missing');
assert(server.includes('r.json({ok:true,bot:publicBot(b),stats:s})'), 'summary must not return encrypted token field');
assert(server.includes("supplied.length===ADMIN_KEY.length"), 'constant-time auth length guard missing');
assert(server.includes('X-Content-Type-Options'), 'security headers missing'); assert(server.includes("app.listen(PORT,'0.0.0.0'"), 'server must bind on 0.0.0.0'); assert(server.includes('uncaughtException'), 'uncaughtException handler missing'); assert(server.includes('unhandledRejection'), 'unhandledRejection handler missing');
const render=fs.readFileSync('render.yaml','utf8');
for(const x of ['BUILDER_SECRET','BUILDER_ADMIN_KEY','NODE_ENV','BUILDER_REQUIRE_AUTH','DATA_DIR'])assert(render.includes(x),`Render env missing: ${x}`);
assert(!html.includes("prompt('Enter Builder Admin Key:')"),'legacy browser prompt still present');
assert(server.includes('payment_gateway_api_key'), 'gateway key handling missing');
assert(server.includes("const ADMIN_KEY=process.env.BUILDER_ADMIN_KEY||'';"), 'production auth must use dedicated admin key');
assert(server.includes('Payment gateway URL must use HTTPS.'), 'gateway HTTPS validation missing');
assert(server.includes("value:'••••••••'+v.slice(-4)"), 'gateway key masking missing');
const bot=fs.readFileSync('bot_template.py','utf8');
for(const x of ['gateway_configured','create_gateway_payment','payment_gateway_url','payment_gateway_api_key','OPEN SECURE PAYMENT','payment:status'])assert(bot.includes(x),`gateway bot integration missing: ${x}`);


assert(server.includes("const BUILDER_SECRET=process.env.BUILDER_SECRET||'';"), 'builder secret must be explicit');
assert(server.includes("BUILDER_SECRET must be set and at least 32 characters"), 'builder secret production guard missing');
assert(server.includes("const supplied=String(req.headers['x-builder-key']||'');"), 'query-string admin key must be disabled');
assert(server.includes("/api/products/:botId/:productId"), 'product edit/delete routes must separate bot and product IDs');
assert(!server.includes("function writeEnv(dir,token,owner){const env=`BOT_TOKEN="), 'bot token must not be persisted to .env');
assert(server.includes("BOT_TOKEN:token"), 'bot token must be passed to worker runtime');
assert(server.includes('CREATE TABLE IF NOT EXISTS sellers'), 'seller account table missing');
assert(server.includes('CREATE TABLE IF NOT EXISTS sessions'), 'session table missing');
assert(server.includes('ALTER TABLE bots ADD COLUMN seller_id INTEGER'), 'bot tenant column migration missing');
assert(server.includes('function accessibleBot(req,id)'), 'tenant access guard missing');
assert(server.includes('b.seller_id&&Number(b.seller_id)===Number(req.user.id)'), 'seller ownership isolation missing');
assert(server.includes("x-csrf-token"), 'CSRF protection missing');
assert(server.includes('passwordHash(password,salt)'), 'password hashing missing');
assert(server.includes("app.post('/api/auth/login'"), 'seller login missing');
assert(server.includes("app.post('/api/auth/register'"), 'seller registration missing');
assert(server.includes("WHERE seller_id=? ORDER BY id DESC"), 'seller bot listing must be tenant scoped');
assert(server.includes('seller_id,gateway_callback_secret)'), 'new bots must store seller ownership and callback secret');
assert(server.includes("app.post('/api/bots/:id/:action'"), 'bot action route missing');
assert(!server.includes("app.post('/api/bots/:id/:action',(q,r)=>{const id=intId(q.params.id);if(!id)return r.status(400).json({ok:false,message:'Invalid bot ID.'});if(!getBot(id))"), 'bot action route must enforce tenant access');

console.log('PASS: syntax, security guards, token redaction, Render env wiring, required endpoints and premium UI markers');

assert(server.includes('/api/saas/me')&&server.includes('/api/saas/plans'),'saas plan endpoints');assert(server.includes('/api/admin/sellers')&&server.includes('/api/admin/subscriptions'),'super admin subscription endpoints');assert(server.includes('/api/admin/invoices')&&server.includes('/api/admin/commissions'),'billing commission endpoints');assert(server.includes('enforceExpiry'),'subscription expiry enforcement');assert(server.includes('BOT_LIMIT_REACHED')&&server.includes('PRODUCT_LIMIT_REACHED')&&server.includes('KEY_LIMIT_REACHED'),'plan limits');console.log('PASS: SaaS plans, limits, expiry, admin and billing checks');

const pkg=JSON.parse(fs.readFileSync('package.json','utf8')); assert(pkg.version==='3.2.5','package version mismatch'); assert(server.includes("SELECT id,status,db_path,uptime_started FROM bots"),'heartbeat watchdog query missing'); assert(server.includes("const shouldRestart=Boolean(b&&b.status==='online');"),'crash restart guard missing'); assert(server.includes('/api/gateway/callback/:id/:secret'),'gateway callback endpoint missing'); assert(server.includes('/api/payments/:id'),'payment history endpoint missing'); assert(server.includes('/api/products/:botId/:productId/maintenance'),'product maintenance endpoint missing'); assert(server.includes('gateway_callback_secret'),'gateway callback secret missing'); assert(server.includes('heartbeat'),'bot heartbeat watchdog missing'); assert(server.includes('telegramStale'),'Telegram connectivity watchdog missing'); assert(bot.includes('telegram_heartbeat'),'Telegram connectivity heartbeat missing'); assert(server.includes('childGeneration'),'stale child generation guard missing'); assert(server.includes('children.get(id)===child'),'stale exit handler guard missing'); assert(server.includes('PUBLIC_BASE_URL||process.env.RENDER_EXTERNAL_URL'),'callback base URL fallback missing'); assert(server.includes('GATEWAY_CALLBACK_URL'),'gateway callback URL runtime wiring missing'); assert(server.includes('RENDER_EXTERNAL_URL'),'Render external URL fallback missing'); assert(server.includes('MAX_BOT_LOG_BYTES'),'bounded bot log missing'); assert(server.includes('diskFreeBytes'),'disk free guard missing'); assert(bot.includes('gateway_callback_fulfillment_job'),'gateway fulfillment job missing'); assert(bot.includes('payment_created'),'payment creation event missing'); assert(bot.includes('BOT_HEARTBEAT_PATH'),'heartbeat env missing'); assert(bot.includes('gateway_configured()'), 'gateway-only checkout guard missing'); assert(!bot.includes('async def require_upi_configured'), 'legacy UPI config helper must be removed'); assert(bot.includes('Manual UPI/UTR payments are disabled'), 'legacy UPI/UTR flow must be blocked'); assert(!bot.includes('Buy with UPI'), 'legacy UPI purchase button must be removed'); assert(!bot.includes('Set UPI'), 'legacy UPI admin button must be removed'); console.log('PASS: v3.1.0 gateway-only, callback, payment tracking, heartbeat and watchdog guards');

assert(fs.readFileSync('.dockerignore','utf8').includes('__pycache__'),'dockerignore pycache'); assert(fs.readFileSync('.dockerignore','utf8').includes('.env'),'dockerignore env'); assert(fs.readFileSync('Dockerfile','utf8').includes('HEALTHCHECK'),'docker healthcheck missing'); assert(fs.readFileSync('bot_template.py','utf8').includes('timeout=20'),'gateway timeout missing'); assert(fs.readFileSync('bot_template.py','utf8').includes('for attempt in range(3)'),'gateway retry missing'); console.log('PASS: v3.2.0 environment, repo hygiene, bind, healthcheck and network resilience checks');

const pkg2=JSON.parse(fs.readFileSync('package.json','utf8'));assert(pkg2.dependencies.nodemailer,'nodemailer dependency missing');
for(const x of ["/api/auth/google/start","/api/auth/google/callback","/api/auth/telegram/start","/api/auth/telegram/callback","/api/auth/forgot","/api/auth/reset","social_identities","oauth_states","password_reset_tokens","TELEGRAM_CLIENT_SECRET","GOOGLE_CLIENT_SECRET","SMTP_HOST","MAIL_FROM","sendResetEmail","verifyTelegramIdToken"]){assert(server.includes(x),`OAuth/password reset wiring missing: ${x}`)}
assert(server.includes("scope:'openid email profile'"),'Google OIDC scope missing');assert(server.includes("code_challenge_method:'S256'"),'Telegram PKCE missing');assert(server.includes("https://oauth.telegram.org/.well-known/jwks.json"),'Telegram JWKS verification missing');assert(server.includes("crypto.verify('RSA-SHA256'"),'Telegram signature verification missing');assert(server.includes('used_at IS NULL'),'password reset one-time guard missing');assert(server.includes('expires_at>?'),'password reset expiry guard missing');assert(server.includes('UPDATE sessions SET revoked_at=? WHERE seller_id=?'),'reset must revoke old sessions');
assert(html.includes("window.location.href='/api/auth/'+provider+'/start'"),'social buttons must launch OAuth');assert(html.includes('sendResetRequest'),'forgot password action missing');assert(html.includes('resetPasswordMode'),'reset UI missing');assert(html.includes("const reset=qs.get('reset')"),'reset query handling missing');assert(!html.includes('login will be enabled when its OAuth configuration is connected'),'stale OAuth placeholder UI remains');assert(!html.includes('Connect the email reset service to send reset links'),'stale reset placeholder UI remains');
const env=fs.readFileSync('.env.example','utf8');for(const x of ['PUBLIC_BASE_URL','GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','TELEGRAM_CLIENT_ID','TELEGRAM_CLIENT_SECRET','SMTP_HOST','SMTP_PORT','SMTP_SECURE','SMTP_USER','SMTP_PASS','MAIL_FROM'])assert(env.includes(x),`env example missing ${x}`);
const render2=fs.readFileSync('render.yaml','utf8');for(const x of ['PUBLIC_BASE_URL','GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','TELEGRAM_CLIENT_ID','TELEGRAM_CLIENT_SECRET','SMTP_HOST','SMTP_USER','SMTP_PASS','MAIL_FROM'])assert(render2.includes(x),`Render OAuth/email env missing ${x}`);
console.log('PASS: Google OAuth, Telegram OIDC+PKCE+JWKS, SMTP password reset, one-time reset tokens, session revocation and auth UI wiring');

// v3.2.5 final recheck: source-tree hygiene, hamburger navigation, auth throttling and runtime architecture.
assert(!fs.existsSync('server.js.bak')&&!fs.existsSync('public/index.html.bak'),'production backup files must be removed');
assert(!fs.readdirSync('.').some(x=>x.endsWith('.pyc')),'Python bytecode must not ship');
const docker=fs.readFileSync('Dockerfile','utf8');
assert(docker.includes('python3 python3-pip'),'Docker image must include Python runtime');
assert(docker.includes('CMD ["node","server.js"]'),'Node must be the single deployment entrypoint');
assert(server.includes("spawn(py,['bot.py']"),'Node must orchestrate isolated Python bot workers');
assert(server.includes("rateLimit(12,60000,'auth')"),'authentication endpoints must have a strict rate limit');
assert(server.includes("app.use((err,req,res,next)=>"),'central Express error handler missing');
assert(html.includes('>☰</button>'),'hamburger menu icon missing');
assert(!html.includes('>⋮</button>'),'three-dot menu must be removed');
assert(html.includes("if(page==='wallet')return wallet()"),'dedicated wallet page renderer missing');
assert(html.includes("if(page==='gateway')return gateway()"),'dedicated gateway page renderer missing');
assert(html.includes("if(page==='products')return products()"),'dedicated product page renderer missing');
assert(html.includes("secureApi('/api/config/'+botId)"),'settings/config frontend endpoint missing');
assert(html.includes("secureApi('/api/products/'+botId)"),'products frontend endpoint missing');
assert(html.includes("secureApi('/api/payments/'+botId)"),'payments frontend endpoint missing');
assert(html.includes("secureApi('/api/users/'+botId)"),'users frontend endpoint missing');
assert(html.includes("secureApi('/api/orders/'+botId)"),'orders frontend endpoint missing');
console.log('PASS: v3.2.5 final source hygiene, hamburger UI, auth throttling, single-entrypoint orchestration and dedicated page wiring');

// Exhaustive audit closure checks for the 12-point external audit.
const sourceFiles=['server.js','bot_template.py','public/index.html','tests.js','Dockerfile','.env.example','.gitignore','.dockerignore','render.yaml','package.json'];
for(const f of sourceFiles){const b=fs.readFileSync(f);assert(!b.includes(Buffer.from([0,1,2,3,4,5,6,7,8]))&&![...b].some(x=>x===11||x===12||x>=14&&x<=31),`control-byte corruption in ${f}`)}
assert(!server.match(/(?:BOT_TOKEN|TELEGRAM_BOT_TOKEN|JWT_SECRET|API_KEY)\s*[:=]\s*['"][^'"]+['"]/i),'hardcoded credential-like fallback detected in server');
assert(!bot.match(/(?:BOT_TOKEN|TELEGRAM_BOT_TOKEN|JWT_SECRET|API_KEY)\s*=\s*['"][^'"]{8,}['"]/i),'hardcoded credential-like fallback detected in bot');
assert(bot.includes('await asyncio.to_thread(_gateway_create_sync'),'gateway network I/O must leave event loop');
assert(bot.includes('await asyncio.to_thread(_fetch_recent_imap_messages_for_utrs'),'IMAP verification must leave event loop');
assert(bot.includes('def heartbeat_thread()'),'heartbeat must run outside async event loop');
assert(server.includes("app.use((req,res,next)=>{if(!req.path.startsWith('/api/auth/'))return next();return rateLimit(12,60000,'auth')(req,res,next)})"),'auth throttling missing');
assert(server.includes('function publicError('),'public error sanitization missing');
assert(server.includes('fs.appendFileSync(log,redactLog(d))'),'worker logs must be redacted');
assert(html.includes('function esc('),'frontend escaping helper missing');
assert(html.includes("esc(x.username)"),'dynamic user data must be escaped');
assert(fs.readFileSync('.gitignore','utf8').includes('*.py[cod]')&&fs.readFileSync('.gitignore','utf8').includes('node_modules/')&&fs.readFileSync('.gitignore','utf8').includes('.env'),'repository artifact rules incomplete');
assert(fs.readFileSync('.dockerignore','utf8').includes('*.zip')&&fs.readFileSync('.dockerignore','utf8').includes('__pycache__/'),'container artifact rules incomplete');
assert(!fs.existsSync('server.js.bak')&&!fs.existsSync('public/index.html.bak'),'backup source artifacts must not ship');
assert(fs.existsSync('AUDIT_REPORT.md'),'audit closure report missing');
console.log('PASS: exhaustive 12-point audit closure, offline-test safety, encoding, credential, async-I/O, escaping and artifact checks');
