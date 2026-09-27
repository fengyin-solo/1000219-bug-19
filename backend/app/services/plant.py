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


def _find_by_code(rows: list[dict[str, Any]], code: str) -> dict[str, Any] | None:
    for row in rows:
        if str(row.get("电站编号", "")).strip() == code:
            return row
    return None


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

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], bool]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing, False
        rows = store.rows(MODULE)
        code = str(values.get("电站编号") or "").strip()
        existing = _find_by_code(rows, code)
        if existing is not None:
            # 同一电站编号重复提交：回写原档案，不再追加记录，避免多出一份历史
            self._apply(existing, values)
            return existing, [], False
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        self._apply(entry, values)
        rows.append(entry)
        return entry, [], True

    def update_entry(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"光伏电站 {entry_id} 不存在或已归档"
        code = values.get("电站编号")
        if code is not None:
            code = str(code).strip()
            if not code:
                return None, "电站编号不能为空"
            clash = _find_by_code(store.rows(MODULE), code)
            if clash is not None and clash is not entry:
                return None, f"电站编号 {code} 已登记在其他档案上，不能重复"
        self._apply(entry, values)
        return entry, "光伏电站档案已更新"

    @staticmethod
    def _apply(entry: dict[str, Any], values: dict[str, Any]) -> None:
        """只回写提交上来的可编辑字段；id、status 等标识与状态字段不允许被覆盖。"""
        for field in EDITABLE_FIELDS:
            if field in values and values[field] is not None:
                entry[field] = values[field]

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
