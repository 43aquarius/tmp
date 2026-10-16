// 咪咕绘影平台 AI 视频生成客户端（逆向自前端 index-legacy）
// 用法:
//   node migu_video.js list                     # 查询图生视频任务列表
//   node migu_video.js upload <file>            # 上传图片 → objectId
//   node migu_video.js create <sceneJson>       # 创建图生视频任务
//   node migu_video.js download <recordId>      # 查询下载地址
//   node migu_video.js points                   # 查询AiQ积分余额
const crypto = require('crypto');
const fs = require('fs');

const BASE = 'https://ai.migudm.cn/ai-delivery-platform/api';
const ALPHA_KEY = 'A)o#LE2ZE_ay7H6br6w_Iaw1uO2@uoTL';
const IDENTITY_FILE = '/home/z/my-project/scripts/device_identity.json';
const TOKEN_FILE = '/home/z/my-project/dalian_video/api_token.txt';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36';

function randStr(n) {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let s = '';
  for (let i = 0; i < n; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}
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
// 签名: 5个基础头值 + token值(如有) + body JSON(FormData除外) 排序join后 HmacSHA256(ALPHA_KEY)
// (逆向确认: authorization在签名前写入, cookieId/sessionId/channel在签名后写入)
function buildHeaders(body, isForm, withAuth) {
  const id = getIdentity();
  const nonce = randStr(32);
  const ts = Date.now();
  let token = '';
  if (withAuth !== false) {
    try { token = fs.readFileSync(TOKEN_FILE, 'utf8').trim(); } catch { }
  }
  const sigValues = [nonce, '102', String(ts), '1.0.0', '0'];
  if (token) sigValues.push(token);
  if (body !== undefined && body !== null && !isForm) sigValues.push(JSON.stringify(body));
  const msg = sigValues.sort().join('');
  const sig = crypto.createHmac('sha256', ALPHA_KEY).update(msg, 'utf8').digest('hex');
  const h = {
    'User-Agent': UA,
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
  };
  if (withAuth !== false) {
    try { h['MG-authorization'] = fs.readFileSync(TOKEN_FILE, 'utf8').trim(); } catch { }
  }
  return h;
}
async function apiPost(path, body, isForm, withAuth) {
  const headers = buildHeaders(body, isForm, withAuth);
  let payload;
  if (isForm) {
    // body 已是 FormData; undici自动带boundary的Content-Type, 不手动设置
    payload = body;
  } else {
    headers['Content-Type'] = 'application/json';
    payload = body !== undefined && body !== null ? JSON.stringify(body) : undefined;
  }
  const resp = await fetch(BASE + path, { method: 'POST', headers, body: payload });
  const text = await resp.text();
  let json = null;
  try { json = JSON.parse(text); } catch { }
  return { status: resp.status, json, text };
}

async function main() {
  const [cmd, arg1, arg2] = process.argv.slice(2);
  if (cmd === 'list') {
    const r = await apiPost('/creative-tool/queryImageToVideoList', { pageNo: 1, pageSize: 20 });
    console.log('status:', r.status);
    console.log(r.text.slice(0, 2500));
  } else if (cmd === 'upload') {
    const fd = new FormData();
    fd.append('file', new Blob([fs.readFileSync(arg1)], { type: 'image/png' }), arg1.split('/').pop());
    const r = await apiPost('/file/uploadFiles', fd, true);
    console.log('status:', r.status);
    console.log(r.text.slice(0, 800));
    if (r.json && r.json.data && r.json.data.objectIdList) {
      fs.writeFileSync('/home/z/my-project/dalian_video/last_object_id.txt', r.json.data.objectIdList[0]);
      console.log('objectId:', r.json.data.objectIdList[0]);
    }
  } else if (cmd === 'create') {
    // arg1 = JSON字符串或文件路径
    let body;
    try { body = JSON.parse(fs.readFileSync(arg1, 'utf8')); }
    catch { body = JSON.parse(arg1); }
    const r = await apiPost('/creative-tool/createImageToVideo', body);
    console.log('status:', r.status);
    console.log(r.text.slice(0, 1500));
  } else if (cmd === 'points') {
    const r = await apiPost('/user/queryUserPoints', {});
    console.log('points:', r.status, r.text.slice(0, 400));
  } else if (cmd === 'quote') {
    // 积分报价: {applicationId:9, context:{qualityMode,resolution,durationSeconds}}
    const r = await apiPost('/points/quote', JSON.parse(arg1));
    console.log('quote:', r.status, r.text.slice(0, 400));
  } else if (cmd === 'raw') {
    // raw <path> <jsonBody>
    const r = await apiPost(arg1, arg2 ? JSON.parse(arg2) : {});
    console.log('raw:', r.status, r.text.slice(0, 2000));
  } else {
    console.log('用法: list | upload <file> | create <json|file> | points | quote <json> | raw <path> <json>');
  }
}
main().catch(e => console.error('ERROR:', e.message));
