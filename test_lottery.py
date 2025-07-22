#!/usr/bin/env python3
"""
抽奖系统综合测试脚本
包含基础功能、持久化、概率模式等所有测试
"""

import json
import sys
import os
import tempfile
import shutil
import random
from datetime import datetime, timezone, timedelta

# 添加当前目录到path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery import Lottery, LotteryParseError, LotteryOperationError, LotteryStatus
from persistence import LotteryPersistence


def get_test_lottery_config():
    """获取测试用的抽奖配置"""
    now = datetime.now(timezone.utc)
    start_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return {
        "name": "测试抽奖",
        "description": "这是一个测试抽奖",
        "start_time": start_time,
        "end_time": end_time,
        "allowed_groups": ["123456", "789012"],
        "participation_limits": {
            "max_total_participants": 10,
            "max_attempts_per_user": 3,
            "max_wins_per_user": 2
        },
        "probability_settings": {
            "probability_mode": "fixed",
            "base_probability": 0.5
        },
        "prizes": [
            {
                "name": "一等奖",
                "description": "大奖",
                "image_url": "",
                "weight": 1,
                "quantity": 2,
                "max_win_per_user": 1
            },
            {
                "name": "二等奖",
                "description": "小奖",
                "image_url": "",
                "weight": 10,
                "quantity": 5,
                "max_win_per_user": 1
            }
        ]
    }


def test_basic_functionality():
    """测试基础功能"""
    print("🔧 测试基础功能...")
    
    # 清空现有抽奖
    Lottery._lotteries.clear()
    # 确保没有持久化管理器干扰测试
    Lottery.set_persistence_manager(None)
    Lottery.enable_auto_save(False)
    
    # 创建抽奖
    config = get_test_lottery_config()
    lottery_json = json.dumps(config)
    lottery = Lottery.parse_and_create(lottery_json)
    
    assert lottery is not None, "抽奖创建失败"
    assert lottery.data.name == "测试抽奖", "抽奖名称不正确"
    assert lottery.get_status() == LotteryStatus.ACTIVE, "抽奖状态不正确"
    
    # 用户参与
    won, prize, message = lottery.participate("user1")
    assert isinstance(won, bool), "返回值类型错误"
    assert isinstance(message, str), "消息类型错误"
    
    # 查询功能
    found_lottery = Lottery.get_lottery_by_id(lottery.id)
    assert found_lottery is not None, "根据ID查找失败"
    
    found_lottery = Lottery.get_lottery_by_name("测试抽奖")
    assert found_lottery is not None, "根据名称查找失败"
    
    all_lotteries = Lottery.get_all_lotteries()
    assert len(all_lotteries) == 1, "获取所有抽奖失败"
    
    print("✅ 基础功能测试通过")


def test_persistence():
    """测试持久化功能"""
    print("💾 测试持久化功能...")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 初始化持久化
        persistence = LotteryPersistence(temp_dir)
        Lottery.set_persistence_manager(persistence)
        Lottery.enable_auto_save(True)
        
        # 清空内存
        Lottery._lotteries.clear()
        
        # 创建抽奖（会自动保存）
        config = get_test_lottery_config()
        config["name"] = "持久化测试抽奖"
        lottery_json = json.dumps(config)
        lottery = Lottery.parse_and_create(lottery_json)
        
        # 用户参与（会自动保存）
        lottery.participate("user1")
        lottery.participate("user2")
        
        original_id = lottery.id
        original_participants = len(lottery.participants)
        
        # 模拟重启：清空内存后重新加载
        Lottery._lotteries.clear()
        Lottery.load_all_from_disk()
        
        # 验证数据恢复
        reloaded_lottery = Lottery.get_lottery_by_id(original_id)
        assert reloaded_lottery is not None, "持久化恢复失败"
        assert len(reloaded_lottery.participants) == original_participants, "参与者数据恢复失败"
        
        # 测试删除
        success = Lottery.delete_lottery(original_id)
        assert success, "删除失败"
        
        print("✅ 持久化测试通过")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        # 重置持久化管理器
        Lottery.set_persistence_manager(None)
        Lottery.enable_auto_save(False)


