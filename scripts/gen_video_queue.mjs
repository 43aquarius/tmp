#!/usr/bin/env node
/**
 * 视频生成流水线:
 *   submit模式: node gen_video_queue.mjs submit <场景号> — 提交任务保存taskID
 *   collect模式: node gen_video_queue.mjs collect — 收割所有已完成任务下载mp4
 *   auto模式: node gen_video_queue.mjs auto — 提交全部未完成任务(30s间隔)然后轮询收割
 */
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

const DIR = '/home/z/my-project/dalian_video';
const TASKS_FILE = `${DIR}/clips/video_tasks.json`;

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

// 10秒的镜头
const LONG_SCENES = [2, 3, 6, 7, 9, 10, 14, 17, 18];

function loadTasks() {
  try { return JSON.parse(fs.readFileSync(TASKS_FILE, 'utf8')); } catch { return {}; }
}
function saveTasks(t) { fs.writeFileSync(TASKS_FILE, JSON.stringify(t, null, 2)); }
function framePath(i) { return `${DIR}/frames/scene_${String(i).padStart(2, '0')}.png`; }
function clipPath(i) { return `${DIR}/clips/scene_${String(i).padStart(2, '0')}.mp4`; }

function findUrl(obj) {
  if (typeof obj === 'string' && obj.startsWith('http') && (obj.includes('.mp4') || obj.includes('video'))) return obj;
  if (Array.isArray(obj)) { for (const v of obj) { const r = findUrl(v); if (r) return r; } }
  if (obj && typeof obj === 'object') { for (const v of Object.values(obj)) { const r = findUrl(v); if (r) return r; } }
  return null;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function submit(zai, sceneId) {
  const img = framePath(sceneId);
  if (!fs.existsSync(img)) { console.log(`场景${sceneId}: 无分镜图`); return false; }
  const b64 = fs.readFileSync(img).toString('base64');
  const dataUri = `data:image/png;base64,${b64}`;
  const body = {
    image_url: dataUri,
    prompt: MOTION[sceneId],
    duration: LONG_SCENES.includes(sceneId) ? 10 : 5,
  };
  try {
    const task = await zai.video.generations.create(body);
    if (task && task.id) {
      const tasks = loadTasks();
      tasks[sceneId] = { id: task.id, status: task.task_status, submitted: new Date().toISOString() };
      saveTasks(tasks);
      console.log(`场景${sceneId}: 任务已提交 ${task.id} (${task.task_status})`);
      return true;
    }
  } catch (e) {
    console.log(`场景${sceneId}: 提交失败 - ${e.message?.slice(0, 80)}`);
  }
  return false;
}

async function collect(zai) {
  const tasks = loadTasks();
  const pending = Object.entries(tasks).filter(([id, t]) =>
    !fs.existsSync(clipPath(id)) && t.status !== 'FAILED');
  console.log(`待收割任务: ${pending.length}个`);
  let downloaded = 0, stillRunning = 0;

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
            console.log(`场景${sceneId}: ✅ 已下载 (${(buf.length / 1048576).toFixed(1)}MB)`);
            downloaded++;
            t.status = 'DOWNLOADED';
          }
        }
      } else if (status === 'FAIL') {
        console.log(`场景${sceneId}: ❌ 任务失败`);
        t.status = 'FAILED';
      } else {
        stillRunning++;
        if (Math.random() < 0.3) console.log(`场景${sceneId}: ${status}...`);
      }
      t.lastStatus = status;
    } catch (e) {
      console.log(`场景${sceneId}: 查询异常 ${e.message?.slice(0, 50)}`);
    }
    await sleep(3000);
  }
  saveTasks(tasks);
  console.log(`本轮: 下载${downloaded}, 进行中${stillRunning}`);
  return { downloaded, stillRunning };
}

async function main() {
  const [mode, arg] = process.argv.slice(2);
  const zai = await ZAI.create();

  if (mode === 'submit') {
    if (arg) {
      await submit(zai, parseInt(arg));
    } else {
      // 提交所有没有任务且没有视频的场景
      for (let i = 1; i <= 18; i++) {
        if (fs.existsSync(clipPath(i))) continue;
        const tasks = loadTasks();
        if (tasks[i] && tasks[i].status !== 'FAILED') continue;
        const ok = await submit(zai, i);
        if (!ok) break; // 连续失败(429)则停止
        await sleep(30000); // 30秒间隔防限流
      }
    }
  } else if (mode === 'collect') {
    await collect(zai);
  } else if (mode === 'auto') {
    // 提交后立即开始收割循环
    const tasks0 = loadTasks();
    for (let i = 1; i <= 18; i++) {
      if (fs.existsSync(clipPath(i))) continue;
      if (tasks0[i] && tasks0[i].status !== 'FAILED') continue;
      await submit(zai, i);
      await sleep(30000);
    }
    // 收割循环: 最多25轮, 每轮间隔20秒
    for (let round = 0; round < 25; round++) {
      const { downloaded, stillRunning } = await collect(zai);
      const done = fs.readdirSync(`${DIR}/clips`).filter(f => f.startsWith('scene_') && f.endsWith('.mp4')).length;
      console.log(`--- 第${round + 1}轮结束, 总完成${done}/18 ---`);
      if (done >= 18 || (stillRunning === 0 && downloaded === 0)) break;
      await sleep(20000);
    }
  }
  process.exit(0);
}

main().catch(e => { console.error('💥', e.message); process.exit(9); });
