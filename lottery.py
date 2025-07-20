# 奖品类
class Prize:
    id: int  # 奖品的唯一ID
    name: str  # 奖品名称
    description: str  # 奖品描述
    image_url: str  # 奖品图片URL

    def __init__(self, id: int, name: str, description: str, image_url: str):
        self.id = id
        self.name = name
        self.description = description
        self.image_url = image_url

# 抽奖类
class Lottery:
    creater_id: str  # 抽奖创建者的ID
    id: str  # 抽奖的唯一ID（也作为显示的标题）
    description: str  # 抽奖的描述
    prize_num: int  # 奖品数量
    prizes: list[Prize]  # 奖品列表
    algorithm_id: str = "default"  # 抽奖算法ID，默认为"default"

    def __init__(self, creater_id: str, id: str, description: str, prize_num: int):
        self.creater_id = creater_id
        self.id = id
        self.description = description
        self.prize_num = prize_num

        # 初始化奖品列表，分别分配id从1到prize_num
        self.prizes = []
        for i in range(1, prize_num + 1):
            prize = Prize(
                id=i,
                name=f"奖品{i}",
                description=f"这是第{i}个奖品",
                image_url=""
            )
            self.prizes.append(prize)

    def set_prize(self, id: int, name: str, description: str, image_url: str):
        try:
            prize = self.prizes[id - 1]  # id从1开始，所以需要减1
            prize.name = name
            prize.description = description
            prize.image_url = image_url
        except IndexError:
            raise ValueError(f"奖品ID {id} 不存在。请确保ID在1到{self.prize_num}之间。")


# 导入算法装饰器和配置类
from algorithm_lot import lottery_algorithm, LotteryConfig

# 使用装饰器的高级抽奖类示例
@lottery_algorithm("random", LotteryConfig(
    prize_limit=None,  # 不限制奖品数量
    user_draw_limit=5,  # 每个用户最多抽奖5次
    allow_duplicate=True  # 允许重复中奖
))
class AdvancedLottery(Lottery):
    """使用算法装饰器的高级抽奖类"""
    
    def __init__(self, creater_id: str, id: str, description: str, prize_num: int):
        super().__init__(creater_id, id, description, prize_num)


# 加权抽奖类示例
@lottery_algorithm("weighted", LotteryConfig(
    prize_limit=10,  # 每个奖品最多被抽取10次
    user_draw_limit=3,  # 每个用户最多抽奖3次
    allow_duplicate=False  # 不允许重复中奖
))
class WeightedLottery(Lottery):
    """使用加权算法的抽奖类"""
    
    def __init__(self, creater_id: str, id: str, description: str, prize_num: int, weights: dict = None):
        super().__init__(creater_id, id, description, prize_num)
        # 如果提供了权重，设置给算法
        if weights and hasattr(self, 'algorithm_instance'):
            self.algorithm_instance.weights = weights
        
