"""Built-in knowledge for the first judgement, before the software knows the person.

Only words that almost every student would place the same way. Anything that depends on the
person — 奶茶, 咖啡, 书, 耳机, 健身 — is deliberately *not* given a category: it is listed as
AMBIGUOUS so that built-in knowledge never decides a text that names it; the person's own
labels can. The person's own phrases always win over these words (see classification.py).

Matching is by longest phrase over tokens (CJK characters one by one, Latin/digit runs as
words), so 电影票 beats 电影, 面包板 beats 面包, and 'gpt' never matches inside 'chatgpt'.
Before adding words, measure with scripts/classification_benchmark.py (see
docs/development/CLASSIFICATION.md §4–§5).
"""

TERMS = {
    "生活": """
        饭 早饭 早餐 午饭 午餐 中饭 晚饭 晚餐 夜宵 宵夜 正餐 便当 快餐 盒饭 食堂 饭堂 饭卡 校园卡
        外卖 美团外卖 饿了么 点餐 堂食 米饭 炒饭 盖饭 盖浇饭 拌饭 炒面 拉面 面条 米线 米粉 粉面 馄饨 饺子 包子 馒头
        豆浆 油条 煎饼 粥 麻辣烫 麻辣香锅 冒菜 黄焖鸡 烧烤 烤串 火锅 串串 螺蛳粉 酸辣粉 小吃 沙县 汉堡 炸鸡
        肯德基 kfc 麦当劳 汉堡王 必胜客 德克士 华莱士 塔斯汀 萨莉亚 海底捞
        菜 买菜 蔬菜 肉 鸡蛋 大米 食用油 调料 水果 苹果 香蕉 西瓜 橘子 葡萄 草莓
        超市 便利店 全家 罗森 美宜佳 盒马 叮咚买菜 朴朴 永辉 沃尔玛
        矿泉水 纯净水 桶装水 买水 饮料 可乐 雪碧 牛奶 酸奶 面包 泡面 方便面
        地铁 公交 公交卡 地铁卡 打车 滴滴 出租车 网约车 高德打车 共享单车 哈啰 青桔 单车 高铁 火车 火车票 动车 12306
        车票 车费 路费 加油 停车
        房租 租房 物业 水费 电费 水电 燃气 煤气 话费 流量 充话费
        日用品 纸巾 卫生纸 抽纸 湿巾 洗衣液 洗衣粉 洗衣 洗发水 沐浴露 牙膏 牙刷 毛巾 香皂 洗洁精 垃圾袋 衣架 拖把 雨伞
        理发 剪头发 洗剪吹 衣服 上衣 t恤 衬衫 裤子 外套 羽绒服 袜子 内衣 鞋 运动鞋 拖鞋 球鞋
        药 药店 药房 感冒药 创可贴 医院 挂号 看病 门诊 体检 牙医 看牙 校医院 口罩 皮肤科
        快递 快递费 寄快递 顺丰 邮费 运费
        面膜 洗面奶 蛋白粉
    """,
    "工具": """
        chatgpt gpt openai claude cursor copilot github gemini kimi
        icloud 网盘 百度网盘 阿里云盘 云盘 云服务器 服务器 阿里云 腾讯云 域名 vps
        打印 复印 扫描 打印店 文具 中性笔 笔芯 钢笔 铅笔 橡皮 本子 笔记本 草稿纸 便利贴 文件夹 订书机 胶带
        教材 课本 教辅 习题 习题册 练习册 专业书 考研 网课 课程 报名费 四六级 雅思 托福 考试 学费 知网
        键盘 鼠标 鼠标垫 显示器 数据线 充电器 充电头 u盘 硬盘 移动硬盘 充电宝 电脑 笔记本电脑 平板 ipad 电池
        插排 插座 扩展坞 计算器 台灯 面包板 车载充电器
        wps office notion 印象笔记 软件 电脑维修
    """,
    "娱乐": """
        steam epic switch ps5 xbox 游戏 手游 买游戏 游戏充值 原神 王者荣耀 皮肤 月卡 卡带 吃鸡 蒸汽平台
        电影 电影票 看电影 影院 imax 猫眼 淘票票
        视频会员 爱奇艺 腾讯视频 优酷 芒果tv b站 大会员 网易云 qq音乐 spotify netflix 音乐会员
        ktv 唱k 剧本杀 密室 密室逃脱 桌游 狼人杀 演唱会 音乐节 话剧 livehouse 展览 脱口秀 门票 景区
        旅游 旅行 民宿 手办 盲盒 乐高 周边 谷子 漫展 网吧 电玩城 抓娃娃 台球 保龄球 小说 漫画 酒吧 精酿
        卡丁车 碰碰车 过山车 赛车 车模 鱼竿 钓鱼 鸡尾酒 粉丝 应援 扭蛋
    """,
}

# Head characters. Chinese compounds are head-final, so an unseen dish, garment or vehicle
# usually ends in, or is cooked by, one of these (烤冷面, 鸡公煲, 秋裤, 电动车). Longer words
# above always win the match — that is what keeps 吃鸡 a game and 面包板 a tool. 鱼 is left
# out on purpose: 闲鱼, 钓鱼 and 鱼缸 made it wrong too often.
HEADS = {
    "生活": "面 粉 汤 饼 饺 锅 煲 鸭 虾 蟹 鸡 串 卤 烤 炒 炖 焖 蒸 煮 炸 餐 蛋 衣 裤 袜 帽 巾 枕 车",
}

# Words whose category depends on the person. Built-in knowledge never decides a text that
# names one of them; only the person's own phrases can.
AMBIGUOUS = """
    奶茶 咖啡 拿铁 美式 茶 零食 甜品 蛋糕 冰淇淋 雪糕 饼干 薯片 辣条 巧克力
    书 买书 图书 电子书 耳机 音箱 健身 健身房 游泳 球
    礼物 红包 转账 聚餐 请客 酒店 机票 闲鱼 淘宝 京东 拼多多 网购 烟 酒 按摩 宠物 猫粮 书包 驾校
"""

# Matched and consumed, but no evidence either way: 面试 is not a bowl of noodles.
NEUTRAL = "面试 见面 当面"
