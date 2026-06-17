# 猫约时光 · 微信支付（会员开通）说明

会员开通接入**云开发支付能力**（`cloud.cloudPay.unifiedOrder`）。设计为**优雅降级**：未配置商户号时自动回退为原型阶段的「模拟开通」，开发者工具与无商户环境照常可用。会员是**按用户(个人)**的，不是情侣共享。

## 涉及文件

| 文件 | 作用 |
|------|------|
| `cloudfunctions/pay/index.js` | 云函数：`unifiedOrder` 统一下单、`query` 查会员态；`payCallback` 支付结果回调 |
| `cloudfunctions/pay/package.json` | 云函数依赖（`wx-server-sdk` ~2.6.3） |
| `utils/pay.js` | 客户端封装：`configured()` / `buy(planKey)` / `fetchMembership()` |
| `pages/membership/membership.js` | 会员页：已配置则真实付款，未配置则模拟开通 |

## 支付流程

```
会员页点击套餐 → pay.configured()?
  ├─ 是：pay.buy(planKey)
  │        → 调 pay 云函数 unifiedOrder（按金额下单，返回 payment 参数）
  │        → wx.requestPayment 拉起收银台
  │        → 付款成功：微信回调 payCallback（云端写 users 会员态）+ 客户端 store.openMember 落地本地态
  └─ 否：保持原型「模拟开通」（弹窗确认后 store.openMember）
```

- 云端权威会员态写入集合 `users`：`{ _id: openid, member:{ isMember, tier, since, orderNo }, updatedAt }`。
- 客户端本地态仍由 `store.openMember(planKey)` 落地，供页面同步读取（与原型一致）。
- 金额（分）：`monthly=1800` / `yearly=13800` / `forever=29800`。`outTradeNo` 唯一。

## 云函数 actions

| action | 入参 | 返回 |
|--------|------|------|
| `unifiedOrder` | `planKey`（monthly/yearly/forever） | `{ ok:true, payment, orderNo, tier }`；未配置 `{ ok:false, error:'PAY_NOT_CONFIGURED' }` |
| `query` | — | `{ ok:true, member }`（调用者 OPENID 的会员态） |

另导出 `payCallback`：支付成功后由微信支付调用，校验 `resultCode==='SUCCESS'` 后发放会员，返回 `{ errcode:0 }`。

## 开发者上线前必须配置的项

1. **开通微信支付商户号**：`mp.weixin.qq.com` →「微信支付」开通并完成签约。
2. **云开发后台绑定商户号**：云开发控制台「设置 → 其他设置」绑定该商户号（让云函数可代调统一下单）。
3. **填 `cloudfunctions/pay/index.js` 顶部 `PAY_CONFIG`**：
   - `SUB_MCH_ID`：子商户号（**留空即视为未配置**，走降级）。
   - `ENV_ID`：云开发环境 ID（留空用当前环境）。
   - `CALLBACK_FUNCTION`：支付回调函数名，默认 `pay_payCallback`（即 `函数名_payCallback`）。
4. **打开客户端开关**：把 `utils/pay.js` 顶部 `PAY_ENABLED` 改为 `true`。

> 任一必要项缺失（`SUB_MCH_ID` 为空 或 `PAY_ENABLED=false`），都会自动走模拟开通，不报错。

## 部署步骤

1. 开发者工具开通**云开发**并创建环境（与 `app.js` 顶部 `CLOUD_ENV` 一致；留空用默认环境）。
2. 云开发控制台 →「数据库」→ 新建集合 **`users`**（权限可设"仅管理端可读写"，仅经云函数访问）。
3. 右键 `cloudfunctions/pay` →「上传并部署：云端安装依赖」。
4. 云开发后台绑定微信支付商户号（见上）。
5. 填好 `PAY_CONFIG` 与 `PAY_ENABLED=true`，重新上传部署 `pay` 云函数。

## 未配置时的降级行为

- `pay.configured()` 返回 `false`（`PAY_ENABLED` 默认 false）→ 会员页走**模拟开通**：弹窗确认后 `store.openMember`，与原型完全一致，不真实扣款。
- 即使误开 `PAY_ENABLED`，只要云函数 `SUB_MCH_ID` 为空，`unifiedOrder` 返回 `PAY_NOT_CONFIGURED`，客户端识别后**回退到模拟开通**，不报错。
- 开发者工具未登录云环境时同样安全降级（`cloudReady()` 为 false）。
