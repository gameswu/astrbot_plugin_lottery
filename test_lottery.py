#!/usr/bin/env python3
"""
抽奖系统综合测试脚本
用于测试抽奖系统的各种功能，包括：
1. 基础功能测试：创建抽奖、参与抽奖、信息查询、列表功能
2. 概率模式测试：固定概率、动态概率、消耗模式
3. 动态概率计算测试：简化后的动态概率计算逻辑验证
4. 错误处理测试：JSON格式错误、字段缺失、时间格式错误等
"""

import json
import sys
import os

# 添加当前目录到path，以便导入lottery模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery import Lottery, LotteryParseError, LotteryOperationError, LotteryStatus


def test_lottery_creation():
    """测试抽奖创建功能"""
    print("=" * 50)
    print("测试抽奖创建功能")
    print("=" * 50)
    
    # 测试用的JSON配置
    lottery_config = {
        "name": "春节抽奖活动",
        "description": "春节期间的特殊抽奖活动",
        "start_time": "2025-01-01T00:00:00Z",
        "end_time": "2025-12-31T23:59:59Z",
        "participation_limits": {
            "max_total_participants": 30,
            "max_attempts_per_user": 3,
            "max_wins_per_user": 1
        },
        "probability_settings": {
            "probability_mode": "exhaust",
            "base_probability": 0.0
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
                "quantity": 5,
                "max_win_per_user": 1
            },
            {
                "name": "三等奖",
                "description": "价值10元的礼品",
                "image_url": "",
                "weight": 20,
                "quantity": 10,
                "max_win_per_user": 1
            }
        ]
    }
    
    try:
        # 测试正常创建
        json_str = json.dumps(lottery_config, ensure_ascii=False, indent=2)
        print("创建抽奖配置：")
        print(json_str)
        print()
        
        lottery = Lottery.parse_and_create(json_str)
        print(f"✅ 抽奖创建成功！")
        print(f"   ID: {lottery.id}")
        print(f"   名称: {lottery.data.name}")
        print(f"   状态: {lottery.get_status().value}")
        print()
        
        return lottery
        
    except LotteryParseError as e:
        print(f"❌ 抽奖创建失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return None


def test_lottery_participation(lottery):
    """测试抽奖参与功能"""
    print("=" * 50)
    print("测试抽奖参与功能")
    print("=" * 50)
    
    if not lottery:
        print("❌ 没有可用的抽奖进行测试")
        return
    
    # 模拟多个用户参与抽奖
    test_users = [f"user_{i}" for i in range(1, lottery.data.participation_limits.max_total_participants + 1)]
    
    print(f"模拟 {len(test_users)} 个用户参与抽奖...")
    print()
    
    results = []
    for user_id in test_users:
        try:
            # 每个用户尝试多次抽奖
            user_results = []
            max_attempts = lottery.data.participation_limits.max_attempts_per_user
            
            for attempt in range(max_attempts):
                try:
                    won, prize, message = lottery.participate(user_id)
                    user_results.append({
                        'attempt': attempt + 1,
                        'won': won,
                        'prize': prize.name if prize else None,
                        'message': message
                    })
                    
                    if won:
                        print(f"🎉 {user_id} 第{attempt + 1}次抽奖中奖: {prize.name}")
                        break  # 中奖后停止继续抽奖
                    else:
                        print(f"😔 {user_id} 第{attempt + 1}次抽奖未中奖")
                        
                except LotteryOperationError as e:
                    print(f"⚠️  {user_id} 第{attempt + 1}次抽奖失败: {e}")
                    break
                    
            results.append({
                'user_id': user_id,
                'attempts': user_results
            })
            
        except Exception as e:
            print(f"❌ {user_id} 参与抽奖时发生错误: {e}")
    
    print()
    print("抽奖参与测试完成！")
    return results


def test_lottery_info(lottery):
    """测试抽奖信息查询功能"""
    print("=" * 50)
    print("测试抽奖信息查询功能")
    print("=" * 50)
    
    if not lottery:
        print("❌ 没有可用的抽奖进行测试")
        return
    
    try:
        info = lottery.get_info()
        
        print("抽奖详细信息：")
        print(f"ID: {info['id']}")
        print(f"名称: {info['name']}")
        print(f"描述: {info['description']}")
        print(f"状态: {info['status']}")
        print(f"参与人数: {info['total_participants']}")
        print(f"抽奖次数: {info['total_attempts']}")
        print()
        
        print("奖品信息：")
        for prize in info['prizes']:
            print(f"• {prize['name']}")
            print(f"  描述: {prize['description']}")
            if prize['total_quantity'] > 0:
                print(f"  库存: {prize['remaining_quantity']}/{prize['total_quantity']}")
            else:
                print(f"  库存: 无限制")
            print(f"  已发放: {prize['distributed']}")
            print(f"  权重: {prize['weight']}")
            print()
            
    except Exception as e:
        print(f"❌ 查询抽奖信息失败: {e}")


def test_lottery_list():
    """测试抽奖列表功能"""
    print("=" * 50)
    print("测试抽奖列表功能")
    print("=" * 50)
    
    try:
        all_lotteries = Lottery.get_all_lotteries()
        print(f"总共有 {len(all_lotteries)} 个抽奖活动：")
        print()
        
        for lottery in all_lotteries:
            status = lottery.get_status()
            print(f"🎲 {lottery.data.name}")
            print(f"   ID: {lottery.id}")
            print(f"   状态: {status.value}")
            print(f"   参与人数: {lottery.total_participants}")
            print(f"   抽奖次数: {lottery.total_attempts}")
            print()
            
        # 测试按状态筛选
        active_lotteries = Lottery.get_all_lotteries(LotteryStatus.ACTIVE)
        print(f"进行中的抽奖活动: {len(active_lotteries)} 个")
        
    except Exception as e:
        print(f"❌ 获取抽奖列表失败: {e}")


def create_test_lottery(probability_mode: str, base_probability: float = 0.3):
    """创建测试抽奖"""
    lottery_config = {
        "name": f"测试抽奖-{probability_mode}模式",
        "description": f"测试{probability_mode}概率模式",
        "start_time": "2025-01-01T00:00:00Z",
        "end_time": "2025-12-31T23:59:59Z",
        "participation_limits": {
            "max_total_participants": 10,
            "max_attempts_per_user": 3,
            "max_wins_per_user": 1
        },
        "probability_settings": {
            "probability_mode": probability_mode,
            "base_probability": base_probability
        },
        "prizes": [
            {
                "name": "一等奖",
                "description": "价值100元的礼品",
                "image_url": "",
                "weight": 1,
                "quantity": 2,
                "max_win_per_user": 1
            },
            {
                "name": "二等奖",
                "description": "价值50元的礼品",
                "image_url": "",
                "weight": 3,
                "quantity": 3,
                "max_win_per_user": 1
            }
        ]
    }
    
    json_str = json.dumps(lottery_config, ensure_ascii=False, indent=2)
    return Lottery.parse_and_create(json_str)


def test_fixed_mode():
    """测试固定概率模式"""
    print("=" * 50)
    print("测试固定概率模式")
    print("=" * 50)
    
    lottery = create_test_lottery("fixed", 0.5)
    print(f"创建抽奖: {lottery.data.name}")
    print(f"概率模式: {lottery.data.probability_settings.probability_mode}")
    print(f"基础概率: {lottery.data.probability_settings.base_probability}")
    print()
    
    # 模拟几次抽奖
    win_count = 0
    total_attempts = 0
    
    for i in range(1, 6):
        user_id = f"test_user_{i}"
        for attempt in range(3):
            try:
                won, prize, message = lottery.participate(user_id)
                total_attempts += 1
                if won:
                    win_count += 1
                    print(f"🎉 {user_id} 第{attempt + 1}次中奖: {prize.name}")
                    break
                else:
                    print(f"😔 {user_id} 第{attempt + 1}次未中奖")
            except LotteryOperationError as e:
                print(f"⚠️  {user_id} 抽奖失败: {e}")
                break
    
    actual_rate = win_count / total_attempts if total_attempts > 0 else 0
    print(f"\n实际中奖率: {actual_rate:.2%} (期望: 50%)")
    print()


def test_dynamic_mode():
    """测试动态概率模式"""
    print("=" * 50)
    print("测试动态概率模式")
    print("=" * 50)
    
    lottery = create_test_lottery("dynamic", 0.3)
    print(f"创建抽奖: {lottery.data.name}")
    print(f"概率模式: {lottery.data.probability_settings.probability_mode}")
    print(f"基础概率: {lottery.data.probability_settings.base_probability}")
    print()
    
    # 模拟几次抽奖
    win_count = 0
    total_attempts = 0
    
    for i in range(1, 6):
        user_id = f"test_user_{i}"
        for attempt in range(3):
            try:
                won, prize, message = lottery.participate(user_id)
                total_attempts += 1
                if won:
                    win_count += 1
                    print(f"🎉 {user_id} 第{attempt + 1}次中奖: {prize.name}")
                    break
                else:
                    print(f"😔 {user_id} 第{attempt + 1}次未中奖")
            except LotteryOperationError as e:
                print(f"⚠️  {user_id} 抽奖失败: {e}")
                break
    
    actual_rate = win_count / total_attempts if total_attempts > 0 else 0
    print(f"\n实际中奖率: {actual_rate:.2%} (期望: 30%)")
    print()


def test_exhaust_mode():
    """测试消耗模式"""
    print("=" * 50)
    print("测试消耗模式（动态调整概率以消耗完奖品）")
    print("=" * 50)
    
    lottery = create_test_lottery("exhaust", 0.3)
    print(f"创建抽奖: {lottery.data.name}")
    print(f"概率模式: {lottery.data.probability_settings.probability_mode}")
    print(f"基础概率: {lottery.data.probability_settings.base_probability}")
    print()
    
    # 模拟所有用户参与抽奖
    win_count = 0
    total_attempts = 0
    
    for i in range(1, 11):  # 10个用户
        user_id = f"test_user_{i}"
        for attempt in range(3):
            try:
                won, prize, message = lottery.participate(user_id)
                total_attempts += 1
                if won:
                    win_count += 1
                    print(f"🎉 {user_id} 第{attempt + 1}次中奖: {prize.name}")
                    break
                else:
                    print(f"😔 {user_id} 第{attempt + 1}次未中奖")
            except LotteryOperationError as e:
                print(f"⚠️  {user_id} 抽奖失败: {e}")
                break
    
    # 检查奖品消耗情况
    print("\n奖品消耗情况:")
    total_prizes = 0
    remaining_prizes = 0
    for prize in lottery.data.prizes:
        total_prizes += prize.quantity
        remaining_prizes += prize.remaining_quantity
        print(f"• {prize.name}: {prize.quantity - prize.remaining_quantity}/{prize.quantity} 已发放")
    
    print(f"\n总奖品: {total_prizes}, 剩余: {remaining_prizes}, 发放率: {(total_prizes - remaining_prizes) / total_prizes:.2%}")
    actual_rate = win_count / total_attempts if total_attempts > 0 else 0
    print(f"实际中奖率: {actual_rate:.2%}")
    print()


def test_invalid_mode():
    """测试无效的概率模式"""
    print("=" * 50)
    print("测试无效的概率模式")
    print("=" * 50)
    
    try:
        lottery = create_test_lottery("invalid_mode", 0.3)
        print("❌ 应该抛出错误")
    except LotteryParseError as e:
        print(f"✅ 正确捕获错误: {e}")
    
    print()


def test_simplified_dynamic_probability():
    """测试简化后的动态概率计算"""
    print("=" * 50)
    print("测试简化后的动态概率计算")
    print("=" * 50)
    
    # 创建一个测试抽奖配置
    config = {
        "name": "测试抽奖",
        "description": "测试动态概率计算",
        "start_time": "2025-01-01T00:00:00Z",
        "end_time": "2025-12-31T23:59:59Z",
        "participation_limits": {
            "max_total_participants": 10,
            "max_attempts_per_user": 3,
            "max_wins_per_user": 1
        },
        "probability_settings": {
            "probability_mode": "exhaust",
            "base_probability": 0.1
        },
        "prizes": [
            {
                "name": "一等奖",
                "description": "超级大奖",
                "image_url": "",
                "weight": 1,
                "quantity": 2,
                "max_win_per_user": 1
            },
            {
                "name": "二等奖", 
                "description": "不错的奖品",
                "image_url": "",
                "weight": 3,
                "quantity": 5,
                "max_win_per_user": 1
            }
        ]
    }
    
    lottery = Lottery.parse_and_create(json.dumps(config))
    
    print("=== 动态概率计算测试 ===")
    print(f"基础概率: {lottery.data.probability_settings.base_probability}")
    print(f"总奖品数: {sum(p.quantity for p in lottery.data.prizes)}")
    print(f"最大参与用户数: {lottery.data.participation_limits.max_total_participants}")
    print(f"每用户最大抽奖次数: {lottery.data.participation_limits.max_attempts_per_user}")
    print()
    
    # 测试不同阶段的概率变化
    scenarios = [
        ("初始状态", 0, 0),
        ("5个用户参与，0个中奖", 5, 0),  
        ("8个用户参与，2个中奖", 8, 2),
        ("10个用户参与，5个中奖", 10, 5),
    ]
    
    for scenario_name, participants, winners in scenarios:
        # 重置抽奖状态
        lottery.participants = {}
        lottery.total_participants = 0
        lottery.total_attempts = 0
        
        # 重置奖品数量
        for prize in lottery.data.prizes:
            prize.remaining_quantity = prize.quantity
        
        # 模拟参与状态
        from lottery import UserParticipation
        for i in range(participants):
            user_id = f"user_{i+1}"
            lottery.participants[user_id] = UserParticipation(
                user_id=user_id,
                attempts=2,  # 每人已抽2次
                wins=[]
            )
            lottery.total_participants += 1
            lottery.total_attempts += 2
        
        # 模拟中奖情况
        prizes_won = 0
        for i, user_participation in enumerate(lottery.participants.values()):
            if i < winners:
                user_participation.wins = ["一等奖"]
                prizes_won += 1
        
        # 更新剩余奖品数量
        for prize in lottery.data.prizes:
            if prize.name == "一等奖":
                prize.remaining_quantity = prize.quantity - min(prizes_won, prize.quantity)
        
        # 计算剩余信息
        total_remaining = sum(p.remaining_quantity for p in lottery.data.prizes)
        remaining_wins = lottery._calculate_remaining_wins()
        
        # 计算动态概率
        dynamic_prob = lottery._calculate_dynamic_probability()
        
        print(f"--- {scenario_name} ---")
        print(f"参与用户数: {participants}")
        print(f"中奖用户数: {winners}")
        print(f"剩余奖品数: {total_remaining}")
        print(f"剩余中奖机会: {remaining_wins}")
        if remaining_wins > 0:
            print(f"理论所需概率: {total_remaining / remaining_wins:.3f}")
        print(f"实际动态概率: {dynamic_prob:.3f}")
        print()


def test_error_handling():
    """测试错误处理功能"""
    print("=" * 50)
    print("测试错误处理功能")
    print("=" * 50)
    
    # 测试JSON格式错误
    print("1. 测试JSON格式错误...")
    try:
        Lottery.parse_and_create("invalid json")
        print("❌ 应该抛出JSON格式错误")
    except LotteryParseError as e:
        print(f"✅ 正确捕获JSON格式错误: {e}")
    
    # 测试缺少必需字段
    print("\n2. 测试缺少必需字段...")
    try:
        incomplete_config = {"name": "test"}
        Lottery.parse_and_create(json.dumps(incomplete_config))
        print("❌ 应该抛出缺少字段错误")
    except LotteryParseError as e:
        print(f"✅ 正确捕获缺少字段错误: {e}")
    
    # 测试时间格式错误
    print("\n3. 测试时间格式错误...")
    try:
        bad_time_config = {
            "name": "test",
            "description": "test",
            "start_time": "invalid_time",
            "end_time": "2025-12-31T23:59:59Z",
            "participation_limits": {
                "max_total_participants": 100,
                "max_attempts_per_user": 3,
                "max_wins_per_user": 1
            },
            "probability_settings": {
                "probability_mode": "fixed",
                "base_probability": 0.3
            },
            "prizes": [
                {
                    "name": "奖品",
                    "description": "测试奖品",
                    "image_url": "",
                    "weight": 1,
                    "quantity": 1,
                    "max_win_per_user": 1
                }
            ]
        }
        Lottery.parse_and_create(json.dumps(bad_time_config))
        print("❌ 应该抛出时间格式错误")
    except LotteryParseError as e:
        print(f"✅ 正确捕获时间格式错误: {e}")


def main():
    """主测试函数"""
    print("🎲 抽奖系统综合测试开始")
    print()
    
    # 基础功能测试
    print("📋 === 基础功能测试 === 📋")
    
    # 测试创建抽奖
    lottery = test_lottery_creation()
    
    # 测试参与抽奖
    if lottery:
        test_lottery_participation(lottery)
        
        # 测试信息查询
        test_lottery_info(lottery)
    
    # 测试列表功能
    test_lottery_list()
    
    # 概率模式测试
    print("\n🎯 === 概率模式测试 === 🎯")
    test_fixed_mode()
    test_dynamic_mode()
    test_exhaust_mode()
    test_invalid_mode()
    
    # 动态概率计算测试
    print("\n🧮 === 动态概率计算测试 === 🧮")
    test_simplified_dynamic_probability()
    
    # 错误处理测试
    print("\n🚨 === 错误处理测试 === 🚨")
    test_error_handling()
    
    print("=" * 50)
    print("🎲 抽奖系统综合测试完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
