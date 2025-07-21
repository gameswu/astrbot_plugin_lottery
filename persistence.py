import json
import os
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import asdict
import threading
from pathlib import Path

from .lottery import Lottery, LotteryData, Prize, ParticipationLimits, ProbabilitySettings, UserParticipation


class LotteryPersistence:
    """抽奖数据持久化管理器"""
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化持久化管理器
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.lotteries_file = self.data_dir / "lotteries.json"
        self.participants_dir = self.data_dir / "participants"
        self.participants_dir.mkdir(exist_ok=True)
        
        self._lock = threading.RLock()
    
    def save_lottery(self, lottery: Lottery) -> bool:
        """
        保存单个抽奖数据
        
        Args:
            lottery: 抽奖实例
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with self._lock:
                # 加载现有数据
                all_lotteries = self._load_all_lotteries_data()
                
                # 更新或添加当前抽奖
                lottery_data = self._serialize_lottery(lottery)
                all_lotteries[lottery.id] = lottery_data
                
                # 保存到文件
                with open(self.lotteries_file, 'w', encoding='utf-8') as f:
                    json.dump(all_lotteries, f, ensure_ascii=False, indent=2)
                
                # 保存参与者数据
                self._save_participants(lottery)
                
                return True
                
        except Exception as e:
            print(f"保存抽奖数据失败: {e}")
            return False
    
    def load_lottery(self, lottery_id: str) -> Optional[Lottery]:
        """
        加载单个抽奖数据
        
        Args:
            lottery_id: 抽奖ID
            
        Returns:
            Optional[Lottery]: 抽奖实例，如果不存在返回None
        """
        try:
            with self._lock:
                all_lotteries = self._load_all_lotteries_data()
                
                if lottery_id not in all_lotteries:
                    return None
                
                lottery_data = all_lotteries[lottery_id]
                lottery = self._deserialize_lottery(lottery_id, lottery_data)
                
                # 加载参与者数据
                self._load_participants(lottery)
                
                return lottery
                
        except Exception as e:
            print(f"加载抽奖数据失败: {e}")
            return None
    
    def load_all_lotteries(self) -> Dict[str, Lottery]:
        """
        加载所有抽奖数据
        
        Returns:
            Dict[str, Lottery]: 所有抽奖数据
        """
        try:
            with self._lock:
                all_lotteries_data = self._load_all_lotteries_data()
                lotteries = {}
                
                for lottery_id, lottery_data in all_lotteries_data.items():
                    try:
                        lottery = self._deserialize_lottery(lottery_id, lottery_data)
                        self._load_participants(lottery)
                        lotteries[lottery_id] = lottery
                    except Exception as e:
                        print(f"加载抽奖 {lottery_id} 失败: {e}")
                        continue
                
                return lotteries
                
        except Exception as e:
            print(f"加载所有抽奖数据失败: {e}")
            return {}
    
    def delete_lottery(self, lottery_id: str) -> bool:
        """
        删除抽奖数据
        
        Args:
            lottery_id: 抽奖ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with self._lock:
                # 加载现有数据
                all_lotteries = self._load_all_lotteries_data()
                
                if lottery_id not in all_lotteries:
                    return False
                
                # 删除抽奖数据
                del all_lotteries[lottery_id]
                
                # 保存到文件
                with open(self.lotteries_file, 'w', encoding='utf-8') as f:
                    json.dump(all_lotteries, f, ensure_ascii=False, indent=2)
                
                # 删除参与者数据文件
                participants_file = self.participants_dir / f"{lottery_id}.json"
                if participants_file.exists():
                    participants_file.unlink()
                
                return True
                
        except Exception as e:
            print(f"删除抽奖数据失败: {e}")
            return False
    
    def _load_all_lotteries_data(self) -> Dict:
        """加载所有抽奖的原始数据"""
        if not self.lotteries_file.exists():
            return {}
        
        try:
            with open(self.lotteries_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _serialize_lottery(self, lottery: Lottery) -> Dict:
        """序列化抽奖数据"""
        return {
            'data': asdict(lottery.data),
            'total_participants': lottery.total_participants,
            'total_attempts': lottery.total_attempts,
            'created_at': lottery.created_at.isoformat()
        }
    
    def _deserialize_lottery(self, lottery_id: str, lottery_data: Dict) -> Lottery:
        """反序列化抽奖数据"""
        data = lottery_data['data']
        
        # 重建数据结构
        participation_limits = ParticipationLimits(**data['participation_limits'])
        probability_settings = ProbabilitySettings(**data['probability_settings'])
        
        prizes = []
        for prize_data in data['prizes']:
            prizes.append(Prize(**prize_data))
        
        lottery_data_obj = LotteryData(
            name=data['name'],
            description=data['description'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            allowed_groups=data.get('allowed_groups', []),
            participation_limits=participation_limits,
            probability_settings=probability_settings,
            prizes=prizes
        )
        
        lottery = Lottery(lottery_id, lottery_data_obj)
        lottery.total_participants = lottery_data.get('total_participants', 0)
        lottery.total_attempts = lottery_data.get('total_attempts', 0)
        
        if 'created_at' in lottery_data:
            lottery.created_at = datetime.fromisoformat(lottery_data['created_at'])
        
        return lottery
    
    def _save_participants(self, lottery: Lottery):
        """保存参与者数据"""
        participants_file = self.participants_dir / f"{lottery.id}.json"
        
        participants_data = {}
        for user_id, participation in lottery.participants.items():
            participants_data[user_id] = asdict(participation)
        
        with open(participants_file, 'w', encoding='utf-8') as f:
            json.dump(participants_data, f, ensure_ascii=False, indent=2)
    
    def _load_participants(self, lottery: Lottery):
        """加载参与者数据"""
        participants_file = self.participants_dir / f"{lottery.id}.json"
        
        if not participants_file.exists():
            return
        
        try:
            with open(participants_file, 'r', encoding='utf-8') as f:
                participants_data = json.load(f)
            
            for user_id, participation_data in participants_data.items():
                lottery.participants[user_id] = UserParticipation(**participation_data)
                
        except Exception as e:
            print(f"加载参与者数据失败: {e}")


# 全局持久化管理器实例
_persistence_manager = None

def get_persistence_manager(data_dir: str = "data") -> LotteryPersistence:
    """获取持久化管理器单例"""
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = LotteryPersistence(data_dir)
    return _persistence_manager