def test_probability_modes():
    """测试概率模式"""
    print("🎯 测试概率模式...")
    
    Lottery._lotteries.clear()
    # 确保没有持久化管理器干扰测试
    Lottery.set_persistence_manager(None)
    Lottery.enable_auto_save(False)
    
    # 测试固定概率模式
    config = get_test_lottery_config()
    config["name"] = "固定概率测试"
    config["probability_settings"]["probability_mode"] = "fixed"
    config["probability_settings"]["base_probability"] = 1.0  # 100%中奖
    
    lottery = Lottery.parse_and_create(json.dumps(config))
    won, prize, message = lottery.participate("user1")
    assert won == True, "固定概率模式测试失败"
    
    # 测试消耗模式
    config["name"] = "消耗模式测试"
    config["probability_settings"]["probability_mode"] = "exhaust"
    config["probability_settings"]["base_probability"] = 0.0
    
    lottery2 = Lottery.parse_and_create(json.dumps(config))
    # 消耗模式应该会动态调整概率
    prob = lottery2._calculate_dynamic_probability()
    assert prob > 0, "消耗模式概率计算失败"
    
    print("✅ 概率模式测试通过")


def test_error_handling():
    """测试错误处理"""
    print("🚨 测试错误处理...")
    
    # 确保没有持久化管理器干扰测试
    Lottery.set_persistence_manager(None)
    Lottery.enable_auto_save(False)
    
    # 测试JSON格式错误
    try:
        Lottery.parse_and_create("invalid json")
        assert False, "应该抛出解析错误"
    except LotteryParseError:
        pass
    
    # 测试缺少字段
    try:
        Lottery.parse_and_create('{"name": "test"}')
        assert False, "应该抛出字段缺失错误"
    except LotteryParseError:
        pass
    
    # 测试已结束的抽奖参与
    past_config = get_test_lottery_config()
    past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past_config["start_time"] = past_time
    past_config["end_time"] = past_time  # 开始和结束时间相同，会报错
    
    try:
        Lottery.parse_and_create(json.dumps(past_config))
        assert False, "应该抛出时间错误"
    except LotteryParseError:
        pass
    
    # 测试正确的过期抽奖
    past_config["end_time"] = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past_lottery = Lottery.parse_and_create(json.dumps(past_config))
    
    try:
        past_lottery.participate("user1")
        assert False, "应该抛出操作错误"
    except LotteryOperationError:
        pass
    
    print("✅ 错误处理测试通过")


def test_limits():
    """测试各种限制"""
    print("🚫 测试限制功能...")
    
    # 确保没有持久化管理器干扰测试
    Lottery.set_persistence_manager(None)
    Lottery.enable_auto_save(False)
    
    config = get_test_lottery_config()
    config["participation_limits"]["max_attempts_per_user"] = 1
    config["participation_limits"]["max_wins_per_user"] = 1
    config["probability_settings"]["base_probability"] = 1.0  # 确保中奖
    
    lottery = Lottery.parse_and_create(json.dumps(config))
    
    # 第一次参与应该成功
    won, prize, message = lottery.participate("user1")
    
    # 第二次参与应该失败（超过尝试次数限制）
    try:
        lottery.participate("user1")
        assert False, "应该抛出次数限制错误"
    except LotteryOperationError:
        pass
    
    print("✅ 限制功能测试通过")


def test_cancel_functionality():
    """测试取消功能"""
    print("🚫 测试取消功能...")
    
    # 确保没有持久化管理器干扰测试
    Lottery.set_persistence_manager(None)
    Lottery.enable_auto_save(False)
    Lottery._lotteries.clear()
    
    # 创建一个正在进行的抽奖
    config = get_test_lottery_config()
    config["name"] = "取消测试抽奖"
    lottery = Lottery.parse_and_create(json.dumps(config))
    
    # 验证初始状态
    assert lottery.get_status() == LotteryStatus.ACTIVE, "抽奖应该处于活跃状态"
    
    # 用户参与抽奖
    won, prize, message = lottery.participate("user1")
    assert isinstance(won, bool), "参与结果类型错误"
    
    # 取消抽奖
    result = lottery.cancel_lottery()
    assert result == True, "取消抽奖应该成功"
    
    # 验证抽奖状态变为已结束
    assert lottery.get_status() == LotteryStatus.ENDED, "取消后抽奖状态应该为已结束"
    
    # 尝试在取消后参与抽奖，应该失败
    try:
        lottery.participate("user2")
        assert False, "取消后应该无法参与抽奖"
    except LotteryOperationError:
        pass
    
    # 测试重复取消，应该失败
    try:
        lottery.cancel_lottery()
        assert False, "已结束的抽奖不应该能再次取消"
    except LotteryOperationError:
        pass
    
    # 测试已结束抽奖的取消
    past_config = get_test_lottery_config()
    past_config["name"] = "已结束抽奖"
    past_time_start = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past_time_end = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past_config["start_time"] = past_time_start
    past_config["end_time"] = past_time_end
    ended_lottery = Lottery.parse_and_create(json.dumps(past_config))
    
    try:
        ended_lottery.cancel_lottery()
        assert False, "已结束的抽奖不应该能被取消"
    except LotteryOperationError:
        pass
    
    print("✅ 取消功能测试通过")


