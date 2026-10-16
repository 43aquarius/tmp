// 咪咕绘影大赛平台(/app-api)客户端 — 逆向自 interactive/match bundle
// 用法:
//   node migu_match.js test                    # 测试API连通性
//   node migu_match.js sendSMS                 # 发送验证码到19824936641
//   node migu_match.js login <验证码>           # 登录保存token
//   node migu_match.js activity                # 查询活动信息
//   node migu_match.js mygroup                 # 查询我的团队
//   node migu_match.js remaining               # 今日剩余提交次数
//   node migu_match.js myworks                 # 我的作品列表
//   node migu_match.js upload <file>           # 上传文件(带审核轮询) → url
//   node migu_match.js publish                 # 发布作品(读取publish_config.json)
const crypto = require('crypto');
const fs = require('fs');

const BASE = 'https://ai.migudm.cn/aigc-work/app-api';
const PHONE = '19824936641';
const TOKEN_FILE = '/home/z/my-project/dalian_video/match_token.json';
const PUB_CFG = '/home/z/my-project/dalian_video/publish_config.json';
const ACTIVITY_CODE = 'MGCP_AIGAME_2026';
const CATEGORY = 'gcxy'; // 家乡文旅与国潮创新
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36';

const RSA_PUB = `-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQClAeRxFnwoVCdgRvaVgMTCAd5XtuvD2bWLCRWkq8NKLoYsF7I/t37LL9+TeLg/py7uB3yaH9ci5KccbHqHTGs4CLJ2LaJAxiLU0YpGx5cR3ZAvOK9WDdFMeJnSJvOajFT1EqTguZT9lPrYJtLogOMjho1BYPwvnr4aSbwftIIzTwIDAQAB
-----END PUBLIC KEY-----`;

// JSEncrypt兼容: PKCS1v1.5 + hex输出
function rsaHex(plain) {
  const buf = crypto.publicEncrypt(
    { key: RSA_PUB, padding: crypto.constants.RSA_PKCS1_PADDING },
    Buffer.from(String(plain), 'utf8'));
  return buf.toString('hex');
}

function loadToken() {
  try { return JSON.parse(fs.readFileSync(TOKEN_FILE, 'utf8')); } catch { return {}; }
}
function saveToken(t) { fs.writeFileSync(TOKEN_FILE, JSON.stringify(t, null, 2)); }

