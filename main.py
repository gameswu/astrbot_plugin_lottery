from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import (
    session_waiter,
    SessionController,
)

from .lottery import Lottery

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
    async def create_lottery(self, event: AstrMessageEvent):
        """创建抽奖"""
        try:
            yield event.plain_result("请按照以下模板填入信息并再次发送：")
            yield event.plain_result("") # TODO: 填入抽奖信息模板

            @session_waiter(timeout=300, record_history_chains=False)
            async def handle_lottery_info(controller: SessionController, event: AstrMessageEvent):
                """处理用户输入的抽奖信息"""
                info = event.message_str

                try:
                    pass # TODO: 解析函数
                except Exception as e:
                    logger.error(f"抽奖信息解析失败: {e}")
                    await event.send(event.plain_result("抽奖信息解析失败，请检查格式。")) # TODO: 可以返回解析函数的错误信息
                    controller.stop()

            try:
                await handle_lottery_info(event) # TODO: 可能需要修改
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
            lotteries = Lottery.get_all()  # TODO: 改为实际的获取方法
            if not lotteries:
                await event.send(event.plain_result("当前没有进行中的抽奖。"))
                return
            
            response = "当前进行中的抽奖：\n"
            for lottery in lotteries:
                response += f"- {lottery.name} (ID: {lottery.id})\n"  # TODO: 改为实际的抽奖信息格式
            
            await event.send(event.plain_result(response))
        except Exception as e:
            logger.error(f"列出抽奖失败: {e}")
            await event.send(event.plain_result("列出抽奖失败，请稍后再试。"))

    @filter.command("lottery", alias={'抽奖'})
    async def lottery_command(self, event: AstrMessageEvent, name: str):
        """抽奖命令处理"""
        try:
            lottery = Lottery.get_by_name(name)  # TODO: 改为实际的获取方法
            if not lottery:
                yield event.plain_result(f"未找到名为 '{name}' 的抽奖。")
            
            await lottery.start(event)  # TODO: 改为实际的抽奖开始方法
        except Exception as e:
            logger.error(f"抽奖命令处理失败: {e}")
            yield event.plain_result("抽奖命令处理失败，请稍后再试。")
        
        try:
            await self.send_notification(event, lottery)  # TODO: 实现通知发送方法
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            await event.send(event.plain_result("发送通知失败，请稍后再试。"))

    async def send_notification(self, event: AstrMessageEvent, lottery): # TODO: 按实际情况修改
        """发送抽奖通知"""
        try:
            await event.send(event.plain_result(f"抽奖 '{lottery.name}' 已开始！"))
        except Exception as e:
            logger.error(f"发送抽奖通知失败: {e}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
