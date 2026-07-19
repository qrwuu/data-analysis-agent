# 电商指标口径

## 订单

- 支付GMV = 有效支付订单的 `payment_amount` 求和。
- 支付订单数 = 有效支付订单中的 `order_id` 去重计数。
- 支付买家数 = 有效支付订单中的 `buyer_id` 去重计数。
- 销售件数 = 有效支付订单 `quantity` 求和。
- 客单价 = 支付GMV / 支付订单数。
- 退款金额 = 有效支付订单 `refund_amount` 求和。
- 净销售额 = 支付GMV - 退款金额。
- 金额退款率 = 退款金额 / 支付GMV。

有效订单状态：`paid`、`completed`、`shipped`、`已支付`、`已发货`、`已完成`、`交易成功`。取消、关闭订单默认不计入支付GMV。

## 流量

- 点击率CTR = `clicks / impressions`。
- 加购率 = `add_to_cart_users / visitors`。
- 支付转化率 = `payment_buyers / visitors`。

## 推广

- 广告点击率 = `clicks / impressions`。
- 平均点击成本CPC = `ad_spend / clicks`。
- 广告转化率 = `ad_orders / clicks`。
- 广告投产比ROAS = `ad_revenue / ad_spend`。
- 广告净回报率 = `(ad_revenue - ad_spend) / ad_spend`。

所有除法在分母为 0 时返回“无法计算”，不让模型猜测。

