"""PersonaCore CLI 入口：文字面试 → 大五人格评分 → 报告（含完整面试记录）。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import load_config
from .llm import LLMClient
from .orchestrator import Orchestrator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "dimensions.yaml"
DEFAULT_OUT_DIR = PROJECT_ROOT / "report_output"


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    # Windows GBK 控制台兼容：遇到无法编码的字符时用 ? 替代，而不是崩溃
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="PersonaCore：多智能体文字面试性格测评（大五人格 OCEAN）"
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="维度配置文件路径")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="每次测评报告的保存目录")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if os.getenv("MAX_PROBES"):
        config.max_probes = int(os.getenv("MAX_PROBES"))

    llm = LLMClient()
    orchestrator = Orchestrator(config, llm)
    result = orchestrator.run(input_fn=input, output_fn=print)

    full = result.full_markdown()
    print("\n" + "=" * 60)
    print(full)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{result.run_id}.md"
    json_path = out_dir / f"{result.run_id}.json"
    md_path.write_text(full, encoding="utf-8")
    json_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n报告已保存：{md_path}")
    print(f"结构化数据：{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
