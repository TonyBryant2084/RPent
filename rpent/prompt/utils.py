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


# 提示词节点类型
# 1. str：字符串。
# 2. Mapping[str, Any]：键为字符串、值类型不限的映射，例如 dict。
#    Mapping 是抽象基类，不要求映射可以修改。
# 3. Sequence[Any]：元素类型和数量不限、支持按位置索引的有序序列。
#    Sequence 是抽象基类，例如 list、tuple、str。
# 4. BulletList：项目符号列表节点，items 属性以元组保存各项内容。
# 5. Numbered：编号列表节点，items 属性以元组保存各项内容。
PromptNode = str | Mapping[str, Any] | Sequence[Any] | BulletList | Numbered

# 格式化提示词节点为最终的提示词字符串
def format_prompt(
    prompt: PromptNode, # 待格式化的提示词节点
    *,
    variables: Mapping[str, object] | None = None, # 提示词变量映射, 可省略
) -> str:

    # 1. (variables or {})：如果 variables 为 None，则使用空字典 {}
    # 2. .items()：返回字典的键值对迭代器
    # 3. 任意 object 对象都可以通过 str() 转换为字符串
    vars_ = {k: str(v) for k, v in (variables or {}).items()}


    return _render(prompt, vars_, depth=0).strip() + "\n"


def _render(
    value: Any, # 待格式化的提示词节点的值，类型不限
    variables: Mapping[str, str], # 提示词变量映射，键值对均为字符串
    *, # 后面的参数必须通过关键字传参
    depth: int # 当前提示词节点的深度，用于渲染标题和列表时的缩进和层级
) -> str:
    
    if value is None: # 如果提示词节点的值为 None，则返回空字符串
        return ""
    # isinstance(value, class): 检查 value 是否为 class 的实例, 若是, 返回 True, 否则返回 False
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


# 1. dedent()：删除多行字符串中所有非空行共有的开头缩进
#
# 原始字符串：
# text = """
#   You are a robot planner.
#     1. Observe the environment.
#     2. Pick up the cup.
# """
#
# 实际字符串：
# text = "\n  You are a robot planner.\n    1. Observe the environment.\n    2. Pick up the cup.\n"
#
# 第一行：2 个空格
# 第二行：4 个空格
# 第三行：4 个空格
# 公共缩进：min(2, 4, 4) = 2
#
# 执行 textwrap.dedent(text)：
# "\nYou are a robot planner.\n  1. Observe the environment.\n  2. Pick up the cup.\n"
#
# 说明：每个非空行删除 2 个空格，保留各行之间的相对缩进。
# 注意：min() 适用于本例中仅使用空格缩进的情况。


# 2. strip()：删除整个字符串首尾的空白字符
# 包括空格、制表符 \t、换行符 \n 等，不删除字符串中间的空白。
#
# 执行 textwrap.dedent(text).strip()：
# "You are a robot planner.\n  1. Observe the environment.\n  2. Pick up the cup."
#
# 说明：删除字符串开头和结尾的 \n，保留中间的换行与缩进。


# 3. _clean_text()：组合 dedent() 和 strip()
# 作用：清理 RPent 中的多行 Prompt，删除公共缩进和首尾空白。
#
# dedent()：删除公共缩进
# strip()：删除字符串首尾空白
# 返回值：清理后的 str，不修改原始字符串
def _clean_text(text: str) -> str:
    return textwrap.dedent(text).strip()
