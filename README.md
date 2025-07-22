# AstrBot 抽奖插件

![](https://count.getloli.com/@lottery?name=lottery&theme=booru-jaypee&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

一个功能强大的 AstrBot 抽奖插件，支持多种抽奖算法和灵活的配置选项。

> [!NOTE]
> 
> 仅支持 aiocqhttp 协议下使用。

## ✨功能特性

- 🎲 灵活的自定义配置创建选项
- 🎯 支持多种抽奖算法
- 📉 完整的统计管理信息

## 📦使用方法

### 安装

1. 在 AstrBot 插件市场中直接获取安装
2. 将该仓库放置在 AstrBot 的插件目录下

### 基本命令

| 命令 | 参数 | 描述 |
| ---- | ---- | ---- |
| `/抽奖(lottery) 创建(create)` | - | 创建新的抽奖(需要op权限) |
| `/抽奖(lottery) 列表(list)` | - | 列出所有抽奖 |
| `/抽奖(lottery) 参与(participate)` | `[抽奖名称]` | 参与指定的抽奖 |

### 创建抽奖

在使用指令创建抽奖后，机器人会发送一个模板消息，用户按照模板消息填写后再发送给机器人才可以成功创建抽奖。

![](docs/create_template.png)

完整的模板消息格式如下：

```json
{
  "name": "",
  "description": "",
  "start_time": "2025-01-01T00:00:00Z",
  "end_time": "2025-12-31T23:59:59Z",
  "allowed_groups": [],
  "participation_limits": {
    "max_total_participants": 1000,
    "max_attempts_per_user": 3,
    "max_wins_per_user": 1
  },
  "probability_settings": {
    "probability_mode": "exhaust",
    "base_probability": 0.2
  },
  "prizes": [
    {
      "name": "",
      "description": "",
      "image_url": "",
      "weight": 1,
      "quantity": 2,
      "max_win_per_user": 1
    }
  ]
}
```

各项字段说明：
- `name`: 抽奖名称
- `description`: 抽奖描述
- `start_time`: 抽奖开始时间，ISO 8601 格式
- `end_time`: 抽奖结束时间，ISO 8601 格式
- `allowed_groups`: 允许参与的群组列表，每一项为string类型的群号
- `participation_limits`: 参与限制设置
  - `max_total_participants`: 最大参与人数
  - `max_attempts_per_user`: 每个用户最大参与次数
  - `max_wins_per_user`: 每个用户最大中奖次数
- `probability_settings`: 概率设置
  - `probability_mode`: 概率模式，支持 "exhaust"（用尽量抽完）和 "fixed"（固定概率）
  - `base_probability`: 基础中奖概率，0-1之间的浮点数
- `prizes`: 奖品列表
  - `name`: 奖品名称
  - `description`: 奖品描述
  - `image_url`: 奖品图片链接
  - `weight`: 奖品权重，整数，权重越高中奖概率越大
  - `quantity`: 奖品数量，整数
  - `max_win_per_user`: 每个用户最大中奖次数

有关于抽奖算法的更多信息，请参考 [抽奖算法文档](docs/ALGORITHMS.md)。

### 消息广播

当有任一玩家抽中奖品后，机器人会自动发送中奖通知消息到所有参与抽奖的群组。

## 🧾更新日志

参见 [CHANGELOG](docs/CHANGELOG.md)。