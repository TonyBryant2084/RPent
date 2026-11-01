from __future__ import annotations

import textwrap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rpent.utils.templates import substitute_text


@dataclass(frozen=True) # dataclass: 自动生成初始化等方法, frozen=True: 实例创建后,不允许直接给字段重新赋值
class BulletList:
    """项目符号列表节点，供格式化函数识别并渲染为 Markdown 无序列表。"""

    # 保存各项提示词内容：元组长度不限，每个元素的类型不限。
    items: tuple[Any, ...]

    def __init__(
        self,
        items: Sequence[Any],  # 接收有序序列，如列表、元组；元素类型和数量不限。
    ):
        # 将传入的序列转换为元组，并保存到当前对象的 items 属性。
        # 使用 object.__setattr__ 绕过 frozen=True 的普通赋值限制，完成初始化。
        object.__setattr__(self, "items", tuple(items))


@dataclass(frozen=True)
class Numbered:
    """编号列表节点，供格式化函数识别并渲染为 Markdown 有序列表。"""

    # 保存各项提示词内容：元组长度不限，每个元素的类型不限。
    items: tuple[Any, ...]

    def __init__(self, items: Sequence[Any]):
        # 与 BulletList 使用相同的存储方式，将输入转换为元组并保存。
        # 两者的对象类型不同，供格式化函数区分无序列表和有序列表。
        object.__setattr__(self, "items", tuple(items))


# 提示词节点的类型别名，| 表示“或者”，允许以下任意一种类型：
# 1. str：字符串。
# 2. Mapping[str, Any]：键为字符串、值类型不限的映射，例如 dict。
#    Mapping 是抽象基类，不要求映射可以修改。
# 3. Sequence[Any]：元素类型和数量不限、支持按位置索引的有序序列。
#    Sequence 是抽象基类，例如 list、tuple、str。
# 4. BulletList：项目符号列表节点，items 属性以元组保存各项内容。
# 5. Numbered：编号列表节点，items 属性以元组保存各项内容。
PromptNode = str | Mapping[str, Any] | Sequence[Any] | BulletList | Numbered


def format_prompt(
    prompt: PromptNode,
    *,
    variables: Mapping[str, object] | None = None,
) -> str:
    """Render a Python prompt tree into final prompt text."""
    vars_ = {k: str(v) for k, v in (variables or {}).items()}
    return _render(prompt, vars_, depth=0).strip() + "\n"


def _render(value: Any, variables: Mapping[str, str], *, depth: int) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return substitute_text(_clean_text(value), variables, strict=True)
    if isinstance(value, BulletList):
        return _render_list(value.items, variables, depth=depth, ordered=False)
    if isinstance(value, Numbered):
        return _render_list(value.items, variables, depth=depth, ordered=True)
    if isinstance(value, Mapping):
        return _render_mapping(value, variables, depth=depth)
    if isinstance(value, Sequence):
        return _render_list(value, variables, depth=depth, ordered=False)
    return str(value)


def _render_mapping(
    value: Mapping[str, Any],
    variables: Mapping[str, str],
    *,
    depth: int,
) -> str:
    r"""Render mapping entries as titled prompt sections.

    Example:
        ``{"INSPECT": "Check the image."}`` at depth 0 renders as::

            ═══════════════════════════════════════════════════════════════════════
            INSPECT
            ═══════════════════════════════════════════════════════════════════════

            Check the image.
    """
    parts: list[str] = []
    for title, body in value.items():
        rendered = _render(body, variables, depth=depth + 1).strip()
        if not rendered:
            continue
        if depth == 0:
            section = [
                "═" * 71,
                title,
                "═" * 71,
                "",
                rendered,
            ]
            parts.append("\n".join(section))
        else:
            parts.append(f"{'#' * min(depth + 2, 6)} {title}\n\n{rendered}")
    return "\n\n\n".join(parts)


def _render_list(
    items: Sequence[Any],
    variables: Mapping[str, str],
    *,
    depth: int,
    ordered: bool,
) -> str:
    r"""Render prompt nodes as a Markdown list.

    Example:
        >>> item = "inspect title\nmulti-line inspect content"
        >>> _render_list([item], {}, depth=0, ordered=True)
        '1. inspect title\n   multi-line inspect content'

        The rendered Markdown aligns the continuation line with the first line's
        content::

            1. inspect title
               multi-line inspect content
    """
    rendered_items = [
        _render(item, variables, depth=depth + 1).strip() for item in items
    ]
    rendered_items = [item for item in rendered_items if item]
    blocks: list[str] = []
    for index, item in enumerate(rendered_items, 1):
        marker = f"{index}." if ordered else "-"
        first_line, *continuation_lines = item.splitlines()
        continuation_indent = " " * (len(marker) + 1)
        indented_continuations = [
            continuation_indent + line for line in continuation_lines
        ]
        blocks.append("\n".join([f"{marker} {first_line}", *indented_continuations]))
    separator = "\n\n" if ordered else "\n"
    return separator.join(blocks)


def _clean_text(text: str) -> str:
    return textwrap.dedent(text).strip()
