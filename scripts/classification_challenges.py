"""Frozen synthetic challenge reporting, including explicit abstention and correction counts."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from classification import Classifier
from scripts.student_scenarios import DEV, HOLDOUT, cold

# Broader author-written cases, frozen before implementing phase-four evidence rules.
# This is a challenge/regression set, not an unseen statistical estimate.
C2 = [
    ('淘宝线性代数课本', '工具'), ('京东买了牙刷', '生活'), ('拼多多购买鼠标垫', '工具'),
    ('网购桌游两盒', '娱乐'), ('京东洗衣液家庭装', '生活'), ('淘宝纸巾三包', '生活'),
    ('打印化学实验报告', '工具'), ('复印英语试卷', '工具'), ('电路教材', '工具'),
    ('宿舍换灯泡', None), ('奶茶和教材', None), ('手机牙膏', None),
    ('京东苹果键盘膜', None), ('面包机玩具', None), ('烤箱模型', None), ('车载摆件', None),
    ('京东面包板', '工具'), ('午饭两份', '生活'), ('周末看电影', '娱乐'),
    ('秋裤', '生活'), ('烤冷面', '生活'), ('鸡公煲加饭', '生活'),
    ('面部护理', None), ('粉丝见面会', None), ('苹果维修', None), ('小鸡玩偶', None),
    ('未知品牌耳机', None), ('瑞幸咖啡小组讨论', None), ('瑞幸咖啡周末聊天', None),
    ('自习室咖啡', None), ('超市插排', None), ('淘宝电影票和教材', None),
    ('图书馆复印讲义', '工具'), ('京东量子力学教材', '工具'), ('买牙膏补充装', '生活'),
    ('打印报告玩具', None), ('地铁回学校', '生活'), ('给自己买药', '生活'),
    ('校园卡充值', '生活'), ('羊毛围巾', '生活'), ('买球鞋', '生活'), ('打印机配件', None),
]


def metrics(cases):
    result = cold(cases)
    result['abstentions'] = sum(row['actual'] is None for row in result['cases'])
    result['decisions'] = len(cases) - result['abstentions']
    result['safe_clear_coverage'] = result['resolved_clear_cases'] / result['clear_cases'] if result['clear_cases'] else None
    result['decision_precision'] = (result['decisions'] - result['wrong_decisions']) / result['decisions'] if result['decisions'] else None
    return result


def corrections():
    rows = []
    for description, category in [('咖啡赶论文', '工具'), ('午饭', '娱乐'), ('瑞幸咖啡周末聊天', '娱乐')]:
        for count in (0, 1, 2):
            labels = [(i, description, category, i) for i in range(count)]
            model = Classifier(labels)
            rows.append({'description': description, 'corrections': count, 'chosen_category': category,
                         'derived': model.classify(description),
                         'other_purpose': model.classify('瑞幸咖啡小组讨论')})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new report path')
    challenge = json.loads((ROOT / 'tests/fixtures/classification_challenge_c1.json').read_text('utf-8'))
    result = {'data': 'synthetic, not blind or real-user accuracy',
              'dev': metrics(DEV), 'holdout': metrics(HOLDOUT),
              'C1': metrics(challenge['cases']), 'C2': metrics(C2), 'corrections': corrections()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({name: {k: v for k, v in report.items() if k != 'cases'}
                      for name, report in result.items() if isinstance(report, dict)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