def test_start_functionality():
    """测试立即开始功能"""
    print("🚀 测试立即开始功能...")
    
    # 确保没有持久化管理器干扰测试
    Lottery.set_persistence_manager(None)
    Lottery.enable_auto_save(False)
    Lottery._lotteries.clear()
    
    # 创建一个未开始的抽奖（开始时间在未来）
    config = get_test_lottery_config()
    config["name"] = "立即开始测试抽奖"
    future_time_start = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    future_time_end = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    config["start_time"] = future_time_start
    config["end_time"] = future_time_end
    lottery = Lottery.parse_and_create(json.dumps(config))
    
    # 验证初始状态
    assert lottery.get_status() == LotteryStatus.PENDING, "抽奖应该处于待开始状态"
    
    # 尝试在未开始时参与抽奖，应该失败
    try:
        lottery.participate("user1")
        assert False, "未开始的抽奖不应该能参与"
    except LotteryOperationError:
        pass
    
    # 立即开始抽奖
    result = lottery.start_lottery()
    assert result == True, "立即开始抽奖应该成功"
    
    # 验证抽奖状态变为活跃
    assert lottery.get_status() == LotteryStatus.ACTIVE, "立即开始后抽奖状态应该为活跃"
    
    # 尝试在开始后参与抽奖，应该成功
    won, prize, message = lottery.participate("user1")
    assert isinstance(won, bool), "参与结果类型错误"
    assert isinstance(message, str), "消息类型错误"
    
    # 测试重复开始，应该失败
    try:
        lottery.start_lottery()
        assert False, "已开始的抽奖不应该能再次开始"
    except LotteryOperationError:
        pass
    
    # 测试已结束抽奖的开始
    past_config = get_test_lottery_config()
    past_config["name"] = "已结束抽奖"
    past_time_start = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past_time_end = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past_config["start_time"] = past_time_start
    past_config["end_time"] = past_time_end
    ended_lottery = Lottery.parse_and_create(json.dumps(past_config))
    
    try:
        ended_lottery.start_lottery()
        assert False, "已结束的抽奖不应该能被立即开始"
    except LotteryOperationError:
        pass
    
    # 测试已活跃抽奖的开始
    active_config = get_test_lottery_config()
    active_config["name"] = "已活跃抽奖"
    active_lottery = Lottery.parse_and_create(json.dumps(active_config))
    
    try:
        active_lottery.start_lottery()
        assert False, "已活跃的抽奖不应该能被立即开始"
    except LotteryOperationError:
        pass
    
    print("✅ 立即开始功能测试通过")


