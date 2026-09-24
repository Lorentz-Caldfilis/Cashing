"""Synthetic benchmark for the derived category (classification.py). No real ledger is read.

A "world" of student spending descriptions with frequency weights and per-persona gold labels,
and a simulator of someone using Cashing for 180 days: every record shows the person's label if
they gave one, otherwise the software's current judgement. Once a week they glance at the last
week in Review: a wrong category is fixed with P_FIX, an undecided one labelled with P_LABEL
(undecided is not a task, so this is low). Items whose gold is None must stay undecided.

    python scripts/classification_benchmark.py            # full report (about a minute)

Personas disagree on the genuinely personal things (奶茶, 咖啡, 健身 ...); D additionally
disagrees with the built-in words on three frequent ones. HARD (split DEV / TEST) and FRESH
are long tails written without the lexicon in view; FRESH was written after the rules and
evaluated once before any further change (docs/development/CLASSIFICATION.md).
Everything is deterministic (seeded).
"""
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classification import Classifier  # noqa: E402

L, T, E = "生活", "工具", "娱乐"
DAYS = 180
P_FIX = 0.7
P_LABEL = 0.25
TAIL_SHARE = 0.3        # share of records drawn from the long tail
MODIFY = 0.3            # share of records with a neutral modifier (和室友, x2, 补记 ...)
NEUTRAL = ["和室友", "两份", "x2", "学校", "周末", "楼下", "补记", "顺便", "二楼", "今天", "给自己", "大份",
           "一起", "昨天的", "附近", "三个人", "老地方", "路上"]


def P(a, b, c):
    return {"A": a, "B": b, "C": c}


