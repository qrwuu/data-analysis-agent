import time
import unittest

from agent.skills import SkillLoader
from agent.skills.intent_router import infer_builtin_skill, routable_skill_names
from api.chat import _resolve_activation
from data.session import ChatSession


class TestSkillIntentRouter(unittest.TestCase):
    CASES = {
        "arima": "用 ARIMA 预测下个月销量",
        "chart": "按月份画销售趋势图",
        "dashboard": "帮我制作经营数据看板",
        "data": "查看数据质量和字段情况",
        "decile": "按消费金额做客户十等分分层",
        "export": "将清洗后的数据导出为 CSV",
        "funnel-analysis": "分析注册到支付的转化漏斗",
        "gru": "用 GRU 做销量预测",
        "inset": "填补订单金额的缺失值",
        "kmeans": "将客户分成 3 类并总结特征",
        "logistic": "用逻辑回归预测客户是否会购买",
        "ppt": "生成一份销售汇报 PPT",
        "prophet": "用 Prophet 预测未来销售额",
        "regression": "做回归分析，找出影响销售额的因素",
        "report": "生成一份本月经营分析报告",
        "sarima": "用 SARIMA 做季节性销售预测",
        "screening": "做单变量筛选，找出重要解释变量",
        "sql": "用 SQL 查询订单表前 10 行",
        "tree": "预测哪些客户可能流失",
        "trimming": "去除销售额中的极端值",
        "var": "用 VAR 分析多个时间序列之间的关系",
        "winsorize": "对价格字段进行缩尾处理",
    }

    def test_every_builtin_skill_has_a_natural_language_route(self):
        loaded = set(SkillLoader().load_all())
        self.assertTrue(set(self.CASES).issubset(loaded))
        self.assertEqual(set(self.CASES), set(routable_skill_names()))
        for expected, message in self.CASES.items():
            self.assertEqual(infer_builtin_skill(message), expected, message)

    def test_automatic_route_activates_skill_without_frontend_selection(self):
        session = ChatSession(session_id=f"auto-skill-{time.time_ns()}")
        activation, skill, command = _resolve_activation(
            session, {"message": "将客户分成 3 类并总结特征"},
        )
        self.assertEqual(activation.skill_name, "kmeans")
        self.assertEqual(skill.name, "kmeans")
        self.assertIsNone(command)

    def test_explicit_picker_selection_still_has_priority(self):
        session = ChatSession(session_id=f"explicit-skill-{time.time_ns()}")
        activation, skill, _ = _resolve_activation(
            session, {"message": "将客户分成 3 类", "skill": "chart"},
        )
        self.assertEqual(activation.skill_name, "chart")
        self.assertEqual(skill.name, "chart")


if __name__ == "__main__":
    unittest.main()
