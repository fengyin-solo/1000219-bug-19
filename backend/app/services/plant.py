"""电站档案业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "plant"
REQUIRED_FIELDS = ["电站编号", "电站名称", "装机容量"]
EDITABLE_FIELDS = ["电站编号", "电站名称", "装机容量", "并网日期", "所属区域", "运维负责人", "组件厂家"]
STATUS_ORDER = ["建设中", "并网运行", "停运维护", "已退役"]
ACTION_RULES = {"确认并网": "并网运行", "进入维护": "停运维护", "标记退役": "已退役"}
NEGATIVE_ACTIONS = []


class PlantService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("电站编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def update_entry(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """按记录 id 原地更新档案：列表、详情、编辑弹窗都只能用这个入口回写。

        只合并可编辑字段，id、status 等流转字段不允许从这里改，避免回写串行丢数据。
        """
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"光伏电站 {entry_id} 不存在或已归档"
        blanked = [field for field in REQUIRED_FIELDS if field in values and not str(values.get(field) or "").strip()]
        if blanked:
            return None, f"必填字段不能清空：{'、'.join(blanked)}"
        code = str(values.get("电站编号") or "").strip()
        if code:
            duplicated = any(
                str(row.get("电站编号", "")) == code and int(row.get("id", 0)) != entry_id
                for row in store.rows(MODULE)
            )
            if duplicated:
                return None, f"电站编号 {code} 已登记在其他档案上，不能重复占用"
        for field in EDITABLE_FIELDS:
            if field in values:
                entry[field] = values[field]
        return entry, "光伏电站档案已更新"

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"光伏电站 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于电站档案可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"光伏电站已{action}"
