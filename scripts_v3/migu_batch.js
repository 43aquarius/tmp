// 咪咕绘影平台批量图生视频: 上传分镜图→创建任务→轮询→下载
// 用法: node migu_batch.mjs submit   — 上传+提交全部计划场景
//       node migu_batch.mjs poll     — 轮询+下载已完成任务
//       node migu_batch.mjs status   — 查看状态
const crypto = require('crypto');
const fs = require('fs');

const BASE = 'https://ai.migudm.cn/ai-delivery-platform/api';
const ALPHA_KEY = 'A)o#LE2ZE_ay7H6br6w_Iaw1uO2@uoTL';
const IDENTITY_FILE = '/home/z/my-project/scripts/device_identity.json';
const TOKEN_FILE = '/home/z/my-project/dalian_video/api_token.txt';
const STATE_FILE = '/home/z/my-project/dalian_video/migu_tasks.json';
const DIR = '/home/z/my-project/dalian_video';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36';

// 运动提示词(与叙事匹配)
const MOTION = {
  1: "雨丝缓缓落下，霓虹灯光流动闪烁，女孩撑伞缓步走出，镜头缓慢推近",
  2: "白色羽毛缓缓飘落，柔光微粒飘散，信封微微发光脉动，窗帘轻轻飘动",
  3: "晨光缓缓移动变幻，羽毛轻轻颤动，光影在信封上流动，浅景深焦点微移",
  4: "海鸥精灵歪头眨眼，翅膀轻轻抖动，女孩缓步走近微笑，阳光光斑闪烁",
  5: "海鸥精灵展翅低飞向前，女孩拖着行李箱奔跑跟随，阳光光斑从画面掠过",
  6: "海鸥群盘旋飞舞俯冲，女孩抛洒食物，海浪缓缓起伏，风筝轻轻飘动",
  7: "车厢轻微摇晃，窗外街景缓缓流动后退，阳光光斑在车厢内缓缓移动",
  8: "云影缓缓流动，鸽子踱步啄食，镜头缓慢横移展现广场建筑",
  9: "铁板焖子滋滋冒泡冒热气，热气缓缓升腾，芝麻酱缓缓流下，奶奶微笑递盘子",
  10: "海浪层层拍打礁石，女孩发丝被海风吹起，白云缓缓移动，镜头缓慢右移",
  11: "暖金光晕缓缓流动，海鸥缓缓盘旋，人物衣角轻轻飘动，柔焦光斑闪烁",
  12: "水面波光荡漾，游船缓缓划过，建筑倒影轻轻摇晃，夕阳光线流动",
  13: "大桥灯光缓缓闪烁流动，海面倒影微微荡漾，镜头缓慢推近",
  14: "夕阳金光在海面缓缓流动，女孩缓缓打开信纸，信纸泛起柔光，发丝轻动",
  15: "夕阳光斑缓缓移动，羽毛轻轻颤动，光线在信纸上缓缓流动",
  16: "海鸥精灵轻轻抖动羽毛，女孩侧头微笑，逆光轮廓光晕缓缓流动",
  17: "朝阳缓缓升起金光渐强，女孩打电话微笑，海鸥精灵振翅，远处海鸥群飞过",
  18: "海鸥群展翅飞过海面，金光闪烁荡漾，镜头缓缓上升俯瞰大海",
};

// 今日预算计划: 2520/2600 AiQ (480P标准=40/s)
// 场景: 时长(秒) — 场景1已完成(720P)
const PLAN = {
  2: 4, 4: 5, 5: 5, 6: 5, 9: 5, 11: 5, 14: 10, 15: 4, 16: 5, 17: 5, 18: 10,
};

