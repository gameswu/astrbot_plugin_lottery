from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import (
    session_waiter,
    SessionController,
)

from .lottery import Lottery, LotteryStatus, LotteryParseError, LotteryOperationError

@register("lottery", "gameswu", "支持机器人设置抽奖", "0.1")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("Lottery plugin initialized.")

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
{\n
  "name": "",\n
  "description": "",\n
  "start_time": "2025-01-01T00:00:00Z",\n
  "end_time": "2025-12-31T23:59:59Z",\n
  "allowed_groups": [],\n
  "participation_limits": {\n
    "max_total_participants": 1000,\n
    "max_attempts_per_user": 3,\n
    "max_wins_per_user": 1\n
  },\n
  "probability_settings": {\n
    "probability_mode": "exhaust",\n
    "base_probability": 0.2\n
  },\n
  "prizes": [\n
    {\n
      "name": "",\n
      "description": "",\n
      "image_url": "",\n
      "weight": 1,\n
      "quantity": 2,\n
      "max_win_per_user": 1\n
    }\n
  ]\n
}"""

            yield event.plain_result(template)

            @session_waiter(timeout=300, record_history_chains=False)
            async def handle_lottery_info(controller: SessionController, event: AstrMessageEvent):
                """处理用户输入的抽奖信息"""
                info = event.message_str

                try:
                    Lottery.parse_and_create(info)
                    await event.send(event.plain_result("抽奖创建成功"))
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
            lotteries = Lottery.get_all_lotteries(LotteryStatus.ACTIVE)
            if not lotteries:
                await event.send(event.plain_result("当前没有进行中的抽奖。"))
                return
            
            response = "当前进行中的抽奖：\n"
            for lottery in lotteries:
                response += f"- {lottery.data.name}：{lottery.data.description}\n"
            
            await event.send(event.plain_result(response))
        except LotteryOperationError as e:
            logger.error(f"获取抽奖列表失败: {e}")
            await event.send(event.plain_result(f"获取抽奖列表失败：{str(e)}"))
        except Exception as e:
            logger.error(f"列出抽奖失败: {e}")
            await event.send(event.plain_result("列出抽奖失败，请稍后再试。"))

    @lottery.command("lottery", alias={'抽奖'})
    async def lottery_command(self, event: AstrMessageEvent, name: str):
        """抽奖命令处理"""
        try:
            lottery = Lottery.get_lottery_by_name(name=name)
            if not lottery:
                yield event.plain_result(f"未找到名为 '{name}' 的抽奖。")
                return
            
            won, prize, message = lottery.participate(event.get_sender_id())
            
            # 向用户发送抽奖结果
            yield event.plain_result(message)
            
            # 如果中奖了，发送通知到相关群
            if won:
                try:
                    await self.send_notification(event, lottery_name=name, result_message=f"用户 {event.get_sender_id()} 中奖了！奖品：{prize.name if prize else '未知'}") # TODO: 修改result_message
                except Exception as e:
                    logger.error(f"发送中奖通知失败: {e}")
                    
        except LotteryOperationError as e:
            logger.error(f"抽奖操作失败: {e}")
            yield event.plain_result(f"抽奖操作失败：{str(e)}")
        except Exception as e:
            logger.error(f"抽奖命令处理失败: {e}")
            yield event.plain_result("抽奖命令处理失败，请稍后再试。")

    async def send_notification(self, event: AstrMessageEvent, lottery_name: str = None, result_message: str = None): 
        """发送抽奖通知到所有允许的群"""
        if not lottery_name:
            return
            
        try:
            # 获取抽奖信息
            lottery = Lottery.get_lottery_by_name(lottery_name)
            if not lottery or not lottery.data.allowed_groups:
                return
            
            # 构造通知消息
            notification_message = f"🎉 抽奖通知 🎉\n"
            notification_message += f"抽奖名称：{lottery.data.name}\n"
            if result_message:
                notification_message += f"结果：{result_message}\n"
            notification_message += f"描述：{lottery.data.description}"
            
            # 创建消息链
            from astrbot.api.event import MessageChain
            message_chain = MessageChain()
            message_chain.message(notification_message)
            
            # 向所有允许的群发送通知
            for group_id in lottery.data.allowed_groups:
                # 对于QQ平台（aiocqhttp适配器）
                # 群聊session格式：platform_name:GroupMessage:群号
                qq_session = f"aiocqhttp:GroupMessage:{group_id}"
                
                try:
                    success = await self.context.send_message(qq_session, message_chain)
                    if success:
                        logger.info(f"成功向群 {group_id} 发送抽奖通知")
                    else:
                        logger.warning(f"向群 {group_id} 发送通知失败：未找到匹配的平台")
                except Exception as e:
                    logger.error(f"向群 {group_id} 发送通知失败: {e}")
                    
        except LotteryOperationError as e:
            logger.error(f"获取抽奖信息失败: {e}")
        except Exception as e:
            logger.error(f"发送抽奖通知失败: {e}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
