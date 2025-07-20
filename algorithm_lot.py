import random
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class LotteryConfig:
    """抽奖配置类"""
    prize_limit: Optional[int] = None  # 奖品数量限制，None表示不限
    user_draw_limit: Optional[int] = None  # 用户抽奖次数限制，None表示不限
    allow_duplicate: bool = True  # 是否允许重复中奖


@dataclass
class LotteryResult:
    """抽奖结果类"""
    user_id: str
    prize_id: Optional[int]  # None表示未中奖
    prize_name: Optional[str] = None
    success: bool = False
    message: str = ""


class LotteryState:
    """抽奖状态管理类"""
    def __init__(self):
        self.prize_draw_count: Dict[int, int] = defaultdict(int)  # 每个奖品的抽取次数
        self.user_draw_count: Dict[str, int] = defaultdict(int)  # 每个用户的抽奖次数
        self.user_prizes: Dict[str, List[int]] = defaultdict(list)  # 用户中奖记录

    def can_user_draw(self, user_id: str, config: LotteryConfig) -> bool:
        """检查用户是否还能抽奖"""
        if config.user_draw_limit is None:
            return True
        return self.user_draw_count[user_id] < config.user_draw_limit

    def can_prize_be_drawn(self, prize_id: int, config: LotteryConfig) -> bool:
        """检查奖品是否还能被抽取"""
        if config.prize_limit is None:
            return True
        return self.prize_draw_count[prize_id] < config.prize_limit

    def record_draw(self, user_id: str, prize_id: Optional[int] = None):
        """记录抽奖结果"""
        self.user_draw_count[user_id] += 1
        if prize_id is not None:
            self.prize_draw_count[prize_id] += 1
            self.user_prizes[user_id].append(prize_id)


class LotteryAlgorithm(ABC):
    """抽奖算法基类"""
    
    def __init__(self, config: LotteryConfig):
        self.config = config
        self.state = LotteryState()
    
    @abstractmethod
    def draw(self, user_id: str, available_prizes: List[Dict]) -> LotteryResult:
        """执行抽奖逻辑"""
        pass
    
    def reset_state(self):
        """重置抽奖状态"""
        self.state = LotteryState()


class RandomLotteryAlgorithm(LotteryAlgorithm):
    """随机抽奖算法"""
    
    def draw(self, user_id: str, available_prizes: List[Dict]) -> LotteryResult:
        # 检查用户是否还能抽奖
        if not self.state.can_user_draw(user_id, self.config):
            return LotteryResult(
                user_id=user_id,
                prize_id=None,
                success=False,
                message=f"您已达到最大抽奖次数限制({self.config.user_draw_limit}次)"
            )
        
        # 过滤可用奖品
        valid_prizes = []
        for prize in available_prizes:
            if self.state.can_prize_be_drawn(prize['id'], self.config):
                # 检查是否允许重复中奖
                if not self.config.allow_duplicate and prize['id'] in self.state.user_prizes[user_id]:
                    continue
                valid_prizes.append(prize)
        
        # 记录抽奖次数
        self.state.record_draw(user_id)
        
        # 如果没有可用奖品
        if not valid_prizes:
            return LotteryResult(
                user_id=user_id,
                prize_id=None,
                success=False,
                message="很遗憾，没有中奖！"
            )
        
        # 随机选择奖品
        selected_prize = random.choice(valid_prizes)
        self.state.record_draw(user_id, selected_prize['id'])
        
        return LotteryResult(
            user_id=user_id,
            prize_id=selected_prize['id'],
            prize_name=selected_prize['name'],
            success=True,
            message=f"恭喜您中奖了！获得: {selected_prize['name']}"
        )


class WeightedLotteryAlgorithm(LotteryAlgorithm):
    """加权抽奖算法"""
    
    def __init__(self, config: LotteryConfig, weights: Dict[int, float] = None):
        super().__init__(config)
        self.weights = weights or {}  # 奖品ID -> 权重
    
    def draw(self, user_id: str, available_prizes: List[Dict]) -> LotteryResult:
        # 检查用户是否还能抽奖
        if not self.state.can_user_draw(user_id, self.config):
            return LotteryResult(
                user_id=user_id,
                prize_id=None,
                success=False,
                message=f"您已达到最大抽奖次数限制({self.config.user_draw_limit}次)"
            )
        
        # 过滤可用奖品
        valid_prizes = []
        weights = []
        
        for prize in available_prizes:
            if self.state.can_prize_be_drawn(prize['id'], self.config):
                # 检查是否允许重复中奖
                if not self.config.allow_duplicate and prize['id'] in self.state.user_prizes[user_id]:
                    continue
                valid_prizes.append(prize)
                weights.append(self.weights.get(prize['id'], 1.0))
        
        # 记录抽奖次数
        self.state.record_draw(user_id)
        
        # 如果没有可用奖品
        if not valid_prizes:
            return LotteryResult(
                user_id=user_id,
                prize_id=None,
                success=False,
                message="很遗憾，没有中奖！"
            )
        
        # 按权重随机选择
        selected_prize = random.choices(valid_prizes, weights=weights, k=1)[0]
        self.state.record_draw(user_id, selected_prize['id'])
        
        return LotteryResult(
            user_id=user_id,
            prize_id=selected_prize['id'],
            prize_name=selected_prize['name'],
            success=True,
            message=f"恭喜您中奖了！获得: {selected_prize['name']}"
        )


