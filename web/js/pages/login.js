// 登录/注册/游客进入
import { POST, setToken } from '../api.js';
import { h, toast, mascot } from '../ui.js';
import { store, deviceId, guestLogin } from '../store.js';
import { nav } from '../router.js';

export function renderLogin(page) {
  let mode = 'entry';   // entry | login | register
  const wrap = h('div', { class: 'login-wrap' });
  page.append(wrap);

  function draw() {
    wrap.innerHTML = '';
    wrap.append(
      h('div', { class: 'login-logo' },
        mascot(110),
        h('h1', {}, 'AI句灵'),
        h('p', {}, '让每一句话活过来 · 年轻人的文案社交圈')
      )
    );

    if (mode === 'entry') {
      wrap.append(
        h('div', { class: 'stagger' },
          h('button', {
            class: 'btn block', style: { marginBottom: '12px' },
            onclick: async () => {
              try { await guestLogin(); toast(`欢迎你，${store.me.nickname} ✨`); nav('/feed'); }
              catch (e) { toast(e.message, 'warn'); }
            }
          }, '🐾 游客一键进入'),
          h('button', { class: 'btn block ghost', style: { marginBottom: '12px' }, onclick: () => { mode = 'login'; draw(); } }, '账号登录'),
          h('button', { class: 'btn block ghost', onclick: () => { mode = 'register'; draw(); } }, '注册新账号'),
          h('div', { class: 'notice-bar', style: { marginTop: '22px' } },
            '进入即表示同意', h('a', { href: '#/about/agreement' }, '《用户协议》'), '与',
            h('a', { href: '#/about/privacy' }, '《隐私政策》'), '。',
            h('div', {}, '本应用包含 AI 生成内容（均有标识）。', store.boot?.compliance?.icp || '')
          )
        )
      );
      return;
    }

    const username = h('input', { class: 'input', placeholder: '用户名（3-20 位字母/数字/下划线）', autocomplete: 'username' });
    const password = h('input', { class: 'input', type: 'password', placeholder: '密码（至少 6 位）', autocomplete: 'current-password' });
    const nickname = h('input', { class: 'input', placeholder: '昵称（2-12 个字）' });
    const form = h('div', { class: 'stagger' },
      h('div', { class: 'field' }, username),
      h('div', { class: 'field' }, password),
      mode === 'register' ? h('div', { class: 'field' }, nickname) : null,
      h('button', {
        class: 'btn block',
        onclick: async () => {
          try {
            const body = { username: username.value.trim(), password: password.value, device_id: deviceId() };
            if (mode === 'register') body.nickname = nickname.value.trim() || username.value.trim();
            const data = await POST(mode === 'register' ? '/api/auth/register' : '/api/auth/login', body);
            setToken(data.token);
            store.me = data.user;
            toast(`欢迎${mode === 'register' ? '加入句灵' : '回来'}，${data.user.nickname} ✨`);
            nav('/feed');
          } catch (e) { toast(e.message, 'warn'); }
        }
      }, mode === 'register' ? '注册并进入' : '登录'),
      h('div', { class: 'divider' }, 'OR'),
      h('button', { class: 'btn block ghost', onclick: () => { mode = 'entry'; draw(); } }, '返回')
    );
    wrap.append(form);
  }
  draw();
}
