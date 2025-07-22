from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult, MessageChain
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

        # 是否启用创建抽奖广播
        self.enable_create_notification = self.config.get("enable_create_notification", True)
        # 是否启用用户中奖广播
        self.enable_result_notification = self.config.get("enable_result_notification", True)
        # 是否启用最终结果广播
        self.enable_draw_notification = self.config.get("enable_draw_notification", True) # TODO: 定时广播目前未实现

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        try:
            # 初始化数据持久化管理器
            # 使用插件数据目录作为存储路径
            data_dir = self.context.get_data_dir() if hasattr(self.context, 'get_data_dir') else "data"
            self.persistence_manager = get_persistence_manager(str(data_dir))
            
            # 设置 Lottery 类的持久化管理器
            Lottery.set_persistence_manager(self.persistence_manager)
            Lottery.enable_auto_save(True)
            
            # 从持久化存储中加载现有的抽奖数据到 Lottery 类
            all_lotteries = self.persistence_manager.load_all_lotteries()
            if all_lotteries:
                # 将加载的数据同步到 Lottery 类的内存存储中
                for lottery_id, lottery in all_lotteries.items():
                    Lottery._lotteries[lottery_id] = lottery
                logger.info(f"成功加载 {len(all_lotteries)} 个抽奖数据到内存")
            else:
                logger.info("未找到现有抽奖数据，从空白状态开始")
            
            logger.info("Lottery plugin initialized successfully.")
        except Exception as e:
            logger.error(f"Lottery plugin initialization failed: {e}")
            # 即使初始化失败，也创建一个默认的持久化管理器
            self.persistence_manager = get_persistence_manager("data")
            Lottery.set_persistence_manager(self.persistence_manager)

    @filter.command_group("lottery", alias={'抽奖'})
    async def lottery(self, event: AstrMessageEvent):
       pass

    @lottery.command("create", alias={'创建'})
    async def create_lottery(self, event: AstrMessageEvent):
        """创建抽奖"""
        try:
            await event.send(MessageChain().message("请按照以下模板填入信息并再次发送："))

            # 抽奖配置模板
            template = (
                "{\n"
                "  \"name\": \"\",\n"
                "  \"description\": \"\",\n"
                "  \"start_time\": \"2025-01-01T00:00:00Z\",\n"
                "  \"end_time\": \"2025-12-31T23:59:59Z\",\n"
                "  \"allowed_groups\": [],\n"
                "  \"participation_limits\": {\n"
                "    \"max_total_participants\": 1000,\n"
                "    \"max_attempts_per_user\": 3,\n"
                "    \"max_wins_per_user\": 1\n"
                "  },\n"
                "  \"probability_settings\": {\n"
                "    \"probability_mode\": \"exhaust\",\n"
                "    \"base_probability\": 0.2\n"
                "  },\n"
                "  \"prizes\": [\n"
                "    {\n"
                "      \"name\": \"\",\n"
                "      \"description\": \"\",\n"
                "      \"image_url\": \"\",\n"
                "      \"weight\": 1,\n"
                "      \"quantity\": 2,\n"
                "      \"max_win_per_user\": 1\n"
                "    }\n"
                "  ]\n"
                "}"
            )

            await event.send(MessageChain().message(template))

            @session_waiter(timeout=600, record_history_chains=False) # 设置超时时间为10分钟
            async def handle_lottery_info(controller: SessionController, event: AstrMessageEvent):
                """处理用户输入的抽奖信息"""
                info = event.message_str

                try:
                    lottery = Lottery.parse_and_create(info, creator=event.get_sender_id())
                    # 使用持久化管理器保存抽奖数据
                    if self.persistence_manager and self.persistence_manager.save_lottery(lottery):
                        await event.send(MessageChain().message(f"抽奖 '{lottery.data.name}' 创建并保存成功！"))
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
                                
                                await self.send_notification(lottery, MessageChain(chain))
                                logger.info(f"已发送抽奖创建通知: {lottery.data.name}")
                            except Exception as e:
                                logger.error(f"发送创建通知失败: {e}")
                    else:
                        await event.send(MessageChain().message(f"抽奖 '{lottery.data.name}' 创建成功，但保存失败！"))
                        logger.warning(f"抽奖创建成功但保存失败: {lottery.data.name}")
                    controller.stop()
                except LotteryParseError as e:
                    logger.error(f"抽奖信息解析失败: {e}")
                    await event.send(MessageChain().message(f"抽奖信息解析失败：{str(e)}"))
                    controller.stop()
                except Exception as e:
                    logger.error(f"创建抽奖时发生未知错误: {e}")
                    await event.send(MessageChain().message("创建抽奖时发生未知错误，请检查格式或联系管理员。"))
                    controller.stop()

            try:
                await handle_lottery_info(event)
            except TimeoutError:
                await event.send(MessageChain().message("抽奖信息输入超时，请重新创建抽奖。"))
                return
            finally:
                event.stop_event()
        except Exception as e:
            logger.error(f"创建抽奖失败: {e}")

    @lottery.command("list", alias={'列表'})
    async def list_lotteries(self, event: AstrMessageEvent):
        """列出所有抽奖"""
        try:
            # 使用 Lottery 类方法获取活跃状态的抽奖
            active_lotteries = Lottery.get_all_lotteries(status_filter=LotteryStatus.ACTIVE)
            
            if not active_lotteries:
                await event.send(MessageChain().message("当前没有进行中的抽奖。"))
                return
            
            chain = [Comp.Plain("当前进行中的抽奖：\n\n")]
            for lottery in active_lotteries:
                chain.extend([
                    Comp.Plain(f"- {lottery.data.name}：{lottery.data.description}\n"),
                    Comp.Plain(f"  ID: {lottery.id}\n"),
                    Comp.Plain(f"  参与人数: {lottery.total_participants}\n")
                ])
                
                # 如果抽奖有图片，添加缩略图
                if hasattr(lottery.data, 'image_url') and lottery.data.image_url and lottery.data.image_url.strip():
                    try:
                        chain.append(Comp.Image.fromURL(lottery.data.image_url))
                    except Exception as img_e:
                        logger.warning(f"加载抽奖缩略图失败: {lottery.data.image_url}, 错误: {img_e}")
                        chain.append(Comp.Plain(f"  [抽奖图片: {lottery.data.image_url}]\n"))
                
                chain.append(Comp.Plain("\n"))
            
            await event.send(MessageChain(chain))
        except LotteryOperationError as e:
            logger.error(f"获取抽奖列表失败: {e}")
            await event.send(MessageChain().message(f"获取抽奖列表失败：{str(e)}"))
        except Exception as e:
            logger.error(f"列出抽奖失败: {e}")
            await event.send(MessageChain().message("列出抽奖失败，请稍后再试。"))

    @lottery.command("participate", alias={'参与', '抽奖'})
    async def lottery_command(self, event: AstrMessageEvent, name: str):
        """抽奖命令处理"""
        try:
            # 使用 Lottery 类方法查找抽奖
            lottery = Lottery.get_lottery_by_name(name)
            if not lottery:
                await event.send(MessageChain().message(f"未找到名为 '{name}' 的抽奖。"))
                return
            
            won, prize, message = lottery.participate(event.get_sender_id())
            
            # 构建抽奖结果消息链
            result_chain = [Comp.Plain(message)]
            
            # 如果中奖且有奖品图片，添加奖品图片
            if won and prize and prize.image_url and prize.image_url.strip():
                try:
                    result_chain.append(Comp.Image.fromURL(prize.image_url))
                except Exception as img_e:
                    logger.warning(f"加载中奖奖品图片失败: {prize.image_url}, 错误: {img_e}")
                    result_chain.append(Comp.Plain(f"\n[奖品图片: {prize.image_url}]"))
            
            # 向用户发送抽奖结果
            await event.send(MessageChain(result_chain))
            
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
                    
                    await self.send_notification(lottery, MessageChain(chain))
                    logger.info(f"已发送中奖通知: {user_id} 在 {lottery.data.name} 中获得 {prize.name if prize else '未知奖品'}")
                except Exception as e:
                    logger.error(f"发送中奖通知失败: {e}")
                    
        except LotteryOperationError as e:
            logger.error(f"抽奖操作失败: {e}")
            await event.send(MessageChain().message(f"抽奖操作失败：{str(e)}"))
        except Exception as e:
            logger.error(f"抽奖命令处理失败: {e}")
            await event.send(MessageChain().message("抽奖命令处理失败，请稍后再试。"))

    @lottery.command("info", alias={'信息'})
    async def lottery_info(self, event: AstrMessageEvent, name: str = None):
        """查询当前用户创建的抽奖信息"""
        try:
            user_id = event.get_sender_id()
            
            # 如果指定了抽奖名称，查询特定抽奖
            if name:
                target_lottery = Lottery.get_lottery_by_name(name)
                
                if not target_lottery or target_lottery.data.creator != user_id:
                    await event.send(MessageChain().message(f"未找到您创建的名为 '{name}' 的抽奖。"))
                    return
                
                # 构建详细信息消息链
                info_chain = self._build_lottery_detail_chain(target_lottery)
                await event.send(MessageChain(info_chain))
                
            else:
                # 没有指定名称，返回用户创建的所有抽奖
                user_lotteries = Lottery.get_all_lotteries(creator_filter=user_id)
                
                if not user_lotteries:
                    await event.send(MessageChain().message("您还没有创建任何抽奖。"))
                    return
                
                # 构建抽奖列表消息链
                chain = [Comp.Plain(f"您创建的抽奖列表 (共 {len(user_lotteries)} 个)：\n\n")]
                
                for lottery in user_lotteries:
                    status = lottery.get_status()
                    status_text = {
                        LotteryStatus.PENDING: "未开始",
                        LotteryStatus.ACTIVE: "进行中",
                        LotteryStatus.ENDED: "已结束",
                    }.get(status, "未知")
                    
                    chain.extend([
                        Comp.Plain(f"📊 {lottery.data.name}\n"),
                        Comp.Plain(f"   状态：{status_text}\n"),
                        Comp.Plain(f"   描述：{lottery.data.description}\n"),
                        Comp.Plain(f"   参与人数：{lottery.total_participants}\n"),
                        Comp.Plain(f"   抽奖次数：{lottery.total_attempts}\n"),
                        Comp.Plain(f"   创建时间：{lottery.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"),
                        Comp.Plain(f"   ID：{lottery.id}\n")
                    ])
                    
                    chain.append(Comp.Plain("\n"))
                
                chain.append(Comp.Plain("使用 '/抽奖 信息 <抽奖名称>' 查看详细信息"))
                await event.send(MessageChain(chain))
                
        except Exception as e:
            logger.error(f"获取抽奖信息失败: {e}")
            await event.send(MessageChain().message("获取抽奖信息失败，请稍后再试。"))

    @lottery.command("admin", alias={'管理'})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def admin_lottery(self, event: AstrMessageEvent, operator: str, name: str = None):
        """管理员管理抽奖"""
        try:
            user_id = event.get_sender_id()
            if not self.context.is_admin(user_id):
                await event.send(MessageChain().message("您没有权限执行此操作。"))
                return
            
            if operator == "list":
                # 列出所有抽奖
                lotteries = Lottery.get_all_lotteries()
                if not lotteries:
                    await event.send(MessageChain().message("当前没有任何抽奖。"))
                    return
                
                chain = [Comp.Plain("所有抽奖列表：\n\n")]
                for lottery in lotteries:
                    chain.extend([
                        Comp.Plain(f"- {lottery.data.name} (ID: {lottery.id})\n"),
                        Comp.Plain(f"  状态：{lottery.get_status().name}\n"),
                        Comp.Plain(f"  创建者：{lottery.data.creator}\n")
                    ])
                
                await event.send(MessageChain(chain))
            
            elif operator == "info":
                # 查询特定抽奖信息
                if not name:
                    await event.send(MessageChain().message("请提供抽奖名称。"))
                    return
                
                lottery = Lottery.get_lottery_by_name(name)
                if not lottery:
                    await event.send(MessageChain().message(f"未找到名为 '{name}' 的抽奖。"))
                    return
                
                info_chain = self._build_lottery_detail_chain(lottery)
                await event.send(MessageChain(info_chain))

            elif operator == "start":
                # 开始抽奖
                if not name:
                    await event.send(MessageChain().message("请提供要开始的抽奖名称。"))
                    return
                
                lottery = Lottery.get_lottery_by_name(name)
                if not lottery:
                    await event.send(MessageChain().message(f"未找到名为 '{name}' 的抽奖。"))
                    return

                lottery.start_lottery()
                await event.send(MessageChain().message(f"抽奖 '{name}' 已成功开始！"))

            elif operator == "end":
                # 结束抽奖
                if not name:
                    await event.send(MessageChain().message("请提供要结束的抽奖名称。"))
                    return
                
                lottery = Lottery.get_lottery_by_name(name)
                if not lottery:
                    await event.send(MessageChain().message(f"未找到名为 '{name}' 的抽奖。"))
                    return

                lottery.cancel_lottery()
                await event.send(MessageChain().message(f"抽奖 '{name}' 已成功取消！"))

            elif operator == "delete":
                if not name:
                    await event.send(MessageChain().message("请提供要删除的抽奖名称。"))
                    return
                
                lottery = Lottery.get_lottery_by_name(name)
                if not lottery:
                    await event.send(MessageChain().message(f"未找到名为 '{name}' 的抽奖。"))
                    return
                
                lottery_id = lottery.id
                success = Lottery.delete_lottery(lottery_id)
                if success:
                    await event.send(MessageChain().message(f"抽奖 '{name}' 已成功删除！"))
                    logger.info(f"管理员 {user_id} 删除了抽奖: {name} (ID: {lottery_id})")
                else:
                    await event.send(MessageChain().message(f"删除抽奖 '{name}' 失败。"))
                logger.error(f"管理员 {user_id} 删除抽奖失败: {name} (ID: {lottery_id})")

            else:
                await event.send(MessageChain().message("未知的管理员操作"))
        
        except Exception as e:
            logger.error(f"管理员操作失败: {e}")
            await event.send(MessageChain().message("管理员操作失败，请稍后再试。"))

    @lottery.command("help", alias={'帮助'})
    async def lottery_help(self, event: AstrMessageEvent):
        """显示抽奖帮助信息"""
        help_message = (
            "抽奖命令帮助：\n"
            "/抽奖 创建 - 创建新的抽奖\n"
            "/抽奖 列表 - 列出所有进行中的抽奖\n"
            "/抽奖 参与 [抽奖名称] - 参与指定的抽奖\n"
            "/抽奖 信息 <抽奖名称> - 查看当前用户创建的抽奖信息\n"
            "/抽奖 管理 [操作] <参数> - 管理员操作，支持 list/info/start/end/delete\n"
            "管理员操作需要权限，请联系管理员获取更多帮助。"
        )
        await event.send(MessageChain().message(help_message))

    async def send_notification(self, lottery: Lottery, message_chain): 
        """发送抽奖通知到所有允许的群"""
        
        if not lottery or not lottery.data.allowed_groups or not message_chain:
            return
            
        try:
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
                    
        except Exception as e:
            logger.error(f"发送抽奖通知失败: {e}")

    def _build_lottery_detail_chain(self, lottery: Lottery) -> list:
        """构建抽奖详细信息的消息链"""
        status = lottery.get_status()
        status_text = {
            LotteryStatus.PENDING: "未开始",
            LotteryStatus.ACTIVE: "进行中",
            LotteryStatus.ENDED: "已结束"
        }.get(status, "未知")
        
        chain = [
            Comp.Plain("抽奖详细信息\n"),
            Comp.Plain("━━━━━━━━━━━━━━━━━━━━\n"),
            Comp.Plain(f"名称：{lottery.data.name}\n"),
            Comp.Plain(f"描述：{lottery.data.description}\n"),
            Comp.Plain(f"状态：{status_text}\n"),
            Comp.Plain(f"开始时间：{lottery.data.start_time}\n"),
            Comp.Plain(f"结束时间：{lottery.data.end_time}\n"),
            Comp.Plain(f"参与人数：{lottery.total_participants}\n"),
            Comp.Plain(f"抽奖次数：{lottery.total_attempts}\n"),
            Comp.Plain(f"创建时间：{lottery.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"),
            Comp.Plain(f"创建者：{lottery.data.creator}\n"),
            Comp.Plain(f"抽奖ID：{lottery.id}\n")
        ]
        
        # 参与限制信息
        limits = lottery.data.participation_limits
        chain.extend([
            Comp.Plain("⚙️ 参与限制：\n"),
            Comp.Plain(f"   最大参与人数：{limits.max_total_participants if limits.max_total_participants > 0 else '无限制'}\n"),
            Comp.Plain(f"   每人最大抽奖次数：{limits.max_attempts_per_user if limits.max_attempts_per_user > 0 else '无限制'}\n"),
            Comp.Plain(f"   每人最大中奖次数：{limits.max_wins_per_user if limits.max_wins_per_user > 0 else '无限制'}\n\n")
        ])
        
        # 概率设置信息
        prob = lottery.data.probability_settings
        mode_text = {
            "fixed": "固定概率",
            "dynamic": "动态概率",
            "exhaust": "抽完即止"
        }.get(prob.probability_mode, "未知")
        chain.extend([
            Comp.Plain("🎲 概率设置：\n"),
            Comp.Plain(f"   模式：{mode_text}\n"),
            Comp.Plain(f"   基础概率：{prob.base_probability:.2%}\n\n")
        ])
        
        # 奖品信息
        chain.append(Comp.Plain(f"🏆 奖品列表 (共 {len(lottery.data.prizes)} 个)：\n"))
        for i, prize in enumerate(lottery.data.prizes, 1):
            remaining = prize.remaining_quantity if prize.remaining_quantity is not None else prize.quantity
            total = prize.quantity if prize.quantity > 0 else "无限"
            chain.extend([
                Comp.Plain(f"   {i}. {prize.name}\n"),
                Comp.Plain(f"      描述：{prize.description}\n"),
                Comp.Plain(f"      权重：{prize.weight}\n"),
                Comp.Plain(f"      剩余/总数：{remaining}/{total}\n"),
                Comp.Plain(f"      每人限制：{prize.max_win_per_user}\n")
            ])
            
            # 如果奖品有图片，添加图片
            if prize.image_url and prize.image_url.strip():
                try:
                    chain.append(Comp.Image.fromURL(prize.image_url))
                except Exception as img_e:
                    logger.warning(f"加载奖品图片失败: {prize.image_url}, 错误: {img_e}")
                    chain.append(Comp.Plain(f"      [奖品图片: {prize.image_url}]\n"))
            
            chain.append(Comp.Plain("\n"))
        
        # 允许的群聊
        if lottery.data.allowed_groups:
            chain.append(Comp.Plain(f"📢 允许的群聊：{', '.join(lottery.data.allowed_groups)}\n"))
        else:
            chain.append(Comp.Plain("📢 允许的群聊：未设置\n"))
        
        return chain

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        self.context = None
        self.persistence_manager = None
        logger.info("Lottery plugin terminated successfully.")