function ease(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }
function progress(now, item) { return Math.max(0, Math.min(1, (now - item.time) / item.duration)); }
function applyAction(ctx, action, p) {
  const e = ease(p);
  if (action === 'fade_out') ctx.globalAlpha *= 1 - e;
  if (action === 'glow') ctx.globalAlpha *= 0.6 + 0.4 * Math.sin(p * Math.PI);
  if (action === 'line_flow') ctx.setLineDash([20 * e + 4, 10]);
  if (action === 'move_left_to_right' || action === 'cloud_float') ctx.translate(e * 80, 0);
  if (action === 'walk') ctx.translate(e * 70, Math.sin(e * Math.PI * 4) * 3);
  if (action === 'run') ctx.translate(e * 120, Math.sin(e * Math.PI * 8) * 5);
  if (action === 'heartbeat_once') { const s = 1 + Math.sin(p * Math.PI * 2) * 0.16; ctx.scale(s, s); }
  if (action === 'crack') ctx.translate((Math.random() - 0.5) * 2 * e, 0);
}
function stroke(ctx, color = '#1f2430', width = 2) { ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; }
function drawLinePerson(ctx, element, p = 1) {
  const { x, y } = element.position; stroke(ctx, '#222532', element.style.strokeWidth || 3);
  ctx.beginPath(); ctx.arc(x, y - 58, 16, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x, y - 42); ctx.lineTo(x, y + 8); ctx.moveTo(x, y - 20); ctx.lineTo(x - 24, y - 4 + Math.sin(p * 6) * 4); ctx.moveTo(x, y - 18); ctx.lineTo(x + 26, y - 8); ctx.moveTo(x, y + 8); ctx.lineTo(x - 22, y + 48); ctx.moveTo(x, y + 8); ctx.lineTo(x + 22, y + 48); ctx.stroke();
}
function drawWindLine(ctx, element, p = 0) { const { x, y } = element.position; stroke(ctx, '#6b7d90', 2); for (let i = 0; i < 4; i++) { ctx.beginPath(); const yy = y + i * 24; ctx.moveTo(x - 40 + p * 120, yy); ctx.bezierCurveTo(x + 40 + p * 100, yy - 22, x + 140 + p * 80, yy + 22, x + 240 + p * 70, yy); ctx.stroke(); } }
function drawRain(ctx, element, p = 0) { stroke(ctx, '#8190a8', 2); const count = Math.floor(18 * (1 - Math.max(0, p - 0.65))); for (let i = 0; i < count; i++) { const x = (i * 47 + p * 80) % 330 + 20; const y = (i * 31 + p * 260) % 260 + 70; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - 10, y + 30); ctx.stroke(); } drawWave(ctx, { position: { x: 180, y: 380 }, style: {} }, p); }
function drawSnow(ctx, element, p = 0) { stroke(ctx, '#edf6ff', 2); for (let i = 0; i < 20; i++) { const x = (i * 43 + Math.sin(p * 3 + i) * 20) % 340 + 10; const y = (i * 29 + p * 180) % 280 + 70; ctx.beginPath(); ctx.arc(x, y, 2 + (i % 3), 0, Math.PI * 2); ctx.stroke(); } }
function drawHeart(ctx, element, p = 1) { const { x, y } = element.position; stroke(ctx, '#e85b7d', 2); ctx.beginPath(); ctx.moveTo(x, y); ctx.bezierCurveTo(x - 35, y - 35, x - 70, y + 15, x, y + 58); ctx.bezierCurveTo(x + 70, y + 15, x + 35, y - 35, x, y); ctx.stroke(); }
function drawBrokenHeart(ctx, element, p = 1) { drawHeart(ctx, element, p); const { x, y } = element.position; stroke(ctx, '#e85b7d', 2); ctx.beginPath(); ctx.moveTo(x, y + 4); ctx.lineTo(x - 8, y + 22); ctx.lineTo(x + 5, y + 34); ctx.lineTo(x - 4, y + 54); ctx.stroke(); }
function drawWave(ctx, element, p = 0) { const { x, y } = element.position; stroke(ctx, '#5f91b8', 2); for (let i = 0; i < 3; i++) { ctx.beginPath(); ctx.ellipse(x, y + i * 12, 20 + p * 80 + i * 20, 6 + p * 12, 0, 0, Math.PI * 2); ctx.stroke(); } }
function drawCloud(ctx, element, p = 0) { const { x, y } = element.position; stroke(ctx, '#9ba9bd', 2); ctx.beginPath(); ctx.arc(x, y, 20, Math.PI, 0); ctx.arc(x + 28, y - 12, 24, Math.PI, 0); ctx.arc(x + 60, y, 18, Math.PI, 0); ctx.moveTo(x - 20, y); ctx.lineTo(x + 80, y); ctx.stroke(); }
function drawCat(ctx, element, p = 0) { const { x, y } = element.position; stroke(ctx, '#24242e', 2); ctx.beginPath(); ctx.arc(x, y, 23, 0, Math.PI * 2); ctx.moveTo(x - 14, y - 18); ctx.lineTo(x - 23, y - 38); ctx.lineTo(x - 4, y - 24); ctx.moveTo(x + 14, y - 18); ctx.lineTo(x + 23, y - 38); ctx.lineTo(x + 4, y - 24); ctx.moveTo(x - 7, y + 5); ctx.lineTo(x + 7, y + 5); ctx.stroke(); }
function drawLightDot(ctx, element, p = 0) { const { x, y } = element.position; ctx.fillStyle = `rgba(255,214,130,${0.2 + p * 0.8})`; for (let i = 0; i < 12; i++) { ctx.beginPath(); ctx.arc(x + Math.cos(i) * 50 * p, y + Math.sin(i * 2) * 28 * p, 3, 0, Math.PI * 2); ctx.fill(); } }
function drawTextGlow(ctx, text, p, width) { ctx.save(); ctx.font = '24px sans-serif'; ctx.fillStyle = `rgba(255,255,255,${0.3 + 0.5 * p})`; ctx.shadowColor = '#fff3bd'; ctx.shadowBlur = 20 * p; wrapText(ctx, text, width / 2, 80, width - 64, 30); ctx.restore(); }
function drawTextToLine(ctx, text, p, width) { stroke(ctx, `rgba(255,255,255,${p})`, 1); for (let i = 0; i < Math.min(text.length, 20); i++) { ctx.beginPath(); ctx.moveTo(40 + i * 12, 130); ctx.lineTo(40 + i * 12 + 20 * p, 130 + Math.sin(i) * 50 * p); ctx.stroke(); } }
function wrapText(ctx, text, x, y, maxWidth, lineHeight) { const chars = String(text).split(''); let line = ''; ctx.textAlign = 'center'; chars.forEach((ch, idx) => { const test = line + ch; if (ctx.measureText(test).width > maxWidth && idx > 0) { ctx.fillText(line, x, y); line = ch; y += lineHeight; } else line = test; }); ctx.fillText(line, x, y); }
const DRAWERS = { line_person: drawLinePerson, wind_line: drawWindLine, rain: drawRain, snow: drawSnow, heart_line: drawHeart, broken_heart: drawBrokenHeart, wave: drawWave, cloud: drawCloud, cat: drawCat, light_dot: drawLightDot, two_people(ctx, e, p) { drawLinePerson(ctx, { ...e, position: { x: e.position.x - 24, y: e.position.y } }, p); drawLinePerson(ctx, { ...e, position: { x: e.position.x + 36 - p * 20, y: e.position.y } }, p); } };
function renderManifest(ctx, manifest, seconds, width, height) {
  const colors = manifest.background && manifest.background.colors || ['#F6F3EE', '#DDE7F0'];
  const grd = ctx.createLinearGradient(0, 0, width, height); grd.addColorStop(0, colors[0]); grd.addColorStop(1, colors[1]); ctx.fillStyle = grd; ctx.fillRect(0, 0, width, height);
  const active = (manifest.timeline || []).filter((item) => seconds >= item.time && seconds <= item.time + item.duration);
  active.forEach((item) => { if (item.target === 'text') { const p = progress(seconds, item); item.action === 'glow' ? drawTextGlow(ctx, manifest.text, p, width) : drawTextToLine(ctx, manifest.text, p, width); } });
  (manifest.elements || []).forEach((element) => {
    const item = active.find((line) => line.target === element.id) || { action: 'line_flow', time: 0, duration: manifest.duration || 6 };
    const p = progress(seconds, item); ctx.save(); ctx.globalAlpha = element.style && element.style.opacity || 0.85; applyAction(ctx, item.action, p); const drawer = DRAWERS[element.type] || drawLightDot; drawer(ctx, element, p); ctx.restore();
  });
  const fade = active.find((item) => item.target === 'all' && item.action === 'fade_out'); if (fade) { ctx.fillStyle = `rgba(247,244,239,${progress(seconds, fade) * 0.85})`; ctx.fillRect(0, 0, width, height); }
}
module.exports = { renderManifest, drawLinePerson, drawWindLine, drawRain, drawSnow, drawHeart, drawBrokenHeart, drawWave, drawCloud, drawCat, drawLightDot, drawTextGlow, drawTextToLine, animateMove: applyAction, animateFade: applyAction, animateScale: applyAction, animateShake: applyAction, animateHeartbeat: applyAction, animateLineFlow: applyAction, animateParticleGather: applyAction, animateParticleScatter: applyAction };
