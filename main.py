from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import (
    session_waiter,
    SessionController,
)

from .lottery import Lottery, LotteryStatus, LotteryParseError, LotteryOperationError
from .persistence import get_persistence_manager

@register("lottery", "gameswu", "支持机器人设置抽奖", "0.1.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        # 初始化数据持久化管理器
        self.persistence_manager = None
        self.config = config

        # 是否启用创建抽奖通知
        self.enable_create_notification = self.config.get("enable_create_notification", True)
        # 是否启用结果通知
        self.enable_result_notification = self.config.get("enable_result_notification", True)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        try:
            # 初始化数据持久化管理器
            # 使用插件数据目录作为存储路径
            data_dir = self.context.get_data_dir() if hasattr(self.context, 'get_data_dir') else "data"
            self.persistence_manager = get_persistence_manager(str(data_dir))
            
            # 从持久化存储中加载现有的抽奖数据
            all_lotteries = self.persistence_manager.load_all_lotteries()
            if all_lotteries:
                logger.info(f"成功加载 {len(all_lotteries)} 个抽奖数据")
            else:
                logger.info("未找到现有抽奖数据，从空白状态开始")
            
            logger.info("Lottery plugin initialized successfully.")
        except Exception as e:
            logger.error(f"Lottery plugin initialization failed: {e}")
            # 即使初始化失败，也创建一个默认的持久化管理器
            self.persistence_manager = get_persistence_manager("data")

    @filter.command_group("lottery", alias={'抽奖'})
    async def lottery(self, event: AstrMessageEvent):
       pass

    @lottery.command("create", alias={'创建'})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def create_lottery(self, event: AstrMessageEvent):
        """创建抽奖"""
        try:
            yield event.plain_result("请按照以下模板填入信息并再次发送：")

            # 抽奖配置模板
            template = """
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
}"""

            yield event.plain_result(template)

            @session_waiter(timeout=300, record_history_chains=False)
            async def handle_lottery_info(controller: SessionController, event: AstrMessageEvent):
                """处理用户输入的抽奖信息"""
                info = event.message_str

                try:
                    lottery = Lottery.parse_and_create(info, creator=event.get_sender_id())
                    # 使用持久化管理器保存抽奖数据
                    if self.persistence_manager and self.persistence_manager.save_lottery(lottery):
                        await event.send(event.plain_result(f"抽奖 '{lottery.data.name}' 创建并保存成功！"))
                        logger.info(f"成功创建并保存抽奖: {lottery.data.name} (ID: {lottery.id})")
                        
                        # 如果启用创建抽奖通知，向参与群聊发布创建信息
                        if self.enable_create_notification and lottery.data.allowed_groups:
                            try:
                                # 构建富媒体消息链
                                chain = [
                                    Comp.Plain("🎉 新抽奖活动 🎉\n"),
                                    Comp.Plain(f"{lottery.data.name}\n"),
                                    Comp.Plain(f"描述：{lottery.data.description}\n"),
                                    Comp.Plain(f"活动时间：{lottery.data.start_time} ~ {lottery.data.end_time}\n"),
                                    Comp.Plain("奖品信息：\n")
                                ]
                                
                                # 添加奖品信息和图片
                                for i, prize in enumerate(lottery.data.prizes, 1):
                                    chain.append(Comp.Plain(f"  {i}. {prize.name} - {prize.description}\n"))
                                    if prize.image_url and prize.image_url.strip():
                                        try:
                                            chain.append(Comp.Image.fromURL(prize.image_url))
                                        except Exception as img_e:
                                            logger.warning(f"加载奖品图片失败: {prize.image_url}, 错误: {img_e}")
                                            chain.append(Comp.Plain(f"    [图片加载失败: {prize.image_url}]\n"))
                                
                                chain.append(Comp.Plain(f"\n使用命令：/抽奖 参与 {lottery.data.name}"))
                                
                                await self.send_notification(lottery, chain)
                                logger.info(f"已发送抽奖创建通知: {lottery.data.name}")
                            except Exception as e:
                                logger.error(f"发送创建通知失败: {e}")
                    else:
                        await event.send(event.plain_result(f"抽奖 '{lottery.data.name}' 创建成功，但保存失败！"))
                        logger.warning(f"抽奖创建成功但保存失败: {lottery.data.name}")
                    controller.stop()
                except LotteryParseError as e:
                    logger.error(f"抽奖信息解析失败: {e}")
                    await event.send(event.plain_result(f"抽奖信息解析失败：{str(e)}"))
                    controller.stop()
                except Exception as e:
                    logger.error(f"创建抽奖时发生未知错误: {e}")
                    await event.send(event.plain_result("创建抽奖时发生未知错误，请检查格式或联系管理员。"))
                    controller.stop()

            try:
                await handle_lottery_info(event)
            except TimeoutError:
                await event.send(event.plain_result("抽奖信息输入超时，请重新创建抽奖。"))
                return
            finally:
                event.stop_event()
        except Exception as e:
            logger.error(f"创建抽奖失败: {e}")

    @lottery.command("list", alias={'列表'})
    async def list_lotteries(self, event: AstrMessageEvent):
        """列出所有抽奖"""
        try:
            # 从持久化存储中获取所有抽奖
            if not self.persistence_manager:
                await event.send(event.plain_result("数据管理器未初始化，无法获取抽奖列表。"))
                return
            
            all_lotteries = self.persistence_manager.load_all_lotteries()
            if not all_lotteries:
                await event.send(event.plain_result("当前没有任何抽奖。"))
                return
            
            # 筛选活跃状态的抽奖
            active_lotteries = []
            for lottery in all_lotteries.values():
                if lottery.get_status() == LotteryStatus.ACTIVE:
                    active_lotteries.append(lottery)
            
            if not active_lotteries:
                await event.send(event.plain_result("当前没有进行中的抽奖。"))
                return
            
            response = "当前进行中的抽奖：\n"
            for lottery in active_lotteries:
                response += f"- {lottery.data.name}：{lottery.data.description}\n"
                response += f"  ID: {lottery.id}\n"
                response += f"  参与人数: {lottery.total_participants}\n\n"
            
            await event.send(event.plain_result(response))
        except LotteryOperationError as e:
            logger.error(f"获取抽奖列表失败: {e}")
            await event.send(event.plain_result(f"获取抽奖列表失败：{str(e)}"))
        except Exception as e:
            logger.error(f"列出抽奖失败: {e}")
            await event.send(event.plain_result("列出抽奖失败，请稍后再试。"))

    @lottery.command("participate", alias={'参与', '抽奖'})
    async def lottery_command(self, event: AstrMessageEvent, name: str):
        """抽奖命令处理"""
        try:
            if not self.persistence_manager:
                yield event.plain_result("数据管理器未初始化，无法参与抽奖。")
                return
            
            # 从持久化存储中查找抽奖
            all_lotteries = self.persistence_manager.load_all_lotteries()
            lottery = None
            for lot in all_lotteries.values():
                if lot.data.name == name:
                    lottery = lot
                    break
            
            if not lottery:
                yield event.plain_result(f"未找到名为 '{name}' 的抽奖。")
                return
            
            won, prize, message = lottery.participate(event.get_sender_id())
            
            # 保存更新后的抽奖数据
            if not self.persistence_manager.save_lottery(lottery):
                logger.warning(f"抽奖数据保存失败: {lottery.id}")
            
            # 向用户发送抽奖结果
            yield event.plain_result(message)
            
            # 如果中奖了且启用结果通知，发送通知到相关群
            if won and self.enable_result_notification:
                try:
                    user_id = event.get_sender_id()
                    # 构建富媒体中奖通知消息链
                    chain = [
                        Comp.Plain("🎊 中奖通知 🎊\n"),
                        Comp.Plain(f"抽奖名称：{lottery.data.name}\n"),
                        Comp.Plain(f"中奖用户：{user_id}\n"),
                        Comp.Plain(f"获得奖品：{prize.name if prize else '未知'}\n")
                    ]
                    
                    if prize:
                        chain.append(Comp.Plain(f"奖品描述：{prize.description}\n"))
                        # 如果奖品有图片，添加图片
                        if prize.image_url and prize.image_url.strip():
                            try:
                                chain.append(Comp.Image.fromURL(prize.image_url))
                            except Exception as img_e:
                                logger.warning(f"加载中奖奖品图片失败: {prize.image_url}, 错误: {img_e}")
                                chain.append(Comp.Plain(f"[奖品图片: {prize.image_url}]\n"))
                    
                    chain.append(Comp.Plain("恭喜中奖！🎉"))
                    
                    await self.send_notification(lottery, chain)
                    logger.info(f"已发送中奖通知: {user_id} 在 {lottery.data.name} 中获得 {prize.name if prize else '未知奖品'}")
                except Exception as e:
                    logger.error(f"发送中奖通知失败: {e}")
                    
        except LotteryOperationError as e:
            logger.error(f"抽奖操作失败: {e}")
            yield event.plain_result(f"抽奖操作失败：{str(e)}")
        except Exception as e:
            logger.error(f"抽奖命令处理失败: {e}")
            yield event.plain_result("抽奖命令处理失败，请稍后再试。")

    async def send_notification(self, lottery: Lottery, message_chain_components): 
        """发送抽奖通知到所有允许的群"""
        if not lottery or not lottery.data.allowed_groups or not message_chain_components:
            return
            
        try:
            # 向所有允许的群发送通知
            for group_id in lottery.data.allowed_groups:
                # 对于QQ平台（aiocqhttp适配器）
                # 群聊session格式：platform_name:GroupMessage:群号
                qq_session = f"aiocqhttp:GroupMessage:{group_id}"
                
                try:
                    success = await self.context.send_message(qq_session, message_chain_components)
                    if success:
                        logger.info(f"成功向群 {group_id} 发送抽奖通知")
                    else:
                        logger.warning(f"向群 {group_id} 发送通知失败：未找到匹配的平台")
                except Exception as e:
                    logger.error(f"向群 {group_id} 发送通知失败: {e}")
                    
        except Exception as e:
            logger.error(f"发送抽奖通知失败: {e}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        self.context = None
        self.persistence_manager = None
        logger.info("Lottery plugin terminated successfully.")