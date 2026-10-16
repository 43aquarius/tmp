// 绘影API直连工具 v2: 持久化设备身份(cookieId/sessionId绑定验证码)
// 用法: node migu_api.js sendSMS <手机号>
//       node migu_api.js loginBySMS <手机号> <验证码>
const crypto = require('crypto');
const fs = require('fs');

const RSA_PUB = fs.readFileSync('/home/z/my-project/scripts/rsa_pub.pem', 'utf8');
const BASE = 'https://ai.migudm.cn/ai-delivery-platform/api';
const ALPHA_KEY = 'A)o#LE2ZE_ay7H6br6w_Iaw1uO2@uoTL';
const IDENTITY_FILE = '/home/z/my-project/scripts/device_identity.json';

function wO(plain) {
  return crypto.publicEncrypt(
    { key: RSA_PUB, padding: crypto.constants.RSA_PKCS1_PADDING },
    Buffer.from(String(plain))).toString('base64');
}
function randStr(n) {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let s = '';
  for (let i = 0; i < n; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}
// 持久化设备身份: cookieId 长期不变, sessionId 30分钟内复用(模拟真实session)
function getIdentity() {
  let id = {};
  try { id = JSON.parse(fs.readFileSync(IDENTITY_FILE, 'utf8')); } catch { }
  if (!id.cookieId) id.cookieId = randStr(16);
  if (!id.sessionId || Date.now() - (id.sessionTs || 0) > 25 * 60 * 1000) {
    id.sessionId = `${randStr(8)}_${Date.now()}`;
    id.sessionTs = Date.now();
  }
  fs.writeFileSync(IDENTITY_FILE, JSON.stringify(id, null, 2));
  return id;
}
function buildHeaders(body, extra) {
  const id = getIdentity();
  const nonce = randStr(32);
  const ts = Date.now();
  const sigValues = [nonce, '102', ts, '1.0.0', 0];
  if (body !== undefined && body !== null) sigValues.push(JSON.stringify(body));
  const msg = sigValues.sort().join('');
  const sig = crypto.createHmac('sha256', ALPHA_KEY).update(msg, 'utf8').digest('hex');
  return {
    'Content-Type': 'application/json',
    'Origin': 'https://ai.migudm.cn',
    'Referer': 'https://ai.migudm.cn/',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'MG-nonce': nonce,
    'MG-platform': '102',
    'MG-timestamp': String(ts),
    'MG-clientVersion': '1.0.0',
    'MG-apiversion': '0',
    'MG-signature': sig,
    'MG-cookieId': id.cookieId,
    'MG-sessionId': id.sessionId,
    'MG-site-channel': 'aidelivery',
    'MG-channel': '750019779',
    'MG-portal': '01',
    ...(extra || {}),
  };
}
async function apiCall(path, body, extraHeaders) {
  const headers = buildHeaders(body, extraHeaders);
  const resp = await fetch(BASE + path, {
    method: 'POST', headers, body: JSON.stringify(body),
  });
  const text = await resp.text();
  let json = null;
  try { json = JSON.parse(text); } catch { }
  return { status: resp.status, json, text, headers: resp.headers };
}

async function main() {
  const [cmd, arg1, arg2] = process.argv.slice(2);
  if (cmd === 'sendSMS') {
    const r = await apiCall('/user/sendSMS', { mobile: wO(arg1) });
    console.log('sendSMS:', r.status, r.text.slice(0, 300));
  } else if (cmd === 'loginBySMS') {
    const r = await apiCall('/user/loginBySMS', { mobile: wO(arg1), validateCode: wO(arg2) });
    console.log('loginBySMS:', r.status, r.text.slice(0, 800));
    fs.writeFileSync('/home/z/my-project/dalian_video/login_response.json', r.text);
    const setCookie = r.headers.get('set-cookie');
    if (setCookie) fs.writeFileSync('/home/z/my-project/dalian_video/api_cookies.txt', setCookie);
    if (r.json && r.json.code === 0) {
      console.log('✅ 登录成功! data:', JSON.stringify(r.json.data).slice(0, 500));
    }
  } else if (cmd === 'queryUserInfo') {
    // 带上保存的token
    let auth = '';
    try { auth = fs.readFileSync('/home/z/my-project/dalian_video/api_token.txt', 'utf8').trim(); } catch { }
    const r = await apiCall('/user/queryUserInfo', {}, auth ? { 'MG-authorization': auth } : {});
    console.log('queryUserInfo:', r.status, r.text.slice(0, 400));
  } else {
    console.log('用法: node migu_api.js sendSMS <手机号> | loginBySMS <手机号> <验证码> | queryUserInfo');
  }
}
main().catch(e => console.error('ERROR:', e.message));
