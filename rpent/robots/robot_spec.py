# robot_spec.py：定义机器人或仿真环境接入 RPent 的统一描述结构，包括配置信息和初始化等函数接口

from __future__ import annotations

import argparse
from collections.abc import Callable

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rpent.dashboard.events import DashboardEventSink
from rpent.dashboard.spec import DashboardSpec
from rpent.evaluation import RunFinalizer


if TYPE_CHECKING:
    from rpent.utils.daemon import ProcessDaemon

# 导入数据类装饰器，用于自动生成初始化、对象表示、相等比较等方法。
from dataclasses import dataclass


from rpent.robots.prompt_bundle import PromptBundle

@dataclass(frozen=True) # dataclass: 自动生成初始化等方法, frozen=True: 实例创建后,不允许直接给字段重新赋值
# 任务配置清单
class RunConfig:

    recipe_tag: str # 任务配置标签(LIBERO为例: 任务套件(一组相关的机器人任务) + 任务编号(这组任务中的具体任务) + 随机种子(保证实验可重复))
    output_dir: Path # 用来保存本次运行结果的目录路径
    prompt_vars: dict[str, Any] # 构建提示词所需要的变量
    task_desc: dict[str, Any] # 用一个字典保存本次任务的描述信息，方便记录和评测
    enable_direct_action: bool = False # 是否允许规划模型直接填写底层动作数值，并调用工具执行


@dataclass(frozen=True) # dataclass: 自动生成初始化等方法, frozen=True: 实例创建后,不允许直接给字段重新赋值
# 机器人接入 RPent 的配置表
class RobotSpec:

    name: str # 机器人名称
    prompts: PromptBundle # 该机器人使用的提示词集和
    add_cli_args: Callable[[argparse.ArgumentParser, bool], None] #
    parse_config: Callable[[argparse.Namespace], RunConfig]
    init_runtime: Callable[
        [argparse.Namespace, Path, DashboardEventSink, set[str] | None],
        tuple[list["ProcessDaemon"], dict[str, Any]],
    ]
    dashboard: DashboardSpec | None = None
    #: Physical scene restoration requires operator involvement, not simulator reset.
    #: Operator input requires an exclusive terminal unless an external ENV owns it.
    is_real_robot: bool = False
    #: Whether the robot implements the exploration-time toolkit contract.
    #: The CLI uses this instead of hard-coding robot names so real-robot
    #: extensions can opt into exploration with their own reset semantics.
    supports_exploration: bool = False
    #: Supports human-interactive exploration via the shared HIL input broker.
    #: Requires supports_exploration, get_toolkit(operator_input=...), and toolkit
    #: request_direct_verdict/finalize_direct_verdict/direct_verdict_requested.
    #: Operator success gates automatic memory publication for this capability.
    supports_human_interactive_exploration: bool = False
    memory_repo_id: str = "RLinf/RPent-memory"
    #: Validate robot arguments without I/O before CLI or Dashboard services start.
    validate_args: Callable[[argparse.Namespace], None] | None = None
    #: Prepare per-task memory before prompts, planner, toolkit or task services.
    #: The hook owns synchronization and sets prompt_vars['memory_dir']; robots
    #: without a hook use the shared HF sync. Dashboard defers hooked sync until
    #: the task's model and configuration are known.
    prepare_memory: Callable[[argparse.Namespace, RunConfig], None] | None = None
    finalize_run: RunFinalizer | None = None
    #: Replay this robot's recorded plan for one cell, in place of a planner.
    #: Takes the toolkit, the cell tag, and a note sink; returns at least
    #: ``{"done": bool}``. Left unset by robots without Flash Mode.
    run_flash: Callable[[Any, str, Callable[[str], None]], dict[str, Any]] | None = None
