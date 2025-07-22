import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import random
import threading


class LotteryStatus(Enum):
    """抽奖状态枚举"""
    PENDING = "pending"      # 未开始
    ACTIVE = "active"        # 进行中
    ENDED = "ended"          # 已结束
    CANCELLED = "cancelled"  # 已取消


@dataclass
class Prize:
    """奖品数据类"""
    name: str
    description: str
    image_url: str
    weight: int
    quantity: int
    max_win_per_user: int
    remaining_quantity: int = None  # 剩余数量
    
    def __post_init__(self):
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity


@dataclass
class ParticipationLimits:
    """参与限制数据类"""
    max_total_participants: int
    max_attempts_per_user: int
    max_wins_per_user: int


@dataclass
class ProbabilitySettings:
    """概率设置数据类"""
    probability_mode: str  # "fixed", "dynamic", "exhaust"
    base_probability: float


@dataclass
class LotteryData:
    """抽奖数据类"""
    name: str
    description: str
    start_time: str
    end_time: str
    allowed_groups: List[str]
    participation_limits: ParticipationLimits
    probability_settings: ProbabilitySettings
    prizes: List[Prize]
    creator: str = ""  # 创建者字段，默认为空字符串


@dataclass
class UserParticipation:
    """用户参与记录"""
    user_id: str
    attempts: int = 0
    wins: List[str] = None  # 中奖奖品名称列表
    
    def __post_init__(self):
        if self.wins is None:
            self.wins = []


class LotteryParseError(Exception):
    """抽奖解析错误"""
    pass


class LotteryOperationError(Exception):
    """抽奖操作错误"""
    pass