ITEMS = [
    # ---- meals & food (very frequent) ----
    (9, L, ["午饭", "午餐", "中饭", "食堂午饭", "吃午饭", "午饭 食堂", "二食堂午饭", "午饭+饮料"]),
    (9, L, ["晚饭", "晚餐", "食堂晚饭", "晚饭 麻辣烫", "吃晚饭", "晚饭外卖"]),
    (6, L, ["早饭", "早餐", "包子豆浆", "早饭 煎饼", "早餐 食堂", "肉包"]),
    (3, L, ["夜宵", "宵夜", "夜宵 烧烤", "烧烤"]),
    (4, L, ["外卖", "美团外卖", "饿了么", "点外卖", "外卖 黄焖鸡", "饿了么 午饭"]),
    (2, L, ["麻辣烫", "黄焖鸡米饭", "兰州拉面", "沙县小吃", "螺蛳粉", "麻辣香锅", "盖浇饭", "饺子"]),
    (1.5, L, ["肯德基", "KFC", "麦当劳", "mcdonald's", "汉堡王", "塔斯汀"]),
    (1.5, L, ["食堂", "饭卡充值", "校园卡充值", "充饭卡"]),
    (1, L, ["海底捞", "火锅", "和室友吃火锅", "聚餐 火锅"]),
    (2, L, ["水果", "买水果", "苹果香蕉", "西瓜", "橘子"]),
    (2, L, ["超市", "学校超市", "便利店", "全家", "7-11", "罗森", "美宜佳"]),
    (2, L, ["矿泉水", "水", "饮料", "可乐", "农夫山泉", "买水"]),
    (1, L, ["牛奶", "酸奶", "面包", "泡面", "方便面"]),
    (1, L, ["买菜", "叮咚买菜", "盒马", "朴朴"]),
    # ---- transport ----
    (4, L, ["地铁", "地铁卡充值", "坐地铁", "地铁 2号线"]),
    (2, L, ["公交", "公交卡", "坐公交"]),
    (2, L, ["打车", "滴滴", "滴滴打车", "打车回学校", "出租车", "高德打车"]),
    (1, L, ["共享单车", "哈啰", "美团单车", "青桔", "骑车"]),
    (1, L, ["高铁", "火车票", "12306", "高铁票 回家", "动车"]),
    (0.3, P(L, L, E), ["机票", "飞机票", "机票 回家"]),
    # ---- housing / utilities / telecom ----
    (0.5, L, ["房租", "租房", "押金"]),
    (0.8, L, ["电费", "宿舍电费", "水电费", "充电费"]),
    (1, L, ["话费", "充话费", "手机话费", "流量包", "话费充值"]),
    (0.4, P(L, L, T), ["校园网", "宽带", "网费"]),
    # ---- daily goods, care, clothing, health ----
    (1.5, L, ["日用品", "纸巾", "卫生纸", "洗衣液", "洗发水", "沐浴露", "牙膏", "牙刷"]),
    (0.8, L, ["洗衣", "洗衣机", "洗衣服", "烘干"]),
    (0.6, L, ["理发", "剪头发", "洗剪吹"]),
    (1, L, ["衣服", "买衣服", "T恤", "裤子", "外套", "羽绒服", "袜子"]),
    (0.6, L, ["鞋", "运动鞋", "拖鞋", "买鞋"]),
    (0.6, L, ["药", "感冒药", "药店", "买药", "创可贴"]),
    (0.3, L, ["医院", "挂号", "看病", "校医院", "体检", "看牙"]),
    (0.8, L, ["快递", "快递费", "寄快递", "顺丰"]),
    (0.4, L, ["雨伞", "伞", "衣架", "垃圾袋", "拖把"]),
    (0.5, P(L, L, None), ["护肤品", "面膜", "洗面奶", "防晒"]),
    # ---- tools: software, study, electronics ----
    (1, T, ["ChatGPT", "chatgpt plus", "GPT", "Claude", "Claude Pro", "Cursor", "Copilot"]),
    (0.5, T, ["iCloud", "icloud 50G", "百度网盘", "网盘会员", "阿里云盘"]),
    (0.3, T, ["云服务器", "阿里云", "腾讯云服务器", "域名", "服务器续费"]),
    (1.5, T, ["打印", "打印资料", "打印 实验报告", "复印", "打印店", "打印论文"]),
    (1, T, ["文具", "笔", "中性笔", "笔芯", "本子", "草稿纸", "便利贴", "文件夹"]),
    (0.8, T, ["教材", "课本", "买教材", "专业书", "习题册", "二手教材"]),
    (0.4, T, ["网课", "课程", "考研资料", "四六级报名", "雅思报名", "考试报名费"]),
    (0.6, T, ["键盘", "鼠标", "鼠标垫", "显示器", "数据线", "充电器", "U盘", "移动硬盘", "充电宝"]),
    (0.2, T, ["电脑", "笔记本电脑", "平板", "iPad", "电脑维修", "换电池"]),
    (0.3, T, ["台灯", "计算器", "插排", "扩展坞"]),
    (0.2, T, ["Notion", "印象笔记", "WPS会员", "Office", "知网下载"]),
    # ---- entertainment ----
    (1.2, E, ["Steam", "steam 秋促", "买游戏", "switch 卡带", "PS5 游戏", "Epic"]),
    (1, E, ["游戏充值", "原神", "原神月卡", "王者荣耀", "皮肤", "月卡", "648"]),
    (0.8, E, ["电影", "电影票", "看电影", "猫眼", "淘票票", "IMAX"]),
    (0.6, E, ["视频会员", "爱奇艺", "腾讯视频", "优酷会员", "B站大会员", "芒果TV"]),
    (0.4, E, ["网易云", "QQ音乐", "Spotify", "音乐会员", "Netflix"]),
    (0.4, E, ["KTV", "唱K", "ktv 包厢"]),
    (0.3, E, ["剧本杀", "密室逃脱", "桌游", "狼人杀"]),
    (0.3, E, ["演唱会", "音乐节", "话剧", "livehouse", "展览", "脱口秀"]),
    (0.4, E, ["旅游", "旅行", "景区门票", "门票", "民宿", "酒店"]),
    (0.4, E, ["手办", "盲盒", "乐高", "周边", "谷子", "漫展"]),
    (0.3, E, ["网吧", "电玩城", "抓娃娃", "台球", "保龄球"]),
    (0.3, E, ["小说", "漫画", "起点币", "晋江"]),
    (0.2, E, ["酒吧", "精酿", "喝酒"]),
    # ---- ambiguous: persona dependent ----
    (3, P(E, L, L), ["奶茶", "蜜雪冰城", "霸王茶姬", "一点点", "喜茶", "茶百道", "古茗", "奶茶 两杯", "coco"]),
    (2, P(T, L, T), ["咖啡", "瑞幸", "luckin", "瑞幸咖啡", "星巴克", "库迪", "美式", "拿铁"]),
    (1.5, P(E, L, E), ["零食", "买零食", "薯片", "辣条", "巧克力", "零食很忙"]),
    (0.5, P(L, E, L), ["健身", "健身房", "游泳", "羽毛球", "球场", "超级猩猩", "keep"]),
    (0.4, P(T, E, E), ["耳机", "蓝牙耳机", "AirPods", "音箱"]),
    (0.4, P(T, T, E), ["书", "买书", "当当", "图书", "旧书"]),
    (0.8, P(L, L, None), ["淘宝", "拼多多", "京东", "网购", "淘宝 杂物"]),
    (0.3, P(E, E, L), ["聚餐", "请客", "班级聚餐", "生日聚餐"]),
    (0.3, P(None, E, None), ["礼物", "生日礼物", "送礼", "花"]),
    (0.3, P(None, None, None), ["红包", "转账", "AA", "还钱", "借给室友"]),
    (0.3, P(L, None, L), ["会员", "续费", "充值"]),
    (0.3, P(T, T, E), ["手机", "手机壳", "贴膜", "手机维修"]),
    (0.3, P(L, E, L), ["猫粮", "猫砂", "宠物", "猫罐头"]),
    (0.2, P(T, T, T), ["驾校", "驾照", "科目二"]),
    (0.2, P(E, L, E), ["烟", "打火机"]),
    # ---- empty / noise ----
    (1.5, P(None, None, None), ["", " ", "?", "1", "xx", "不记得了", "杂"]),
]


