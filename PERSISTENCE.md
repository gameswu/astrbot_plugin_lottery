# 抽奖系统持久化使用指南

## 概述

抽奖系统现在支持基于JSON文件的持久化，所有数据会自动保存到磁盘，插件重启后能自动恢复数据。

## 数据存储结构

```
data/
├── lotteries.json        # 主抽奖数据文件
└── participants/         # 参与者数据目录
    ├── {lottery_id}.json # 每个抽奖的参与者数据
    └── ...
```

## 快速开始

### 1. 基本初始化

```python
from lottery import Lottery
from persistence import get_persistence_manager

# 初始化持久化（通常在插件启动时调用一次）
persistence_manager = get_persistence_manager("data")  # data是存储目录
Lottery.set_persistence_manager(persistence_manager)
Lottery.enable_auto_save(True)  # 启用自动保存
Lottery.load_all_from_disk()    # 加载现有数据
```

### 2. 使用简化的初始化

```python
from lottery import Lottery
from persistence import get_persistence_manager

# 初始化（自动处理持久化）
persistence_manager = get_persistence_manager("data")
Lottery.set_persistence_manager(persistence_manager)
Lottery.enable_auto_save(True)
Lottery.load_all_from_disk()

# 正常使用，数据自动保存
lottery = Lottery.parse_and_create(json_config)
won, prize, msg = lottery.participate("user_001")
```

## 自动保存时机

以下操作会自动触发保存到磁盘：

1. **创建抽奖** - `Lottery.parse_and_create()`
2. **用户参与** - `lottery.participate()`  
3. **删除抽奖** - `Lottery.delete_lottery()`

## 数据加载

### 插件启动时加载

```python
# 在插件初始化时调用
Lottery.load_all_from_disk()

# 检查加载结果
lotteries = Lottery.get_all_lotteries()
print(f"已加载 {len(lotteries)} 个抽奖")
```

### 手动加载单个抽奖

```python
from persistence import get_persistence_manager

persistence_manager = get_persistence_manager()
lottery = persistence_manager.load_lottery("lottery_id")
```

## 配置选项

### 自定义数据目录

```python
# 使用自定义目录
persistence_manager = get_persistence_manager("/path/to/custom/data")
Lottery.set_persistence_manager(persistence_manager)
```

### 禁用自动保存

```python
# 禁用自动保存（需要手动调用保存）
Lottery.enable_auto_save(False)

# 手动保存
lottery = Lottery.get_lottery_by_id("some_id")
persistence_manager.save_lottery(lottery)
```

## 文件格式

### lotteries.json 结构

```json
{
  "lottery_id": {
    "data": {
      "name": "抽奖名称",
      "description": "抽奖描述", 
      "start_time": "2025-01-01T00:00:00Z",
      "end_time": "2025-02-01T23:59:59Z",
      "participation_limits": {...},
      "probability_settings": {...},
      "prizes": [...]
    },
    "total_participants": 10,
    "total_attempts": 25,
    "created_at": "2025-01-01T12:00:00+00:00"
  }
}
```

### participants/{lottery_id}.json 结构

```json
{
  "user_001": {
    "user_id": "user_001",
    "attempts": 3,
    "wins": ["奖品名称1", "奖品名称2"]
  },
  "user_002": {
    "user_id": "user_002", 
    "attempts": 1,
    "wins": []
  }
}
```

## 错误处理

### 加载失败处理

```python
try:
    Lottery.load_all_from_disk()
    print("数据加载成功")
except Exception as e:
    print(f"数据加载失败：{e}")
    # 可以选择从备份恢复或重新初始化
```

### 保存失败处理

```python
# 自动保存失败会在控制台打印错误信息
# 也可以手动检查保存结果
success = persistence_manager.save_lottery(lottery)
if not success:
    print("保存失败，请检查磁盘空间和权限")
```

## 性能优化建议

### 1. 合理设置数据目录

```python
# 将数据目录设置在快速存储设备上
# 避免网络存储或慢速磁盘
persistence_manager = get_persistence_manager("/fast/ssd/path/data")
```

### 2. 大量数据时考虑禁用自动保存

```python
# 批量操作时暂时禁用自动保存
Lottery.enable_auto_save(False)

# 执行大量操作
for i in range(1000):
    lottery.participate(f"user_{i}")

# 最后手动保存一次
persistence_manager.save_lottery(lottery)
Lottery.enable_auto_save(True)
```

### 3. 定期清理过期数据

```python
from lottery import LotteryStatus

# 获取已结束的抽奖
ended_lotteries = Lottery.get_all_lotteries(LotteryStatus.ENDED)

# 清理超过一定时间的抽奖
from datetime import datetime, timedelta
cutoff_date = datetime.now() - timedelta(days=30)

for lottery in ended_lotteries:
    if lottery.created_at < cutoff_date:
        Lottery.delete_lottery(lottery.id)
        print(f"已清理过期抽奖：{lottery.data.name}")
```

## 备份和恢复

### 备份数据

```bash
# 简单的文件复制备份
cp -r data/ backup_$(date +%Y%m%d_%H%M%S)/
```

### 恢复数据

```bash
# 恢复备份数据
cp -r backup_20250101_120000/ data/
```

```python
# 重新加载数据
Lottery._lotteries.clear()  # 清空内存
Lottery.load_all_from_disk()  # 重新加载
```

## 注意事项

1. **线程安全**：持久化操作已经考虑了线程安全，可以在多线程环境下使用
2. **文件权限**：确保程序对数据目录有读写权限
3. **磁盘空间**：大量抽奖和参与者数据可能占用较多空间，需要定期清理
4. **编码格式**：所有JSON文件使用UTF-8编码，支持中文等特殊字符
5. **重复初始化**：重复调用初始化方法是安全的，会使用单例模式

## 示例：完整的插件集成

```python
# main.py - 插件主入口
from lottery import Lottery
from persistence import get_persistence_manager

class AstrBotLotteryPlugin:
    def __init__(self):
        # 初始化抽奖系统持久化
        persistence_manager = get_persistence_manager("data")
        Lottery.set_persistence_manager(persistence_manager)
        Lottery.enable_auto_save(True)
        Lottery.load_all_from_disk()
        print("抽奖插件已启动")
    
    def handle_create_lottery(self, json_config):
        """处理创建抽奖命令"""
        try:
            lottery = Lottery.parse_and_create(json_config)
            return f"抽奖已创建：{lottery.data.name}"
        except Exception as e:
            return f"创建失败：{e}"
    
    def handle_participate(self, lottery_id, user_id):
        """处理参与抽奖命令"""
        lottery = Lottery.get_lottery_by_id(lottery_id)
        if not lottery:
            return "抽奖不存在"
        
        try:
            won, prize, message = lottery.participate(user_id)
            return message
        except Exception as e:
            return f"参与失败：{e}"
    
    def handle_list_lotteries(self):
        """处理查看抽奖列表命令"""
        lotteries = Lottery.get_all_lotteries()
        return f"当前有 {len(lotteries)} 个抽奖"

# 创建插件实例
plugin = AstrBotLotteryPlugin()
```

这样，你的抽奖系统就有了完整的JSON持久化功能，数据会自动保存和加载，插件重启也不会丢失数据！
