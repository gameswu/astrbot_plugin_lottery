# 抽奖系统使用说明

## 概述

这是一个功能完整的抽奖系统，支持创建抽奖活动、用户参与抽奖、查询抽奖信息等功能。

## 主要功能

### 1. 根据JSON字符串创建抽奖

```python
from lottery import Lottery, LotteryParseError

# JSON配置示例
lottery_config = '''
{
  "name": "春节抽奖活动",
  "description": "春节期间的特殊抽奖活动",
  "start_time": "2025-01-01T00:00:00Z",
  "end_time": "2025-12-31T23:59:59Z",
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
      "name": "一等奖",
      "description": "价值500元的礼品",
      "image_url": "https://example.com/prize1.jpg",
      "weight": 1,
      "quantity": 2,
      "max_win_per_user": 1
    },
    {
      "name": "二等奖",
      "description": "价值100元的礼品",
      "image_url": "https://example.com/prize2.jpg",
      "weight": 5,
      "quantity": 10,
      "max_win_per_user": 1
    }
  ]
}
'''

try:
    lottery = Lottery.parse_and_create(lottery_config, creator="admin_user")
    print(f"抽奖创建成功！ID: {lottery.id}")
except LotteryParseError as e:
    print(f"创建失败: {e}")
```

### 2. 用户参与抽奖

```python
from lottery import LotteryOperationError

try:
    # 用户参与抽奖
    won, prize, message = lottery.participate("user_123")
    
    if won:
        print(f"中奖了！奖品：{prize.name}")
        print(f"描述：{prize.description}")
    else:
        print("很遗憾，没有中奖")
        
except LotteryOperationError as e:
    print(f"参与失败: {e}")
```

### 3. 查询抽奖信息

```python
# 获取抽奖详细信息
info = lottery.get_info()
print(f"抽奖名称: {info['name']}")
print(f"状态: {info['status']}")
print(f"参与人数: {info['total_participants']}")

# 获取奖品信息
for prize in info['prizes']:
    print(f"奖品: {prize['name']}")
    print(f"剩余数量: {prize['remaining_quantity']}/{prize['total_quantity']}")
```

### 4. 查找和管理抽奖

```python
# 根据名称查找抽奖
lottery = Lottery.get_lottery_by_name("春节抽奖活动")

# 根据ID查找抽奖
lottery = Lottery.get_lottery_by_id("lottery_id")

# 获取所有抽奖
all_lotteries = Lottery.get_all_lotteries()

# 获取指定状态的抽奖
from lottery import LotteryStatus
active_lotteries = Lottery.get_all_lotteries(LotteryStatus.ACTIVE)

# 获取指定创建者的抽奖
user_lotteries = Lottery.get_all_lotteries(creator_filter="admin_user")

# 同时使用多个过滤器
user_active_lotteries = Lottery.get_all_lotteries(
    status_filter=LotteryStatus.ACTIVE, 
    creator_filter="admin_user"
)
```

## 配置参数说明

### 基本信息
- `name`: 抽奖活动名称
- `description`: 活动描述
- `start_time`: 活动开始时间（ISO 8601格式）
- `end_time`: 活动结束时间

### 参与限制
- `max_total_participants`: 最多参与总人数（0=无限制）
- `max_attempts_per_user`: 每个用户最大抽奖次数
- `max_wins_per_user`: 每个用户最大中奖次数（0=无限制）

### 概率设置
- `probability_mode`: 概率模式，可选值：
  - `"fixed"`: 固定概率模式
  - `"dynamic"`: 动态概率模式
  - `"exhaust"`: 消耗模式（动态调整概率以尽量发完所有奖品）
- `base_probability`: 基础中奖概率（0-1之间）

### 奖品配置
- `name`: 奖品名称
- `description`: 奖品描述
- `image_url`: 奖品图片链接（可选）
- `weight`: 相对权重（影响中奖概率）
- `quantity`: 奖品总数量（-1=无限量）
- `max_win_per_user`: 单个用户最多可获得数量

## 错误处理

### 解析错误
- `LotteryParseError`: JSON解析失败、缺少必需字段、格式错误等

### 操作错误
- `LotteryOperationError`: 抽奖状态不正确、达到参与限制等

## 抽奖状态

- `PENDING`: 未开始
- `ACTIVE`: 进行中
- `ENDED`: 已结束
- `CANCELLED`: 已取消

## 概率计算

### 固定概率模式 (fixed)
使用配置的`base_probability`作为固定中奖概率。

### 动态概率模式 (dynamic)
使用配置的`base_probability`作为基础概率（当前版本与固定模式相同，可扩展）。

### 消耗模式 (exhaust)
根据剩余奖品数量和剩余中奖次数动态调整概率，确保尽量发完所有有限量奖品。

## 线程安全

系统使用`threading.RLock()`确保多线程环境下的数据一致性。

## 存储说明

当前实现使用内存存储，实际部署时可以替换为数据库存储：

```python
# 替换类级别的存储
class Lottery:
    # 将这些替换为数据库操作
    _lotteries: Dict[str, 'Lottery'] = {}
    _lock = threading.RLock()
```

## 测试

运行测试脚本验证功能：

```bash
python3 test_lottery.py
```

测试包含：
- 抽奖创建
- 用户参与
- 信息查询
- 错误处理
- 边界条件测试