HARD = [
    (L, ["酸菜鱼", "酸菜鱼 两人"]),
    (L, ["鸡公煲", "鸡公煲加饭"]),
    (L, ["隆江猪脚饭", "猪脚饭"]),
    (L, ["热干面", "热干面+蛋酒"]),
    (L, ["肠粉", "早上肠粉"]),
    (L, ["煲仔饭"]),
    (L, ["绝味鸭脖", "周黑鸭", "卤味"]),
    (L, ["手抓饼", "鸡蛋灌饼"]),
    (L, ["肉夹馍", "凉皮", "肉夹馍凉皮"]),
    (L, ["生煎", "小笼包"]),
    (L, ["关东煮", "炸串", "鸡排"]),
    (L, ["杨国福", "张亮"]),
    (L, ["老乡鸡"]),
    (L, ["自助餐", "烤肉自助"]),
    (L, ["鸭血粉丝汤"]),
    (L, ["寿司", "日料"]),
    (L, ["牛排", "西餐"]),
    (L, ["烤鸭"]),
    (L, ["机场大巴", "大巴"]),
    (L, ["顺风车", "花小猪", "曹操出行", "T3出行"]),
    (L, ["电动车充电", "电瓶车充电"]),
    (L, ["轮渡"]),
    (L, ["停车费", "过路费"]),
    (L, ["热水卡", "洗澡卡", "澡堂"]),
    (L, ["空调费", "电费充值"]),
    (L, ["移动话费", "联通", "电信套餐"]),
    (L, ["枕头", "床单", "被子", "四件套"]),
    (L, ["蚊香", "花露水", "电蚊拍"]),
    (L, ["收纳盒", "晾衣架", "挂钩"]),
    (L, ["电热水壶", "吹风机"]),
    (L, ["配眼镜", "隐形眼镜", "护理液"]),
    (L, ["布洛芬", "维生素", "口腔溃疡贴"]),
    (L, ["卫生巾", "棉签", "剃须刀", "指甲刀"]),
    (L, ["牛仔裤", "卫衣", "毛衣", "围巾", "帽子"]),
    (L, ["帆布鞋", "凉鞋"]),
    (L, ["行李箱"]),
    (L, ["证件照"]),
    (L, ["菜鸟驿站", "驿站取件费"]),
    (L, ["开水", "饮水机"]),
    (L, ["五金店 灯泡", "灯泡"]),
    (T, ["机械键盘", "显示器支架"]),
    (T, ["固态硬盘", "内存条", "读卡器"]),
    (T, ["转接头", "hdmi线", "typec线"]),
    (T, ["apple pencil", "触控笔"]),
    (T, ["论文查重", "知网查重", "维普查重"]),
    (T, ["overleaf", "jetbrains", "adobe"]),
    (T, ["百度文库", "文库下载"]),
    (T, ["装订", "胶装", "打印简历"]),
    (T, ["考研报名", "教资报名", "计算机二级报名"]),
    (T, ["百词斩会员", "扇贝单词", "有道词典会员"]),
    (T, ["实验耗材", "面包板", "arduino", "树莓派"]),
    (T, ["3d打印"]),
    (T, ["电子词典", "翻译笔"]),
    (T, ["学习资料", "复习资料"]),
    (T, ["维修电脑", "修电脑", "电脑清灰"]),
    (T, ["网课会员", "中国大学mooc"]),
    (E, ["音乐剧", "剧场", "相声"]),
    (E, ["博物馆", "看展"]),
    (E, ["欢乐谷", "迪士尼", "环球影城", "游乐园"]),
    (E, ["动物园", "海洋馆"]),
    (E, ["露营", "爬山", "徒步"]),
    (E, ["滑雪", "潜水", "攀岩"]),
    (E, ["卡丁车", "蹦床"]),
    (E, ["网吧包夜", "电竞馆"]),
    (E, ["手柄", "游戏机"]),
    (E, ["黑神话", "塞尔达", "崩坏星穹铁道", "明日方舟"]),
    (E, ["抽卡", "氪金", "买皮肤"]),
    (E, ["直播打赏", "打赏"]),
    (E, ["番剧", "追剧", "喜马拉雅"]),
    (E, ["快看漫画", "漫画会员"]),
    (E, ["拍立得", "相纸", "胶卷"]),
    (E, ["吉他弦", "尤克里里"]),
    (E, ["高达", "拼图", "模型"]),
    (E, ["桌球", "飞镖", "棋牌室"]),
    (E, ["蹦迪", "清吧", "夜店"]),
    (E, ["唱歌"]),
    (P(E, L, E), ["冰淇淋", "雪糕", "甜品"]),
    (P(E, E, L), ["蛋糕", "生日蛋糕"]),
    (P(L, E, L), ["按摩", "足疗", "洗浴"]),
    (P(T, E, E), ["kindle", "电子书"]),
    (P(E, E, T), ["画材", "马克笔", "颜料"]),
    (P(L, L, T), ["书包", "双肩包"]),
    (P(None, None, E), ["电子烟"]),
    (None, ["打车去看电影"]),
    (None, ["超市买零食和水"]),
    (None, ["午饭+奶茶"]),
    (P(E, E, E), ["和同学吃饭唱K"]),
    (P(E, E, E), ["看电影买爆米花"]),
    (L, ["午范", "晚反"]),  # typos
    (L, ["mdl", "kdj"]),    # abbreviations
    (P(None, None, None), ["给妈妈买的", "室友代付", "帮同学带"]),
    (P(None, None, None), ["万达", "大悦城", "商场"]),
]