async function api(method, path, body, opts = {}) {
  const headers = {
    'User-Agent': UA,
    'Origin': 'https://ai.migudm.cn',
    'Referer': 'https://ai.migudm.cn/interactive/match/home',
    ...opts.headers,
  };
  const tok = loadToken();
  if (tok.accessToken && !opts.noAuth) headers['Authorization'] = `Bearer ${tok.accessToken}`;
  let payload;
  if (body instanceof FormData) { payload = body; }
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  const url = BASE + path;
  const resp = await fetch(url, { method, headers, body: payload, signal: AbortSignal.timeout(opts.timeoutMs || 30000) });
  const text = await resp.text();
  let json = null;
  try { json = JSON.parse(text); } catch { }
  return { status: resp.status, json, text };
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function sendSMS() {
  const r = await api('POST', '/member/auth/send-sms-code/v1', { mobile: rsaHex(PHONE), scene: 1 }, { noAuth: true });
  console.log(`sendSMS → ${r.status}`);
  console.log(r.text.slice(0, 400));
  if (r.json && r.json.data && r.json.data.sessionid) {
    const t = loadToken();
    t.sessionid = r.json.data.sessionid;
    saveToken(t);
    console.log('✅ sessionid已保存:', t.sessionid);
  }
}

async function login(code) {
  const t = loadToken();
  const r = await api('POST', '/member/auth/login/v1',
    { mobile: rsaHex(PHONE), smsCode: rsaHex(String(code).trim()), sessionid: t.sessionid || '' }, { noAuth: true });
  console.log(`login → ${r.status}`);
  const d = r.json && (r.json.data || r.json);
  if (d && d.accessToken) {
    saveToken({ ...t, ...d });
    console.log('✅ 登录成功, token已保存');
  } else {
    console.log(r.text.slice(0, 400));
  }
}

async function activity() {
  const r = await api('GET', `/activity/get?activityCode=${ACTIVITY_CODE}`);
  console.log(`activity → ${r.status}`);
  console.log(r.text.slice(0, 800));
}

async function mygroup() {
  const r = await api('GET', `/activity/participant-group/get-my?activityCode=${ACTIVITY_CODE}`);
  console.log(`mygroup → ${r.status}`);
  console.log(r.text.slice(0, 1200));
}

async function remaining() {
  const r = await api('GET', `/activity/video-work/publish/today-remaining?activityCode=${ACTIVITY_CODE}`);
  console.log(`remaining → ${r.status}`);
  console.log(r.text.slice(0, 400));
}

async function myworks() {
  const r = await api('GET', `/activity/video-work/my-page?pageNum=1&pageSize=10`);
  console.log(`myworks → ${r.status}`);
  console.log(r.text.slice(0, 20000));
}

async function auditQuery() {
  const t = loadToken();
  if (!t.auditBizId) {
    // 从myworks取最新作品的auditBizId
    const r = await api('GET', `/activity/video-work/my-page?pageNum=1&pageSize=10`);
    const list = r.json && r.json.data && r.json.data.list || [];
    if (!list.length) { console.log('无作品'); return; }
    t.auditBizId = list[0].auditBizId;
    saveToken(t);
  }
  const r = await api('GET', `/infra/file/audit-result?auditBizId=${t.auditBizId}`);
  console.log(`audit → ${r.status}`);
  console.log(r.text.slice(0, 600));
}

async function uploadFile(file) {
  const buf = fs.readFileSync(file);
  const fd = new FormData();
  fd.append('file', new Blob([buf]), file.split('/').pop());
  fd.append('path', file.split('/').pop());
  console.log(`上传 ${file} (${(buf.length / 1048576).toFixed(1)}MB)...`);
  const r = await api('POST', '/infra/file/upload-after-audit', fd, { timeoutMs: 15 * 60 * 1000 });
  console.log(`upload → ${r.status}`);
  if (!r.json) { console.log(r.text.slice(0, 300)); return null; }
  const d = r.json.data || r.json;
  console.log('上传响应:', JSON.stringify(d).slice(0, 400));
  if (!d.auditBizId) {
    if (d.url) return d.url;
    return null;
  }
  // 轮询审核
  const t0 = Date.now();
  while (Date.now() - t0 < 5 * 60 * 1000) {
    await sleep(4000);
    const a = await api('GET', `/infra/file/audit-result?auditBizId=${d.auditBizId}`);
    const ad = a.json ? (a.json.data || a.json) : null;
    if (ad) {
      console.log(`审核状态: ${ad.auditStatus}`);
      if (ad.auditStatus === 2 && ad.url) return ad.url;
      if (ad.auditStatus === 3) { console.log('❌ 审核拒绝'); return null; }
    }
  }
  console.log('审核超时');
  return null;
}

async function publish() {
  const cfg = JSON.parse(fs.readFileSync(PUB_CFG, 'utf8'));
  const body = {
    activityCode: ACTIVITY_CODE,
    categoryNodeCode: CATEGORY,
    sourceType: 4,
    workData: '',
    name: cfg.name,
    description: cfg.description,
    coverUrl: cfg.coverUrl,
    previewUrl: cfg.previewUrl,
    roles: [],
  };
  console.log('发布payload:', JSON.stringify({ ...body, description: body.description.slice(0, 40) + '...' }));
  const r = await api('POST', '/activity/video-work/publish', body);
  console.log(`publish → ${r.status}`);
  console.log(r.text.slice(0, 800));
}

async function main() {
  const cmd = process.argv[2];
  if (cmd === 'test') {
    const r = await api('POST', '/member/auth/login/v1', { mobile: 'x', smsCode: 'y' }, { noAuth: true });
    console.log(`test → ${r.status} (期望非404即通)`);
    console.log(r.text.slice(0, 200));
  } else if (cmd === 'sendSMS') await sendSMS();
  else if (cmd === 'login') await login(process.argv[3]);
  else if (cmd === 'activity') await activity();
  else if (cmd === 'mygroup') await mygroup();
  else if (cmd === 'remaining') await remaining();
  else if (cmd === 'myworks') await myworks();
  else if (cmd === 'audit') await auditQuery();
  else if (cmd === 'upload') {
    const url = await uploadFile(process.argv[3]);
    if (url) console.log('✅ URL:', url);
  } else if (cmd === 'publish') await publish();
  else console.log('用法: test|sendSMS|login <code>|activity|mygroup|remaining|myworks|upload <file>|publish');
}
main().catch(e => console.error('ERROR:', e.message));
