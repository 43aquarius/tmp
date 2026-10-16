#!/usr/bin/env node
/**
 * 视频生成工具：支持本地图片路径 → base64 → 图生视频
 * 用法: node gen_video.mjs <图片路径> <运动描述> <时长秒> <输出mp4> [分辨率]
 */
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';

const [imgPath, motionPrompt, duration, outPath, size] = process.argv.slice(2);

if (!imgPath || !motionPrompt || !duration || !outPath) {
  console.error('用法: node gen_video.mjs <图片> <运动描述> <时长> <输出> [尺寸如768x1344]');
  process.exit(1);
}

async function main() {
  const zai = await ZAI.create();

  // 读取本地图片转base64
  const buf = fs.readFileSync(imgPath);
  const b64 = buf.toString('base64');
  const ext = path.extname(imgPath).toLowerCase().replace('.', '');
  const mime = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : 'image/png';
  const dataUri = `data:${mime};base64,${b64}`;
  console.log(`📦 图片已编码: ${(b64.length / 1024).toFixed(0)}KB`);

  const body = {
    image_url: dataUri,
    prompt: motionPrompt,
    duration: parseInt(duration),
  };
  if (size) body.size = size;

  console.log('🎬 创建视频生成任务...');
  const task = await zai.video.generations.create(body);
  console.log(`✅ 任务创建成功 ID: ${task.id} 状态: ${task.task_status}`);

  // 轮询结果
  const maxPolls = 90;
  for (let i = 0; i < maxPolls; i++) {
    await new Promise(r => setTimeout(r, 8000));
    let result;
    try {
      result = await zai.queryAsyncResult(task.id);
    } catch (e) {
      console.log(`⏳ 轮询${i + 1}: 查询失败(${e.message?.slice(0, 60)}), 继续...`);
      continue;
    }

    const status = result?.task_status;
    if (i % 3 === 0) console.log(`⏳ 轮询${i + 1}/${maxPolls}: ${status || 'RUNNING'}`);

    if (status === 'SUCCEED' || status === 'SUCCESS') {
      // 查找视频URL
      function findUrl(obj) {
        if (typeof obj === 'string' && obj.startsWith('http') && (obj.includes('.mp4') || obj.includes('video'))) return obj;
        if (Array.isArray(obj)) { for (const v of obj) { const r = findUrl(v); if (r) return r; } }
        if (obj && typeof obj === 'object') { for (const v of Object.values(obj)) { const r = findUrl(v); if (r) return r; } }
        return null;
      }
      const videoUrl = findUrl(result);
      if (!videoUrl) {
        console.log('❌ 成功但未找到视频URL，完整结果:');
        console.log(JSON.stringify(result, null, 2).slice(0, 2000));
        process.exit(2);
      }
      console.log(`🔗 视频URL: ${videoUrl}`);
      // 下载
      const res = await fetch(videoUrl);
      if (!res.ok) { console.error(`❌ 下载失败: ${res.status}`); process.exit(3); }
      const arrayBuf = Buffer.from(await res.arrayBuffer());
      fs.writeFileSync(outPath, arrayBuf);
      console.log(`🎉 视频已保存: ${outPath} (${(arrayBuf.length / 1024 / 1024).toFixed(1)}MB)`);
      process.exit(0);
    }
    if (status === 'FAIL') {
      console.log('❌ 任务失败:');
      console.log(JSON.stringify(result, null, 2).slice(0, 1500));
      process.exit(4);
    }
  }
  console.log('⏰ 轮询超时');
  process.exit(5);
}

main().catch(e => { console.error('💥', e.message); process.exit(9); });