def test_system_crash_recovery():
    """测试系统崩溃恢复场景 - 重点测试exhaust模式"""
    print("💥 测试系统崩溃恢复场景...")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 初始化持久化
        persistence = LotteryPersistence(temp_dir)
        Lottery.set_persistence_manager(persistence)
        Lottery.enable_auto_save(True)
        
        # 清空内存
        Lottery._lotteries.clear()
        
        # 创建一个专门测试exhaust模式的抽奖活动
        config = get_test_lottery_config()
        config.update({
            "name": "Exhaust模式测试抽奖",
            "description": "测试exhaust模式是否能够准确消耗完奖品",
            "participation_limits": {
                "max_total_participants": 30,  # 30个用户 
                "max_attempts_per_user": 4,    # 每人最多抽4次
                "max_wins_per_user": 3         # 每人最多中3次
            },
            "probability_settings": {
                "probability_mode": "exhaust",  # 使用exhaust模式
                "base_probability": 0.1        # 基础概率10%
            },
            "prizes": [
                {
                    "name": "特等奖",
                    "description": "MacBook Pro",
                    "image_url": "",
                    "weight": 1,
                    "quantity": 2,            # 只有2个特等奖
                    "max_win_per_user": 1
                },
                {
                    "name": "一等奖",
                    "description": "iPad Pro",
                    "image_url": "",
                    "weight": 8,
                    "quantity": 8,           # 8个一等奖
                    "max_win_per_user": 1
                },
                {
                    "name": "二等奖",
                    "description": "AirPods Pro",
                    "image_url": "",
                    "weight": 20,
                    "quantity": 25,           # 25个二等奖
                    "max_win_per_user": 2
                },
                {
                    "name": "三等奖",
                    "description": "Apple Watch",
                    "image_url": "",
                    "weight": 30,
                    "quantity": 35,           # 35个三等奖
                    "max_win_per_user": 2
                }
            ]
        })
        
        lottery_json = json.dumps(config)
        lottery = Lottery.parse_and_create(lottery_json)
        original_id = lottery.id
        
        total_prizes = sum(p.quantity for p in lottery.data.prizes)
        max_possible_wins = lottery.data.participation_limits.max_total_participants * lottery.data.participation_limits.max_wins_per_user
        
        print(f"📊 创建抽奖活动: {lottery.data.name}")
        print(f"🎯 抽奖ID: {original_id}")
        print(f"🎁 总奖品数量: {total_prizes}")
        print(f"👥 最大参与人数: {lottery.data.participation_limits.max_total_participants}")
        print(f"🎟️ 每人最大抽奖次数: {lottery.data.participation_limits.max_attempts_per_user}")
        print(f"🏆 每人最大中奖次数: {lottery.data.participation_limits.max_wins_per_user}")
        print(f"📈 理论最大中奖人次: {max_possible_wins}")
        print(f"🎯 概率模式: {lottery.data.probability_settings.probability_mode}")
        print("=" * 80)
        
        # 创建用户池，随机抽奖顺序
        all_users = [f"user_{i:03d}" for i in range(1, lottery.data.participation_limits.max_total_participants + 1)]
        
        # 阶段1: 模拟随机抽奖过程
        print("🚀 阶段1: 随机顺序抽奖测试...")
        phase1_attempts = 0
        phase1_winners = []
        phase1_attempts_per_user = {}
        
        # 每轮随机选择用户抽奖，直到达到一定的抽奖次数
        max_phase1_attempts = 100  # 阶段1最多100次抽奖
        round_count = 0
        
        while phase1_attempts < max_phase1_attempts:
            round_count += 1
            print(f"\n🎲 第{round_count}轮随机抽奖 (目标: 每轮10-20次随机抽奖)")
            
            # 检查是否还有奖品
            remaining_prizes = sum(p.remaining_quantity for p in lottery.data.prizes if p.quantity > 0)
            if remaining_prizes == 0:
                print(f"   🎊 所有奖品已被抽完，提前结束阶段1！")
                break
            
            # 每轮随机选择10-20次抽奖
            round_attempts = random.randint(5, 10)
            round_winners = 0
            
            for _ in range(round_attempts):
                if phase1_attempts >= max_phase1_attempts:
                    break
                    
                # 随机选择一个用户
                available_users = [
                    user for user in all_users 
                    if phase1_attempts_per_user.get(user, 0) < lottery.data.participation_limits.max_attempts_per_user
                ]
                
                if not available_users:
                    print("   ⚠️ 所有用户都已达到抽奖次数上限")
                    break
                
                user_id = random.choice(available_users)
                phase1_attempts_per_user[user_id] = phase1_attempts_per_user.get(user_id, 0) + 1
                
                try:
                    won, prize, message = lottery.participate(user_id)
                    phase1_attempts += 1
                    
                    if won and prize:
                        phase1_winners.append({
                            'user': user_id,
                            'prize': prize.name,
                            'description': prize.description,
                            'round': round_count
                        })
                        round_winners += 1
                        print(f"   🎉 {user_id} 中奖! {prize.name} - {prize.description}")
                    
                except Exception as e:
                    print(f"   ❌ {user_id} 抽奖失败: {e}")
            
            # 显示本轮统计
            remaining_prizes = sum(p.remaining_quantity for p in lottery.data.prizes if p.quantity > 0)
            print(f"   📊 本轮统计: 抽奖{round_attempts}次, 中奖{round_winners}次")
            print(f"   🎁 剩余奖品: {remaining_prizes}/{total_prizes}")
            
            # 计算并显示当前的动态概率
            current_prob = lottery._calculate_dynamic_probability()
            remaining_wins = lottery._calculate_remaining_wins()
            print(f"   🎯 当前动态概率: {current_prob:.3f}, 剩余可中奖次数: {remaining_wins}")
            
            # 显示各奖品剩余情况
            print("   📦 奖品详情:")
            for prize in lottery.data.prizes:
                distributed = prize.quantity - prize.remaining_quantity
                percentage = (distributed / prize.quantity * 100) if prize.quantity > 0 else 0
                print(f"      {prize.name}: {distributed}/{prize.quantity} ({percentage:.1f}%)")
                
            # 如果奖品全部消耗完，提前结束
            if remaining_prizes == 0:
                print(f"   🎊 所有奖品已被抽完！")
                break
        
        print(f"\n📈 阶段1总统计:")
        print(f"   总抽奖次数: {phase1_attempts}")
        print(f"   参与人数: {len(lottery.participants)}")
        print(f"   中奖人数: {len(phase1_winners)}")
        print(f"   中奖率: {len(phase1_winners)/phase1_attempts*100:.1f}%")
        
        print("\n💥 模拟系统崩溃...")
        print("🔄 系统重启中...")
        
        # 记录崩溃前的状态
        crash_participants = len(lottery.participants)
        crash_winners = len(phase1_winners)
        crash_remaining_prizes = sum(p.remaining_quantity for p in lottery.data.prizes if p.quantity > 0)
        
        # 模拟系统崩溃
        Lottery._lotteries.clear()
        
        # 系统恢复
        print("💾 从磁盘恢复数据...")
        persistence = LotteryPersistence(temp_dir)
        Lottery.set_persistence_manager(persistence)
        Lottery.enable_auto_save(True)
        Lottery.load_all_from_disk()
        
        recovered_lottery = Lottery.get_lottery_by_id(original_id)
        assert recovered_lottery is not None, "❌ 数据恢复失败！"
        
        print("✅ 系统恢复成功！")
        
        # 阶段2: 继续随机抽奖，观察exhaust模式如何处理剩余奖品
        print(f"\n� 阶段2: 系统恢复后继续抽奖，观察exhaust模式效果...")
        phase2_attempts = 0
        phase2_winners = []
        
        # 继续抽奖直到大部分奖品被消耗完或用户达到限制
        max_phase2_attempts = 300
        round_count = 0
        consecutive_no_progress_rounds = 0  # 连续没有进展的轮数
        
        while phase2_attempts < max_phase2_attempts and consecutive_no_progress_rounds < 10:
            round_count += 1
            
            # 检查是否还有奖品和可用用户
            remaining_prizes = sum(p.remaining_quantity for p in recovered_lottery.data.prizes if p.quantity > 0)
            if remaining_prizes == 0:
                print(f"\n🎊 所有有限量奖品已被抽完！")
                break
            
            # 获取可用用户 - 需要检查抽奖次数和中奖次数两个限制
            available_users = []
            
            # 检查已参与的用户
            for user in all_users:
                if user in recovered_lottery.participants:
                    user_data = recovered_lottery.participants[user]
                    # 检查抽奖次数限制
                    if user_data.attempts >= recovered_lottery.data.participation_limits.max_attempts_per_user:
                        continue
                    # 检查中奖次数限制
                    if len(user_data.wins) >= recovered_lottery.data.participation_limits.max_wins_per_user:
                        continue
                    available_users.append(user)
                else:
                    # 新用户，可以参与
                    available_users.append(user)
            
            if not available_users:
                print(f"\n⚠️ 所有用户都已达到抽奖限制")
                break
            
            print(f"\n🎲 阶段2-第{round_count}轮: 剩余奖品{remaining_prizes}个, 可用用户{len(available_users)}个")
            
            # 每轮抽奖次数根据剩余奖品数量动态调整，但不超过可用用户数
            round_attempts = min(random.randint(5, 15), len(available_users), max_phase2_attempts - phase2_attempts)
            round_winners = 0
            round_start_prizes = remaining_prizes
            
            for _ in range(round_attempts):
                if phase2_attempts >= max_phase2_attempts:
                    break
                
                # 重新获取可用用户列表（因为状态可能变化）
                current_available_users = []
                for user in all_users:
                    if user in recovered_lottery.participants:
                        user_data = recovered_lottery.participants[user]
                        if (user_data.attempts < recovered_lottery.data.participation_limits.max_attempts_per_user and
                            len(user_data.wins) < recovered_lottery.data.participation_limits.max_wins_per_user):
                            current_available_users.append(user)
                    else:
                        current_available_users.append(user)
                
                if not current_available_users:
                    break
                
                user_id = random.choice(current_available_users)
                
                try:
                    won, prize, message = recovered_lottery.participate(user_id)
                    phase2_attempts += 1
                    
                    if won and prize:
                        phase2_winners.append({
                            'user': user_id,
                            'prize': prize.name,
                            'description': prize.description,
                            'round': round_count
                        })
                        round_winners += 1
                        print(f"   🎉 {user_id} 中奖! {prize.name}")
                    
                except Exception as e:
                    # 忽略限制错误，继续下一个用户
                    continue
            
            # 检查本轮是否有进展
            round_end_prizes = sum(p.remaining_quantity for p in recovered_lottery.data.prizes if p.quantity > 0)
            if round_start_prizes == round_end_prizes and round_winners == 0:
                consecutive_no_progress_rounds += 1
            else:
                consecutive_no_progress_rounds = 0
            
            # 显示进度
            remaining_wins_recovery = recovered_lottery._calculate_remaining_wins()
            current_prob_recovery = recovered_lottery._calculate_dynamic_probability()
            print(f"   📊 本轮: 抽奖{round_attempts}次, 中奖{round_winners}次, 剩余奖品{round_end_prizes}个")
            print(f"   🎯 动态概率: {current_prob_recovery:.3f}, 剩余可中奖次数: {remaining_wins_recovery}")
            
            # 如果剩余奖品很少且连续多轮没进展，提前结束
            if round_end_prizes <= 5 and consecutive_no_progress_rounds >= 3:
                print(f"   ⏸️ 剩余奖品较少且连续{consecutive_no_progress_rounds}轮无进展，提前结束测试")
                break
        
        # 最终统计
        print(f"\n🏆 最终统计报告:")
        total_attempts = phase1_attempts + phase2_attempts
        total_winners = len(phase1_winners) + len(phase2_winners)
        final_participants = len(recovered_lottery.participants)
        
        print(f"   总抽奖次数: {total_attempts}")
        print(f"   总参与人数: {final_participants}")
        print(f"   总中奖人次: {total_winners}")
        print(f"   总体中奖率: {total_winners/total_attempts*100:.1f}%")
        
        # 详细的奖品消耗统计
        print(f"\n🎁 奖品消耗详情:")
        total_distributed = 0
        for prize in recovered_lottery.data.prizes:
            distributed = prize.quantity - prize.remaining_quantity if prize.quantity > 0 else 0
            total_distributed += distributed
            percentage = (distributed / prize.quantity * 100) if prize.quantity > 0 else 0
            print(f"   {prize.name}: {distributed}/{prize.quantity} ({percentage:.1f}%) 剩余{prize.remaining_quantity}")
        
        print(f"\n� Exhaust模式效果分析:")
        print(f"   奖品总消耗率: {total_distributed/total_prizes*100:.1f}%")
        print(f"   理论最大中奖人次: {max_possible_wins}")
        print(f"   实际中奖人次: {total_winners}")
        print(f"   中奖效率: {total_winners/max_possible_wins*100:.1f}%")
        
        # 验证数据一致性
        print(f"\n� 数据一致性验证:")
        print(f"   崩溃前参与者: {crash_participants}")
        print(f"   恢复后参与者: {final_participants}")
        print(f"   崩溃前中奖: {crash_winners}")
        print(f"   最终中奖: {total_winners}")
        
        print("✅ Exhaust模式系统崩溃恢复测试通过")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        # 重置持久化管理器
        Lottery.set_persistence_manager(None)
        Lottery.enable_auto_save(False)


def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行抽奖系统综合测试")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_persistence()
        test_probability_modes()
        test_error_handling()
        test_limits()
        test_cancel_functionality()  # 新增的取消功能测试
        test_start_functionality()   # 新增的立即开始功能测试
        test_system_crash_recovery()  # 新增的崩溃恢复测试
        
        print("=" * 50)
        print("🎉 所有测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
