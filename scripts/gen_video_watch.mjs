#!/usr/bin/env node
/**
 * 值守脚本: 循环 {收割已完成任务 → 提交新任务}
 * - 每轮最多提交 MAX_SUBMIT 个新任务(防429)
 * - 遇到429自动退避(本轮不提交, 加长下轮等待)
 * - 用法: node gen_video_watch.mjs [最大轮数, 默认200]
 */
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

const DIR = '/home/z/my-project/dalian_video';
const TASKS_FILE = `${DIR}/clips/video_tasks.json`;
const MAX_SUBMIT = 2;          // 每轮最多提交数
const ROUND_WAIT = 120000;     // 正常轮间隔2分钟
const BACKOFF_WAIT = 300000;   // 429退避5分钟

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
const LONG_SCENES = [2, 3, 6, 7, 9, 10, 14, 17, 18];

const sleep = ms => new Promise(r => setTimeout(r, ms));
const ts = () => new Date().toLocaleTimeString('zh-CN', { hour12: false });
function loadTasks() { try { return JSON.parse(fs.readFileSync(TASKS_FILE, 'utf8')); } catch { return {}; } }
function saveTasks(t) { fs.writeFileSync(TASKS_FILE, JSON.stringify(t, null, 2)); }
function clipPath(i) { return `${DIR}/clips/scene_${String(i).padStart(2, '0')}.mp4`; }
function framePath(i) { return `${DIR}/frames/scene_${String(i).padStart(2, '0')}.png`; }
function doneCount() { try { return fs.readdirSync(`${DIR}/clips`).filter(f => /^scene_\d+\.mp4$/.test(f)).length; } catch { return 0; } }

function findUrl(obj) {
  if (typeof obj === 'string' && obj.startsWith('http') && (obj.includes('.mp4') || obj.includes('video'))) return obj;
  if (Array.isArray(obj)) { for (const v of obj) { const r = findUrl(v); if (r) return r; } }
  if (obj && typeof obj === 'object') { for (const v of Object.values(obj)) { const r = findUrl(v); if (r) return r; } }
  return null;
}

async function submit(zai, sceneId) {
  const img = framePath(sceneId);
  if (!fs.existsSync(img)) { console.log(`[${ts()}] 场景${sceneId}: 无分镜图,跳过`); return 'NOIMG'; }
  const b64 = fs.readFileSync(img).toString('base64');
  const body = {
    image_url: `data:image/png;base64,${b64}`,
    prompt: MOTION[sceneId],
    duration: LONG_SCENES.includes(sceneId) ? 10 : 5,
  };
  try {
    const task = await zai.video.generations.create(body);
    if (task && task.id) {
      const tasks = loadTasks();
      tasks[sceneId] = { id: task.id, status: task.task_status, submitted: new Date().toISOString() };
      saveTasks(tasks);
      console.log(`[${ts()}] 场景${sceneId}: 已提交 ${task.id}`);
      return 'OK';
    }
    return 'NORSP';
  } catch (e) {
    const msg = e.message || '';
    if (msg.includes('429') || msg.toLowerCase().includes('rate') || msg.includes('频繁')) {
      console.log(`[${ts()}] 场景${sceneId}: 429限流`);
      return '429';
    }
    console.log(`[${ts()}] 场景${sceneId}: 提交失败 ${msg.slice(0, 80)}`);
    return 'FAIL';
  }
}

async function collect(zai) {
  const tasks = loadTasks();
  const pending = Object.entries(tasks).filter(([id, t]) =>
    !fs.existsSync(clipPath(id)) && t.status !== 'FAILED' && t.status !== 'DOWNLOADED');
  let running = 0;
  for (const [sceneId, t] of pending) {
    try {
      const r = await zai.queryAsyncResult(t.id);
      const status = r?.task_status || 'UNKNOWN';
      if (status === 'SUCCEED' || status === 'SUCCESS') {
        const url = findUrl(r);
        if (url) {
          const res = await fetch(url);
          if (res.ok) {
            const buf = Buffer.from(await res.arrayBuffer());
            fs.writeFileSync(clipPath(sceneId), buf);
            console.log(`[${ts()}] 场景${sceneId}: ✅下载 ${(buf.length / 1048576).toFixed(1)}MB`);
            t.status = 'DOWNLOADED';
            continue;
          }
        }
        console.log(`[${ts()}] 场景${sceneId}: 成功但无URL`);
      } else if (status === 'FAIL') {
        console.log(`[${ts()}] 场景${sceneId}: ❌失败,删除任务待重提`);
        delete tasks[sceneId];
        saveTasks(tasks);
        continue;
      } else {
        running++;
      }
      t.lastStatus = status;
      saveTasks(tasks);
    } catch (e) {
      console.log(`[${ts()}] 场景${sceneId}: 查询异常 ${e.message?.slice(0, 40)}`);
    }
    await sleep(2000);
  }
  return running;
}

async function main() {
  const maxRounds = parseInt(process.argv[2] || '200');
  const zai = await ZAI.create();
  console.log(`[${ts()}] === 值守启动, 完成${doneCount()}/18 ===`);
  for (let round = 1; round <= maxRounds; round++) {
    if (doneCount() >= 18) { console.log(`[${ts()}] 18/18全部完成!`); break; }
    // 1. 收割
    const running = await collect(zai);
    // 2. 提交(最多MAX_SUBMIT个)
    let submitted = 0, hit429 = false;
    const tasks = loadTasks();
    for (let i = 1; i <= 18 && submitted < MAX_SUBMIT && !hit429; i++) {
      if (fs.existsSync(clipPath(i))) continue;
      if (tasks[i] && tasks[i].status !== 'FAILED') continue;
      const r = await submit(zai, i);
      if (r === 'OK') { submitted++; await sleep(15000); }
      else if (r === '429') { hit429 = true; }
      else if (r === 'FAIL') { hit429 = true; }
    }
    console.log(`[${ts()}] 第${round}轮: 完成${doneCount()}/18, 提交${submitted}, 进行中${running}${hit429 ? ' [限流退避]' : ''}`);
    if (doneCount() >= 18) break;
    await sleep(hit429 ? BACKOFF_WAIT : ROUND_WAIT);
  }
  console.log(`[${ts()}] === 值守结束, 完成${doneCount()}/18 ===`);
  process.exit(0);
}

main().catch(e => { console.error(`[${ts()}] 💥`, e.message); process.exit(9); });