FRESH = [
    (L, ["烤肠", "烤红薯", "烤冷面"]),
    (L, ["章鱼小丸子", "羊肉串", "牛肉面", "鱼香肉丝盖饭"]),
    (L, ["酸奶碗", "轻食沙拉", "麻辣拌"]),
    (L, ["洗车", "修自行车", "电动车维修"]),
    (L, ["驾照体检", "打疫苗"]),
    (L, ["电动牙刷", "牙线"]),
    (L, ["睡衣", "内裤", "秋裤"]),
    (L, ["泡脚桶", "暖宝宝", "热水袋"]),
    (L, ["小区停车", "高速费"]),
    (L, ["早茶", "茶餐厅"]),
    (L, ["鸡蛋", "挂面", "螺蛳粉"]),
    (L, ["保险", "医保"]),
    (T, ["显卡", "路由器", "网线"]),
    (T, ["手机充电器", "蓝牙鼠标"]),
    (T, ["作业本", "笔袋", "荧光笔"]),
    (T, ["pdf会员", "ocr识别"]),
    (T, ["简历模板", "ppt模板"]),
    (T, ["实验服", "护目镜"]),
    (T, ["github copilot", "cursor pro"]),
    (T, ["打印照片"]),
    (E, ["车模", "扭蛋"]),
    (E, ["写真", "拍写真"]),
    (E, ["电竞比赛门票", "看球赛"]),
    (E, ["桌游吧", "剧本杀车费"]),
    (E, ["游乐场", "摩天轮"]),
    (E, ["cos服", "汉服"]),
    (E, ["吃鸡皮肤", "吃鸡"]),
    (E, ["鸡尾酒"]),
    (E, ["电影院爆米花"]),
    (E, ["蜡笔小新周边"]),
    (P(E, E, T), ["游戏本"]),
    (P(L, E, L), ["美甲", "纹身"]),
    (P(E, L, E), ["糖葫芦", "蜜雪冰城柠檬水"]),
    (P(E, L, E), ["炸鸡啤酒"]),
    (P(L, T, L), ["共享充电宝"]),
    (P(E, E, L), ["鱼缸", "猫砂盆"]),
    (P(None, None, None), ["闲鱼", "闲鱼 耳机"]),
    (P(None, None, None), ["面试", "见面"]),
    (L, ["面试 打车", "面试 西装"]),
]