# 算法注册表
_algorithm_registry: Dict[str, type] = {}


def register_algorithm(name: str):
    """算法注册装饰器"""
    def decorator(algorithm_class: type) -> type:
        _algorithm_registry[name] = algorithm_class
        return algorithm_class
    return decorator


def get_algorithm(name: str) -> Optional[type]:
    """获取注册的算法类"""
    return _algorithm_registry.get(name)


def list_algorithms() -> List[str]:
    """列出所有注册的算法"""
    return list(_algorithm_registry.keys())


# 抽奖算法装饰器
def lottery_algorithm(algorithm_name: str, config: LotteryConfig = None):
    """抽奖算法装饰器，为抽奖类添加算法支持"""
    def decorator(lottery_class):
        # 保存原始的__init__方法
        original_init = lottery_class.__init__
        
        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            # 调用原始初始化
            original_init(self, *args, **kwargs)
            
            # 添加算法相关属性
            self.algorithm_name = algorithm_name
            self.algorithm_config = config or LotteryConfig()
            self.algorithm_instance = None
            self._initialize_algorithm()
        
        def _initialize_algorithm(self):
            """初始化算法实例"""
            algorithm_class = get_algorithm(self.algorithm_name)
            if algorithm_class is None:
                raise ValueError(f"Unknown algorithm: {self.algorithm_name}")
            self.algorithm_instance = algorithm_class(self.algorithm_config)
        
        def set_algorithm_config(self, config: LotteryConfig):
            """设置算法配置"""
            self.algorithm_config = config
            self._initialize_algorithm()
        
        def set_prize_limit(self, limit: Optional[int]):
            """设置奖品数量限制"""
            self.algorithm_config.prize_limit = limit
            self._initialize_algorithm()
        
        def set_user_draw_limit(self, limit: Optional[int]):
            """设置用户抽奖次数限制"""
            self.algorithm_config.user_draw_limit = limit
            self._initialize_algorithm()
        
        def set_allow_duplicate(self, allow: bool):
            """设置是否允许重复中奖"""
            self.algorithm_config.allow_duplicate = allow
            self._initialize_algorithm()
        
        def draw_prize(self, user_id: str) -> LotteryResult:
            """执行抽奖"""
            if self.algorithm_instance is None:
                raise RuntimeError("Algorithm not initialized")
            
            # 将奖品转换为算法需要的格式
            available_prizes = [
                {
                    'id': prize.id,
                    'name': prize.name,
                    'description': prize.description
                }
                for prize in self.prizes
            ]
            
            return self.algorithm_instance.draw(user_id, available_prizes)
        
        def reset_lottery_state(self):
            """重置抽奖状态"""
            if self.algorithm_instance:
                self.algorithm_instance.reset_state()
        
        def get_lottery_statistics(self) -> Dict[str, Any]:
            """获取抽奖统计信息"""
            if not self.algorithm_instance:
                return {}
            
            state = self.algorithm_instance.state
            return {
                'prize_draw_count': dict(state.prize_draw_count),
                'user_draw_count': dict(state.user_draw_count),
                'user_prizes': dict(state.user_prizes),
                'config': {
                    'prize_limit': self.algorithm_config.prize_limit,
                    'user_draw_limit': self.algorithm_config.user_draw_limit,
                    'allow_duplicate': self.algorithm_config.allow_duplicate
                }
            }
        
        # 添加新方法到类
        lottery_class.__init__ = new_init
        lottery_class._initialize_algorithm = _initialize_algorithm
        lottery_class.set_algorithm_config = set_algorithm_config
        lottery_class.set_prize_limit = set_prize_limit
        lottery_class.set_user_draw_limit = set_user_draw_limit
        lottery_class.set_allow_duplicate = set_allow_duplicate
        lottery_class.draw_prize = draw_prize
        lottery_class.reset_lottery_state = reset_lottery_state
        lottery_class.get_lottery_statistics = get_lottery_statistics
        
        return lottery_class
    
    return decorator


# 注册默认算法
@register_algorithm("random")
class RegisteredRandomAlgorithm(RandomLotteryAlgorithm):
    pass


@register_algorithm("weighted")
class RegisteredWeightedAlgorithm(WeightedLotteryAlgorithm):
    pass