function rs(n) {
  const c = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let s = '';
  for (let i = 0; i < n; i++) s += c[Math.floor(Math.random() * c.length)];
  return s;
}
function getIdentity() {
  let id = {};
  try { id = JSON.parse(fs.readFileSync(IDENTITY_FILE, 'utf8')); } catch { }
  if (!id.cookieId) id.cookieId = rs(16);
  if (!id.sessionId || Date.now() - (id.sessionTs || 0) > 25 * 60 * 1000) {
    id.sessionId = `${rs(8)}_${Date.now()}`;
    id.sessionTs = Date.now();
  }
  fs.writeFileSync(IDENTITY_FILE, JSON.stringify(id, null, 2));
  return id;
}
async function apiPost(path, body, isForm) {
  const id = getIdentity();
  const nonce = rs(32);
  const ts = Date.now();
  let token = '';
  try { token = fs.readFileSync(TOKEN_FILE, 'utf8').trim(); } catch { }
  const sv = [nonce, '102', String(ts), '1.0.0', '0'];
  if (token) sv.push(token);
  if (body !== undefined && body !== null && !isForm) sv.push(JSON.stringify(body));
  const sig = crypto.createHmac('sha256', ALPHA_KEY).update(sv.sort().join(''), 'utf8').digest('hex');
  const headers = {
    'User-Agent': UA,
    'MG-nonce': nonce, 'MG-platform': '102', 'MG-timestamp': String(ts),
    'MG-clientVersion': '1.0.0', 'MG-apiversion': '0', 'MG-signature': sig,
    'MG-cookieId': id.cookieId, 'MG-sessionId': id.sessionId,
    'MG-site-channel': 'aidelivery', 'MG-channel': '750019779', 'MG-portal': '01',
  };
  if (token) headers['MG-authorization'] = token;
  let payload;
  if (isForm) { payload = body; }
  else { headers['Content-Type'] = 'application/json'; payload = body != null ? JSON.stringify(body) : undefined; }
  const resp = await fetch(BASE + path, { method: 'POST', headers, body: payload });
  const text = await resp.text();
  let json = null;
  try { json = JSON.parse(text); } catch { }
  return { status: resp.status, json, text };
}
function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch { return { tasks: {}, scene1: { recordId: 656, downloaded: true } }; }
}
function saveState(s) { fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2)); }
const frame = i => `${DIR}/frames/scene_${String(i).padStart(2, '0')}.png`;
const clip = i => `${DIR}/migu_clips/scene_${String(i).padStart(2, '0')}.mp4`;
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function submitAll() {
  const state = loadState();
  for (const sceneId of Object.keys(PLAN).map(Number)) {
    if (state.tasks[sceneId] && state.tasks[sceneId].recordId) {
      console.log(`场景${sceneId}: 已提交(recordId=${state.tasks[sceneId].recordId}), 跳过`);
      continue;
    }
    const img = frame(sceneId);
    if (!fs.existsSync(img)) { console.log(`场景${sceneId}: 无分镜图!`); continue; }
    // 上传
    const fd = new FormData();
    fd.append('file', new Blob([fs.readFileSync(img)], { type: 'image/png' }), img.split('/').pop());
    const up = await apiPost('/file/uploadFiles', fd, true);
    let objectId = null;
    try { objectId = up.json.data.objectIdList[0]; } catch { }
    if (!objectId) { console.log(`场景${sceneId}: 上传失败 ${up.text.slice(0, 120)}`); continue; }
    console.log(`场景${sceneId}: 上传OK objectId=${objectId.slice(0, 12)}...`);
    // 创建任务
    const body = {
      imageIdList: [objectId],
      prompt: MOTION[sceneId],
      ratio: '9:16',
      qualityMode: 0,
      resolution: '480P',
      duration: PLAN[sceneId],
    };
    const cr = await apiPost('/creative-tool/createImageToVideo', body);
    let rec = null;
    try { rec = cr.json.data.record; } catch { }
    if (!rec) { console.log(`场景${sceneId}: 创建失败 ${cr.text.slice(0, 150)}`); continue; }
    state.tasks[sceneId] = {
      recordId: rec.id, objectId, duration: PLAN[sceneId],
      submitted: new Date().toISOString(), status: rec.status,
    };
    saveState(state);
    console.log(`场景${sceneId}: ✅ 已创建 recordId=${rec.id} (${PLAN[sceneId]}s 480P, 预计消耗${PLAN[sceneId] * 40}AiQ)`);
    await sleep(1500);
  }
  // 查余额
  const p = await apiPost('/points/queryUserPointsInfo', {});
  try { console.log(`当前AiQ余额: ${p.json.data.points.total}`); } catch { }
}

async function pollAll(download = true) {
  const state = loadState();
  const all = { ...(state.scene1 ? { 1: state.scene1 } : {}), ...state.tasks };
  const pending = Object.entries(all).filter(([k, v]) => !v.downloaded).map(([k, v]) => [Number(k), v]);
  if (!pending.length) { console.log('全部完成!'); return; }
  const ids = pending.map(([, v]) => v.recordId);
  const r = await apiPost('/creative-tool/queryImageToVideoList', { recordIdList: ids, limit: 50 });
  let list = [];
  try { list = r.json.data.recordList; } catch { console.log('查询失败', r.text.slice(0, 150)); return; }
  for (const rec of list) {
    const sceneId = Number(Object.entries(all).find(([k, v]) => v.recordId === rec.id)?.[0] || 0);
    if (!sceneId) continue;
    const results = rec.resultList || [];
    const main = results[0] || {};
    const st = rec.status;
    if (st === 'SUCCEEDED' && main.videoUrl) {
      if (download) {
        try {
          const resp = await fetch(main.videoUrl);
          const buf = Buffer.from(await resp.arrayBuffer());
          fs.writeFileSync(clip(sceneId), buf);
          state.tasks[sceneId] = state.tasks[sceneId] || all[sceneId];
          state.tasks[sceneId].downloaded = true;
          state.tasks[sceneId].videoUrl = main.videoUrl;
          state.tasks[sceneId].status = 'SUCCEEDED';
          saveState(state);
          console.log(`场景${sceneId}: ✅ 下载完成 ${(buf.length / 1048576).toFixed(1)}MB`);
        } catch (e) { console.log(`场景${sceneId}: 下载失败 ${e.message}`); }
      } else {
        console.log(`场景${sceneId}: SUCCEEDED(未下载)`);
      }
    } else if (st === 'FAILED' || st === 'PARTIAL_FAILED') {
      console.log(`场景${sceneId}: ❌ 失败 code=${main.errorCode} msg=${(main.msg || '').slice(0, 80)}`);
      state.tasks[sceneId] = state.tasks[sceneId] || all[sceneId];
      state.tasks[sceneId].status = st;
      state.tasks[sceneId].failed = true;
      saveState(state);
    } else {
      console.log(`场景${sceneId}: ${st} (预计完成: ${(main.expectedCompleteTime || '').slice(11, 19)})`);
    }
  }
}

async function main() {
  const cmd = process.argv[2] || 'status';
  if (cmd === 'submit') await submitAll();
  else if (cmd === 'poll') await pollAll(true);
  else if (cmd === 'status') {
    const state = loadState();
    const all = { ...(state.scene1 ? { 1: state.scene1 } : {}), ...state.tasks };
    for (const [k, v] of Object.entries(all).sort((a, b) => a[0] - b[0])) {
      console.log(`场景${k}: recordId=${v.recordId} status=${v.status || '?'} downloaded=${!!v.downloaded}`);
    }
  }
}
main().catch(e => console.error('ERROR:', e.message));