# Persona D is A, but genuinely disagrees with the built-in view of three frequent things.
D_OVERRIDES = {"海底捞": E, "打车": T, "话费": T}




DEV = [x for i, x in enumerate(HARD) if i % 2 == 0]
TEST = [x for i, x in enumerate(HARD) if i % 2 == 1]
TAILS = {"dev": DEV, "test": TEST, "fresh": FRESH}


def gold_of(gold, persona, first_variant=None):
    if persona == "D":
        if first_variant in D_OVERRIDES:
            return D_OVERRIDES[first_variant]
        persona = "A"
    return gold.get(persona) if isinstance(gold, dict) else gold


def stream(persona, seed, tail=None, exceptions=0.0, per_day=4.0):
    """Records of one person. An exception is a deliberate one-off: the person files this one
    record under another category than they usually would."""
    rng = random.Random(f"{persona}-{seed}")
    items = list(ITEMS)
    if tail:
        core = sum(w for w, _, _ in ITEMS)
        each = core * TAIL_SHARE / (1 - TAIL_SHARE) / len(TAILS[tail])
        items += [(each, gold, variants) for gold, variants in TAILS[tail]]
    weights = [w for w, _, _ in items]
    records = []
    for day in range(DAYS):
        for _ in range(max(0, int(rng.gauss(per_day, 1.5) + 0.5))):
            _, gold, variants = rng.choices(items, weights)[0]
            text = rng.choices(variants, [1 / (i + 1) ** 1.1 for i in range(len(variants))])[0]
            if text.strip() and rng.random() < MODIFY:
                m = rng.choice(NEUTRAL)
                text = f"{m}{text}" if rng.random() < 0.3 else f"{text} {m}"
            g = gold_of(gold, persona, variants[0])
            exception = g is not None and rng.random() < exceptions
            if exception:
                g = rng.choice([c for c in (L, T, E) if c != g])
            records.append({"day": day, "text": text, "gold": g, "exception": exception, "label": None})
    return records