class Lottery:
    """抽奖系统主类"""
    
    # 类级别的存储，实际使用时可以替换为数据库
    _lotteries: Dict[str, 'Lottery'] = {}
    _lock = threading.RLock()
    _auto_save = True  # 是否自动保存到磁盘
    _persistence_manager = None  # 持久化管理器
    
    def __init__(self, lottery_id: str, data: LotteryData, creator: str = ""):
        self.id = lottery_id
        self.data = data
        # 设置创建者
        if creator:
            self.data.creator = creator
        self.participants: Dict[str, UserParticipation] = {}
        self.total_participants = 0
        self.total_attempts = 0
        self.created_at = datetime.now(timezone.utc)
    
    @classmethod
    def set_persistence_manager(cls, persistence_manager):
        """设置持久化管理器"""
        cls._persistence_manager = persistence_manager
    
    @classmethod
    def enable_auto_save(cls, enabled: bool = True):
        """启用或禁用自动保存"""
        cls._auto_save = enabled
    
    @classmethod
    def load_all_from_disk(cls):
        """从磁盘加载所有抽奖数据"""
        if cls._persistence_manager is None:
            return
        
        with cls._lock:
            loaded_lotteries = cls._persistence_manager.load_all_lotteries()
            cls._lotteries.update(loaded_lotteries)
    
    def _auto_save_if_enabled(self):
        """如果启用了自动保存，则保存到磁盘"""
        if self._auto_save and self._persistence_manager:
            self._persistence_manager.save_lottery(self)
    
    @classmethod
    def set_persistence_manager(cls, persistence_manager):
        """设置持久化管理器"""
        cls._persistence_manager = persistence_manager
    
    @classmethod
    def enable_auto_save(cls, enabled: bool = True):
        """启用或禁用自动保存"""
        cls._auto_save = enabled
    
    @classmethod
    def load_all_from_disk(cls):
        """从磁盘加载所有抽奖数据"""
        if cls._persistence_manager is None:
            return
        
        with cls._lock:
            loaded_lotteries = cls._persistence_manager.load_all_lotteries()
            cls._lotteries.update(loaded_lotteries)
    
    def _auto_save_if_enabled(self):
        """如果启用了自动保存，则保存到磁盘"""
        if self._auto_save and self._persistence_manager:
            self._persistence_manager.save_lottery(self)
        
    @classmethod
    def parse_and_create(cls, json_str: str, creator: str = "") -> 'Lottery':
        """
        从JSON字符串解析并创建抽奖
        
        Args:
            json_str: 抽奖配置的JSON字符串
            creator: 创建者标识（可选）
            
        Returns:
            Lottery: 创建的抽奖实例
            
        Raises:
            LotteryParseError: 解析错误时抛出
        """
        try:
            # 解析JSON
            raw_data = json.loads(json_str)
            
            # 验证必需字段
            required_fields = ['name', 'description', 'start_time', 'end_time', 
                             'allowed_groups', 'participation_limits', 'probability_settings', 'prizes']
            
            for field in required_fields:
                if field not in raw_data:
                    raise LotteryParseError(f"缺少必需字段: {field}")
            
            # 验证时间格式
            try:
                start_time = datetime.fromisoformat(raw_data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(raw_data['end_time'].replace('Z', '+00:00'))
                
                if start_time >= end_time:
                    raise LotteryParseError("开始时间必须早于结束时间")
                    
            except ValueError as e:
                raise LotteryParseError(f"时间格式错误: {e}")
            
            # 解析参与限制
            limits_data = raw_data['participation_limits']
            required_limit_fields = ['max_total_participants', 'max_attempts_per_user', 'max_wins_per_user']
            for field in required_limit_fields:
                if field not in limits_data:
                    raise LotteryParseError(f"参与限制中缺少字段: {field}")
                if not isinstance(limits_data[field], int) or limits_data[field] < 0:
                    raise LotteryParseError(f"参与限制字段 {field} 必须是非负整数")
            
            participation_limits = ParticipationLimits(**limits_data)
            
            # 解析概率设置
            prob_data = raw_data['probability_settings']
            required_prob_fields = ['probability_mode', 'base_probability']
            for field in required_prob_fields:
                if field not in prob_data:
                    raise LotteryParseError(f"概率设置中缺少字段: {field}")
            
            if prob_data['probability_mode'] not in ['fixed', 'dynamic', 'exhaust']:
                raise LotteryParseError("概率模式必须是 'fixed', 'dynamic' 或 'exhaust' 中的一个")
            
            if not isinstance(prob_data['base_probability'], (int, float)) or \
               not (0 <= prob_data['base_probability'] <= 1):
                raise LotteryParseError("基础概率必须是0-1之间的数值")
                
            probability_settings = ProbabilitySettings(**prob_data)
            
            # 解析奖品列表
            prizes_data = raw_data['prizes']
            if not prizes_data:
                raise LotteryParseError("奖品列表不能为空")
                
            prizes = []
            required_prize_fields = ['name', 'description', 'weight', 'quantity', 'max_win_per_user']
            
            for i, prize_data in enumerate(prizes_data):
                for field in required_prize_fields:
                    if field not in prize_data:
                        raise LotteryParseError(f"奖品 {i+1} 中缺少字段: {field}")
                
                # 验证数值字段
                if not isinstance(prize_data['weight'], int) or prize_data['weight'] <= 0:
                    raise LotteryParseError(f"奖品 {i+1} 的权重必须是正整数")
                    
                if not isinstance(prize_data['quantity'], int) or prize_data['quantity'] < -1 or prize_data['quantity'] == 0:
                    raise LotteryParseError(f"奖品 {i+1} 的数量必须是正整数或-1（无限量）")
                    
                if not isinstance(prize_data['max_win_per_user'], int) or prize_data['max_win_per_user'] <= 0:
                    raise LotteryParseError(f"奖品 {i+1} 的单用户最大获得数量必须是正整数")
                
                # 设置默认值
                if 'image_url' not in prize_data:
                    prize_data['image_url'] = ""
                    
                prizes.append(Prize(**prize_data))
            
            # 创建抽奖数据
            lottery_data = LotteryData(
                name=raw_data['name'],
                description=raw_data['description'],
                start_time=raw_data['start_time'],
                end_time=raw_data['end_time'],
                allowed_groups=raw_data['allowed_groups'],
                participation_limits=participation_limits,
                probability_settings=probability_settings,
                prizes=prizes
            )
            
            # 生成唯一ID并创建抽奖
            lottery_id = str(uuid.uuid4())
            lottery = cls(lottery_id, lottery_data, creator)
            
            # 存储抽奖
            with cls._lock:
                cls._lotteries[lottery_id] = lottery
                
            # 自动保存到磁盘
            lottery._auto_save_if_enabled()
                
            return lottery
            
        except json.JSONDecodeError as e:
            raise LotteryParseError(f"JSON格式错误: {e}")
        except Exception as e:
            if isinstance(e, LotteryParseError):
                raise
            raise LotteryParseError(f"解析错误: {e}")
    
    def participate(self, user_id: str) -> Tuple[bool, Optional[Prize], str]:
        """
        用户参与抽奖
        
        Args:
            user_id: 用户ID
            
        Returns:
            Tuple[bool, Optional[Prize], str]: (是否中奖, 中奖奖品, 消息)
            
        Raises:
            LotteryOperationError: 操作错误时抛出
        """
        with self._lock:
            # 检查抽奖状态
            status = self.get_status()
            if status != LotteryStatus.ACTIVE:
                raise LotteryOperationError(f"抽奖当前状态为 {status.value}，无法参与")
            
            # 获取或创建用户参与记录
            if user_id not in self.participants:
                self.participants[user_id] = UserParticipation(user_id)
                self.total_participants += 1
            
            user_participation = self.participants[user_id]
            
            # 检查参与限制
            limits = self.data.participation_limits
            
            # 检查总参与人数限制
            if limits.max_total_participants > 0 and self.total_participants > limits.max_total_participants:
                raise LotteryOperationError("参与人数已达上限")
            
            # 检查用户抽奖次数限制
            if user_participation.attempts >= limits.max_attempts_per_user:
                raise LotteryOperationError(f"您的抽奖次数已达上限（{limits.max_attempts_per_user}次）")
            
            # 检查用户中奖次数限制
            if limits.max_wins_per_user > 0 and len(user_participation.wins) >= limits.max_wins_per_user:
                raise LotteryOperationError(f"您的中奖次数已达上限（{limits.max_wins_per_user}次）")
            
            # 增加抽奖次数
            user_participation.attempts += 1
            self.total_attempts += 1
            
            # 计算是否中奖
            won, prize = self._calculate_win(user_id)
            
            if won and prize:
                # 处理中奖
                user_participation.wins.append(prize.name)
                if prize.quantity > 0:  # -1表示无限量
                    prize.remaining_quantity -= 1
                
                # 自动保存到磁盘
                self._auto_save_if_enabled()
                
                return True, prize, f"恭喜您中奖了！获得奖品：{prize.name}"
            else:
                # 即使没中奖也要保存（因为attempts增加了）
                self._auto_save_if_enabled()
                return False, None, "很遗憾，这次没有中奖，请再接再厉！"
    
    def _calculate_win(self, user_id: str) -> Tuple[bool, Optional[Prize]]:
        """计算用户是否中奖及中奖奖品"""
        # 计算中奖概率
        if self.data.probability_settings.probability_mode == 'fixed':
            win_probability = self.data.probability_settings.base_probability
        else:
            win_probability = self._calculate_dynamic_probability()
        
        # 判断是否中奖
        if random.random() > win_probability:
            return False, None
        
        # 获取可中奖的奖品
        available_prizes = self._get_available_prizes(user_id)
        if not available_prizes:
            return False, None
        
        # 根据权重选择奖品
        total_weight = sum(prize.weight for prize in available_prizes)
        if total_weight == 0:
            return False, None
            
        rand_value = random.randint(1, total_weight)
        current_weight = 0
        
        for prize in available_prizes:
            current_weight += prize.weight
            if rand_value <= current_weight:
                return True, prize
        
        return False, None
    
    def _calculate_dynamic_probability(self) -> float:
        """计算动态概率"""
        base_prob = self.data.probability_settings.base_probability
        
        # 如果是 fixed 模式，直接返回基础概率
        if self.data.probability_settings.probability_mode == 'fixed':
            return base_prob
        
        # 如果是 dynamic 模式，返回稍微调整的概率（这里可以根据需要添加其他逻辑）
        if self.data.probability_settings.probability_mode == 'dynamic':
            return base_prob
        
        # 如果是 exhaust 模式，需要计算动态概率以尽量消耗完奖品
        if self.data.probability_settings.probability_mode == 'exhaust':
            # 计算剩余奖品总数
            total_remaining = sum(
                prize.remaining_quantity if prize.quantity > 0 else 0  # 无限量奖品不参与动态调整
                for prize in self.data.prizes
            )
            
            # 如果没有有限量的奖品，返回基础概率
            if total_remaining <= 0:
                return base_prob
            
            # 计算剩余中奖次数总数
            total_remaining_wins = self._calculate_remaining_wins()
            
            # 如果没有剩余中奖次数，返回0
            if total_remaining_wins <= 0:
                return 0.0
            
            # 如果剩余奖品数量大于等于剩余中奖次数，应该100%中奖
            if total_remaining >= total_remaining_wins:
                return 1.0
            
            # 否则根据剩余奖品数量和剩余中奖次数计算所需概率
            needed_prob = total_remaining / total_remaining_wins
            
            # 确保概率不低于基础概率
            return max(base_prob, needed_prob)
        
        return base_prob
    
    def _calculate_remaining_wins(self) -> int:
        """计算剩余的中奖人次数（还能中奖的总次数）"""
        # 计算现有用户的剩余中奖次数（需要考虑抽奖次数限制）
        remaining_wins_existing_users = 0
        for user in self.participants.values():
            # 用户剩余的中奖次数
            remaining_wins = max(0, self.data.participation_limits.max_wins_per_user - len(user.wins))
            # 用户剩余的抽奖次数
            remaining_attempts = max(0, self.data.participation_limits.max_attempts_per_user - user.attempts)
            # 实际可能的中奖次数是两者的最小值
            remaining_wins_existing_users += min(remaining_wins, remaining_attempts)
        
        # 计算还没参与用户的中奖次数
        users_not_participated = max(0, self.data.participation_limits.max_total_participants - self.total_participants)
        # 新用户的可能中奖次数也要考虑抽奖次数限制
        max_wins_per_new_user = min(
            self.data.participation_limits.max_wins_per_user,
            self.data.participation_limits.max_attempts_per_user
        )
        remaining_wins_new_users = users_not_participated * max_wins_per_new_user
        
        return remaining_wins_existing_users + remaining_wins_new_users
    
    def _get_available_prizes(self, user_id: str) -> List[Prize]:
        """获取用户可中奖的奖品列表"""
        user_participation = self.participants.get(user_id)
        if not user_participation:
            return []
        
        available_prizes = []
        
        for prize in self.data.prizes:
            # 检查奖品是否还有库存
            if prize.quantity > 0 and prize.remaining_quantity <= 0:
                continue
            
            # 检查用户是否已达该奖品的获得上限
            user_wins_count = user_participation.wins.count(prize.name)
            if user_wins_count >= prize.max_win_per_user:
                continue
                
            available_prizes.append(prize)
        
        return available_prizes
    
    def get_status(self) -> LotteryStatus:
        """获取抽奖状态"""
        now = datetime.now(timezone.utc)
        start_time = datetime.fromisoformat(self.data.start_time.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(self.data.end_time.replace('Z', '+00:00'))
        
        if now < start_time:
            return LotteryStatus.PENDING
        elif now > end_time:
            return LotteryStatus.ENDED
        else:
            return LotteryStatus.ACTIVE
    
    def get_info(self) -> Dict[str, Any]:
        """获取抽奖详细信息"""
        status = self.get_status()
        
        # 计算奖品信息
        prizes_info = []
        for prize in self.data.prizes:
            prize_info = {
                'name': prize.name,
                'description': prize.description,
                'weight': prize.weight,
                'total_quantity': prize.quantity,
                'remaining_quantity': prize.remaining_quantity,
                'distributed': prize.quantity - prize.remaining_quantity if prize.quantity > 0 else 0
            }
            prizes_info.append(prize_info)
        
        return {
            'id': self.id,
            'name': self.data.name,
            'description': self.data.description,
            'status': status.value,
            'start_time': self.data.start_time,
            'end_time': self.data.end_time,
            'total_participants': self.total_participants,
            'total_attempts': self.total_attempts,
            'participation_limits': asdict(self.data.participation_limits),
            'probability_settings': asdict(self.data.probability_settings),
            'prizes': prizes_info,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def get_lottery_by_id(cls, lottery_id: str) -> Optional['Lottery']:
        """根据ID获取抽奖"""
        with cls._lock:
            return cls._lotteries.get(lottery_id)
    
    @classmethod
    def get_lottery_by_name(cls, name: str) -> Optional['Lottery']:
        """根据名称获取抽奖"""
        with cls._lock:
            for lottery in cls._lotteries.values():
                if lottery.data.name == name:
                    return lottery
            return None
    
    @classmethod
    def get_all_lotteries(cls, status_filter: Optional[LotteryStatus] = None, creator_filter: Optional[str] = None) -> List['Lottery']:
        """
        获取所有抽奖
        
        Args:
            status_filter: 可选的状态过滤器，只返回指定状态的抽奖
            creator_filter: 可选的创建者过滤器，只返回指定创建者的抽奖
            
        Returns:
            List['Lottery']: 符合条件的抽奖列表，按创建时间倒序排列
        """
        with cls._lock:
            lotteries = list(cls._lotteries.values())
            
            if status_filter:
                lotteries = [lottery for lottery in lotteries if lottery.get_status() == status_filter]
            
            if creator_filter:
                lotteries = [lottery for lottery in lotteries if lottery.data.creator == creator_filter]
            
            # 按创建时间排序
            lotteries.sort(key=lambda x: x.created_at, reverse=True)
            return lotteries
    
    @classmethod
    def delete_lottery(cls, lottery_id: str) -> bool:
        """删除抽奖"""
        with cls._lock:
            if lottery_id in cls._lotteries:
                del cls._lotteries[lottery_id]
                
                # 从磁盘删除
                if cls._persistence_manager:
                    cls._persistence_manager.delete_lottery(lottery_id)
                
                return True
            return False
    
    def get_user_participation(self, user_id: str) -> Optional[UserParticipation]:
        """获取用户参与信息"""
        return self.participants.get(user_id)
