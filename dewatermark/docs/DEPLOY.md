# 部署指南

## 0. 前置条件

- 一个**已认证**的微信小程序账号（个人主体即可，但「流量主」需满足条件，见 MONETIZE）。
- 微信开发者工具（最新稳定版）。
- 基础库 ≥ 2.2.3（云开发）、≥ 2.0.4（激励视频广告）。

## 1. 导入与 AppID

1. 微信开发者工具 → 导入项目 → 目录选 `dewatermark/`。
2. 填入你的小程序 **AppID**（测试可先用「测试号」，但广告与云开发需要正式 AppID）。
3. `project.config.json` 已配置 `miniprogramRoot=miniprogram/`、`cloudfunctionRoot=cloudfunctions/`。

## 2. 开通云开发

1. 工具顶部点「云开发」→ 开通（首次会让你选按量付费/包月，个人起步按量即可）。
2. 新建环境，记下**环境 ID**（形如 `prod-xxxxxx`）。
3. 打开 `miniprogram/config.js`，把 `cloudEnv` 改成你的环境 ID。

## 3. 部署云函数

> 云函数依赖 `wx-server-sdk`，在云端安装，本地无需 `npm install`。

1. 右键 `cloudfunctions/parse` → **上传并部署：云端安装依赖**。
2. 右键 `cloudfunctions/login` → 同样上传并部署。
3. 右键 `cloudfunctions/stats` → 同样上传并部署（数据看板用）。
4. 右键 `cloudfunctions/history` → 同样上传并部署（解析记录云端同步用）。
5. 部署完成后，「云开发控制台 → 云函数」能看到 `parse`、`login`、`stats`、`history`。

### （可选）云函数环境变量

在「云开发控制台 → 云函数 → parse → 配置 → 环境变量」里可设置：

| 变量 | 作用 | 示例 |
| --- | --- | --- |
| `PROXY_TO_STORAGE` | 设为 `1` 时，视频先转存云存储再返回（更稳，但有存储/流量费） | `1` |
| `THIRDPARTY_API` | 第三方去水印聚合接口地址，内置解析失败时兜底 | `https://api.xxx.com/parse?key=KEY&url=` |

> 配置 `THIRDPARTY_API` 后，若内置解析失败会自动调用它。不同服务返回结构不同，按需在 `cloudfunctions/parse/lib/thirdparty.js` 的 `mapResult` 里适配字段。

**stats 云函数**还需配置管理员白名单（数据看板鉴权）：

| 变量 | 作用 | 示例 |
| --- | --- | --- |
| `ADMIN_OPENIDS` | 可查看数据看板的 openid，逗号分隔 | `oABC123...,oDEF456...` |

> 怎么拿自己的 openid：先**不配**该变量，在小程序「我的」页连点版本号 5 次进入数据看板，页面会显示你的 openid，复制后填进 `ADMIN_OPENIDS` 再重试即可。

### 平台说明

- **抖音 / 皮皮虾**（字节系）：内置 H5 解析，最稳定。
- **快手 / 小红书 / 微博**：基于分享页 og 标签与内联直链的 best-effort，平台改版可能失效。
- **B站**：走官方 view/playurl(html5) 取免登录 360p mp4；B站 CDN 有 **Referer 防盗链**，直链通常无法直接预览/保存，**需开启 `PROXY_TO_STORAGE=1`**（云函数已带 Referer 转存，详见第 6 节）。
- 任何平台失效时，配置 `THIRDPARTY_API` 即可兜底。

## 4. 创建数据库集合

「云开发控制台 → 数据库 → 新建集合」：

| 集合 | 用途 | 权限 |
| --- | --- | --- |
| `users` | 用户（openid + 首次/最近访问时间） | 仅创建者可读写 |
| `parse_logs` | 解析量统计（用于数据看板） | 仅创建者可读写 |
| `histories` | 解析记录云端同步（按 openid 存档） | 仅创建者可读写 |

> 不创建也不会报错（云函数里已 try/catch），但建上能积累统计数据。

## 5. 配置广告位（变现）

见 [MONETIZE.md](MONETIZE.md)。拿到广告位 ID 后填入 `miniprogram/config.js`：

```js
rewardedAdUnitId: 'adunit-你的激励视频ID',
bannerAdUnitId:   'adunit-你的Banner ID',
interstitialAdUnitId: 'adunit-你的插屏ID', // 不需要可留空
```

## 6. 让「保存」可靠工作（下载域名 · 重要）

`wx.downloadFile` 只允许请求**已配置的 HTTPS 合法域名**，**不支持通配符**、不支持端口。而抖音等短视频 CDN 的主机名会**轮换**，几乎无法靠白名单覆盖全。所以保存功能有两条路：

**方案 A（推荐，最稳）：转存云存储**

- 在 parse 云函数环境变量里设 `PROXY_TO_STORAGE=1`。
- 云函数把无水印视频/图片下载后转存云存储，返回 `fileID`；客户端用 `wx.cloud.downloadFile` 保存，云存储域名 `*.tcb.qcloud.la` **自动在白名单内**。
- 代价：产生云存储与下行流量费用（视频较大，留意成本，可结合限免/看广告策略平衡）。

**方案 B（省钱，但脆）：把 CDN 域名加进 downloadFile 白名单**

- mp.weixin.qq.com → 开发 → 开发管理 → 开发设置 → 服务器域名 → `downloadFile 合法域名`，逐个填**精确**域名（无通配符）。
- 抖音相关域名举例（会变，需自行抓包补充）：`https://aweme.snssdk.com`、`https://www.iesdouyin.com`，图片走 `douyinpic.com` 系列、视频走 `douyinvod.com` 系列的**具体主机名**。
- 因 CDN 主机名轮换，此法常有部分链接保存失败，适合作补充，不能完全替代方案 A。

> 预览不受影响：`<video>` / `<image>` 组件加载 src **不走** downloadFile 白名单，所以没配域名也能预览，卡的是"保存"。
>
> 实战建议：视频用方案 A（`PROXY_TO_STORAGE=1`）；或接一个返回**稳定域名**的第三方接口，再用方案 B 白名单那几个稳定域名。

## 7. 联调测试

1. 真机预览（扫码），粘贴一条**真实的抖音分享文案**。
2. 点「立即去水印」→ 进结果页能看到视频预览。
3. 点「保存」→ 弹激励视频（开发者工具里广告可能是模拟态）→ 看完保存到相册。

> 开发者工具里广告组件常显示「mock」或报错属正常，**以真机为准**。`utils/ad.js` 在不支持广告的环境会直接放行，保证联调不被卡住。

## 8. 上传与提审

1. 工具点「上传」，填版本号与项目备注。
2. 登录 [mp.weixin.qq.com](https://mp.weixin.qq.com) → 版本管理 → 提交审核。
3. **提审前务必读 [REVIEW.md](REVIEW.md)**：选对类目、写好审核备注，能显著提高过审率。

## 故障排查

| 现象 | 排查 |
| --- | --- |
| 调用云函数报 `-501000` / env 错误 | `config.js` 的 `cloudEnv` 是否填对、云函数是否已部署 |
| 解析总是失败 | 平台结构可能升级；配置 `THIRDPARTY_API` 兜底；看云函数日志 |
| 能预览但保存失败 | downloadFile 域名限制；按第 6 节开启 `PROXY_TO_STORAGE=1` 或配置下载域名 |
| 保存提示无权限 | 用户拒过相册授权；`save.js` 会引导去设置页开启 |
| 广告不出 | 流量主未开通 / 广告位 ID 错 / 未满 1000 UV；真机调试 |
