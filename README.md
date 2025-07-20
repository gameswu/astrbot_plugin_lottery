# AstrBot 抽奖插件

一个功能强大的 AstrBot 抽奖插件，支持多种抽奖算法和灵活的配置选项。

## 功能特点

- 🎯 **多种抽奖算法**: 支持随机抽奖和加权抽奖
- 🔧 **装饰器模式**: 使用装饰器轻松为抽奖类添加算法支持
- 📊 **灵活配置**: 
  - 设置奖品数量限制（可以为不限）
  - 设置用户抽奖次数限制（可以为不限）
  - 控制是否允许重复中奖
- 📈 **统计功能**: 实时统计抽奖情况和中奖记录
- 🎮 **易于扩展**: 可以轻松添加新的抽奖算法

## 核心组件

### 1. LotteryConfig (抽奖配置)
```python
from algorithm_lot import LotteryConfig

config = LotteryConfig(
    prize_limit=10,        # 每个奖品最多被抽取10次，None表示不限
    user_draw_limit=5,     # 每个用户最多抽奖5次，None表示不限
    allow_duplicate=True   # 是否允许用户重复中奖同一个奖品
)
```

### 2. 抽奖算法装饰器
```python
from algorithm_lot import lottery_algorithm, LotteryConfig

@lottery_algorithm("random", LotteryConfig(user_draw_limit=3))
class MyLottery(Lottery):
    pass
```

### 3. 支持的算法类型
- `"random"`: 随机抽奖算法
- `"weighted"`: 加权抽奖算法（可设置不同奖品的中奖概率）

## 使用示例

### 基本使用
```python
from lottery import AdvancedLottery

# 创建抽奖活动
lottery = AdvancedLottery(
    creater_id="admin_001",
    id="新年抽奖",
    description="2025新年抽奖活动",
    prize_num=3
)

# 设置奖品
lottery.set_prize(1, "一等奖：iPhone 15", "最新款苹果手机", "iphone15.jpg")
lottery.set_prize(2, "二等奖：AirPods Pro", "苹果无线耳机", "airpods.jpg")
lottery.set_prize(3, "三等奖：Apple Watch", "苹果智能手表", "watch.jpg")

# 用户抽奖
result = lottery.draw_prize("user_001")
print(result.message)
if result.success:
    print(f"中奖奖品: {result.prize_name}")
```

### 自定义限制
```python
from algorithm_lot import lottery_algorithm, LotteryConfig
from lottery import Lottery

@lottery_algorithm("random", LotteryConfig(
    prize_limit=1,          # 每个奖品只能被抽取1次
    user_draw_limit=2,      # 每个用户最多抽奖2次
    allow_duplicate=False   # 不允许重复中奖
))
class LimitedLottery(Lottery):
    pass

lottery = LimitedLottery("admin", "限量抽奖", "稀有奖品", 2)
```

### 加权抽奖
```python
from lottery import WeightedLottery

# 创建加权抽奖，不同奖品有不同中奖概率
lottery = WeightedLottery(
    creater_id="admin",
    id="加权抽奖",
    description="VIP专属抽奖",
    prize_num=3,
    weights={1: 0.1, 2: 0.3, 3: 0.6}  # 奖品权重
)
```

### 动态配置
```python
# 运行时修改配置
lottery.set_prize_limit(5)          # 修改奖品数量限制
lottery.set_user_draw_limit(3)      # 修改用户抽奖次数限制
lottery.set_allow_duplicate(False)  # 禁止重复中奖

# 重置抽奖状态
lottery.reset_lottery_state()

# 查看统计信息
stats = lottery.get_lottery_statistics()
print(stats)
```

## API 文档

### LotteryResult (抽奖结果)
```python
class LotteryResult:
    user_id: str                    # 用户ID
    prize_id: Optional[int]         # 中奖奖品ID，None表示未中奖
    prize_name: Optional[str]       # 奖品名称
    success: bool                   # 是否中奖
    message: str                    # 结果消息
```

### 装饰器添加的方法
使用 `@lottery_algorithm` 装饰器后，抽奖类会自动获得以下方法：

- `draw_prize(user_id: str) -> LotteryResult`: 执行抽奖
- `set_prize_limit(limit: Optional[int])`: 设置奖品数量限制
- `set_user_draw_limit(limit: Optional[int])`: 设置用户抽奖次数限制
- `set_allow_duplicate(allow: bool)`: 设置是否允许重复中奖
- `reset_lottery_state()`: 重置抽奖状态
- `get_lottery_statistics()`: 获取统计信息

## 扩展开发

### 创建自定义算法
```python
from algorithm_lot import LotteryAlgorithm, register_algorithm

@register_algorithm("custom")
class CustomLotteryAlgorithm(LotteryAlgorithm):
    def draw(self, user_id: str, available_prizes: List[Dict]) -> LotteryResult:
        # 实现自定义抽奖逻辑
        pass
```

### 使用自定义算法
```python
@lottery_algorithm("custom", config)
class CustomLottery(Lottery):
    pass
```

## 运行示例

```bash
cd /path/to/plugin
python example_usage.py
```

这将运行所有示例，展示各种功能的使用方法。

## 支持

[AstrBot 帮助文档](https://astrbot.app)