def outcome(pred, gold):
    return "unknown" if pred is None else ("right" if pred == gold else "wrong")


def simulate(persona, seed, *, tail=None, exceptions=0.0, migrant_days=0):
    """(at-creation Counter, [monthly Review snapshot Counters]).
    migrant_days: the first days come from v1, where the person chose every category."""
    rng = random.Random(f"user-{persona}-{seed}")
    model = Classifier()
    records = stream(persona, seed, tail, exceptions)
    clock = 0

    def label(i, r, category):
        nonlocal clock
        clock += 1
        r["label"] = category
        model.set_label(i, r["text"], category, clock)

    def shown(r):
        return (r["label"], True) if r["label"] is not None else (model.classify(r["text"]), False)

    by_day = {}
    for i, r in enumerate(records):
        by_day.setdefault(r["day"], []).append((i, r))
    at_create, months = Counter(), []
    for day in range(DAYS):
        for i, r in by_day.get(day, []):
            if day < migrant_days:
                if r["gold"] is not None:
                    label(i, r, r["gold"])
                continue
            at_create[outcome(shown(r)[0], r["gold"])] += 1
        if day % 7 == 6 and day >= migrant_days:
            for d in range(day - 6, day + 1):
                for i, r in by_day.get(d, []):
                    if r["label"] is not None or r["gold"] is None:
                        continue
                    pred = model.classify(r["text"])
                    if (pred is not None and pred != r["gold"] and rng.random() < P_FIX) or (
                            pred is None and rng.random() < P_LABEL):
                        label(i, r, r["gold"])
        if day % 30 == 29 and day >= migrant_days:
            snap = Counter()
            for d in range(day - 29, day + 1):
                for _, r in by_day.get(d, []):
                    pred, by_user = shown(r)
                    snap["user" if by_user else outcome(pred, r["gold"])] += 1
            months.append(snap)
    return at_create, months


def summary(counter):
    right, wrong, unknown = counter["right"], counter["wrong"], counter["unknown"]
    machine = right + wrong
    return {"precision": right / machine if machine else 1.0,
            "coverage": machine / (machine + unknown) if machine + unknown else 0.0,
            "wrong": wrong / (machine + unknown) if machine + unknown else 0.0}


def evaluate(*, tail="fresh", seeds=range(5), personas=("A", "B", "C", "D"), exceptions=0.0, migrant_days=0):
    """Summaries at creation, in the first month and in the last month shown in Review."""
    create, first, last = Counter(), Counter(), Counter()
    for persona in personas:
        for seed in seeds:
            c, months = simulate(persona, seed, tail=tail, exceptions=exceptions, migrant_days=migrant_days)
            create += c
            first += months[0]
            last += months[-1]
    return summary(create), summary(first), summary(last)


def cold_tail(tail, persona="A"):
    """Built-in knowledge alone on a long tail: (right, wrong, undecided)."""
    model, counts = Classifier(), Counter()
    for gold, variants in TAILS[tail]:
        for text in variants:
            counts[outcome(model.classify(text), gold_of(gold, persona))] += 1
    return counts["right"], counts["wrong"], counts["unknown"]


def main():
    def fmt(s):
        return f"precision {s['precision']:.3f}  coverage {s['coverage']:.3f}  wrong {s['wrong']:.4f}"
    for tail in ("dev", "test", "fresh"):
        r, w, u = cold_tail(tail)
        print(f"cold {tail:5s} tail (built-in only): right {r}  wrong {w}  undecided {u}")
    for label, kw in [("new user", {}), ("from v1 (60 labelled days)", {"migrant_days": 60}),
                      ("new user, 3% one-off exceptions", {"exceptions": 0.03})]:
        for tail in ("test", "fresh"):
            create, first, last = evaluate(tail=tail, **kw)
            print(f"\n{label} · {tail} tail")
            print(f"  at creation   {fmt(create)}")
            print(f"  first month   {fmt(first)}")
            print(f"  sixth month   {fmt(last)}")


if __name__ == "__main__":
    main()
