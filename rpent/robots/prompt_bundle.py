# Copyright 2026 The RPent Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Prompt bundle dataclass for robot-contributed LLM prompts.

Lives in :mod:`rpent.robots` so each robot's
``prompt_bundle.py`` (e.g. :mod:`robots.libero.prompt_bundle`)
can import it without depending on the RPC transport layer.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from rpent.prompt.utils import PromptNode, format_prompt

# 提示词工厂: 可调用函数的类型(参数类型没有限定, 返回值类型为 PromptNode(提示词节点))
PromptFactory = Callable[..., PromptNode]


@dataclass(frozen=True) # dataclass: 自动生成初始化等方法, frozen=True: 实例创建后,不允许直接给字段重新赋值
# 提示词生成函数包
class PromptBundle:
    """保存某个机器人的系统提示词和用户提示词生成函数"""

    # 系统提示词生成函数，通常用于定义模型角色、行为规则等
    system: PromptFactory

    # 用户提示词生成函数，通常用于提供具体任务和上下文
    user: PromptFactory

    # 选择提示词生成函数, 传入变量生成提示字, 格式化成字符串返回
    def render(
        self,
        variant: str, # 提示词类型: "system" or "user"
        *, # 后面的参数必须通过关键字传参
        variables: Mapping[str, object] | None = None, # 提示词变量映射, 可省略
    ) -> str:
        # getattr(self, variant): 根据 variant 字符串, 从当前对象 self 中取出同名属性
        # 1. variant = "system": prompt = getattr(self, variant)(variables) == self.system(variables)
        # 2. variant = "user": prompt = getattr(self, variant)(variables) == self.user(variables)
        prompt = getattr(self, variant)(variables)
        return format_prompt(prompt, variables=variables)
