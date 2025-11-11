#!/usr/bin/env python3
"""
Codebase Health Analyzer
Analyzes current codebase and identifies improvement opportunities

Run: python analyze_codebase.py
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


class CodebaseAnalyzer:
    """Analyze Python codebase for quality metrics"""

    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir)
        self.py_files = list(self.root.rglob("*.py"))
        # Exclude virtual env and cache
        self.py_files = [
            f for f in self.py_files
            if '.venv' not in str(f) and '__pycache__' not in str(f)
        ]

    def count_lines(self) -> Tuple[int, int, int]:
        """Count total, code, and comment lines"""
        total_lines = 0
        code_lines = 0
        comment_lines = 0

        for file_path in self.py_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        total_lines += 1
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            comment_lines += 1
                        elif stripped and not stripped.startswith('"""') and not stripped.startswith("'''"):
                            code_lines += 1
            except:
                pass

        return total_lines, code_lines, comment_lines

    def count_async_functions(self) -> int:
        """Count async def occurrences"""
        count = 0
        for file_path in self.py_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    count += len(re.findall(r'\basync\s+def\s+', content))
            except:
                pass
        return count

    def count_type_hints(self) -> int:
        """Count functions with type hints"""
        count = 0
        for file_path in self.py_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Count functions with -> return type hint
                    count += len(re.findall(r'def\s+\w+\([^)]*\)\s*->', content))
            except:
                pass
        return count

    def count_total_functions(self) -> int:
        """Count all function definitions"""
        count = 0
        for file_path in self.py_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    count += len(re.findall(r'\bdef\s+\w+\s*\(', content))
            except:
                pass
        return count

    def find_error_handling_patterns(self) -> Dict[str, int]:
        """Find error handling patterns"""
        patterns = {
            'try_except': 0,
            'retry_decorator': 0,
            'circuit_breaker': 0,
            'timeout': 0
        }

        for file_path in self.py_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    patterns['try_except'] += len(re.findall(r'\btry\s*:', content))
                    patterns['retry_decorator'] += len(re.findall(r'@retry', content))
                    patterns['circuit_breaker'] += len(re.findall(r'@circuit', content))
                    patterns['timeout'] += len(re.findall(r'timeout\s*=', content))
            except:
                pass

        return patterns

    def find_i_o_operations(self) -> Dict[str, List[str]]:
        """Find I/O operations that should be async"""
        io_patterns = {
            'requests': r'requests\.(get|post|put|delete)',
            'file_read': r'open\([^)]+,\s*["\']r',
            'file_write': r'open\([^)]+,\s*["\']w',
            'db_query': r'\.(execute|query|fetch)',
            'sleep': r'time\.sleep',
        }

        findings = defaultdict(list)

        for file_path in self.py_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for op_type, pattern in io_patterns.items():
                        matches = re.findall(pattern, content)
                        if matches:
                            findings[op_type].append(str(file_path.relative_to(self.root)))
            except:
                pass

        return findings

    def check_for_tools(self) -> Dict[str, bool]:
        """Check if improvement tools are available"""
        tools = {
            'pytest': False,
            'mypy': False,
            'ruff': False,
            'prometheus_client': False,
            'tenacity': False,
            'aiohttp': False,
        }

        requirements_file = self.root / 'requirements.txt'
        if requirements_file.exists():
            with open(requirements_file) as f:
                content = f.read()
                for tool in tools:
                    if tool in content:
                        tools[tool] = True

        return tools

    def generate_report(self) -> str:
        """Generate comprehensive analysis report"""
        total_lines, code_lines, comment_lines = self.count_lines()
        async_funcs = self.count_async_functions()
        total_funcs = self.count_total_functions()
        typed_funcs = self.count_type_hints()
        error_patterns = self.find_error_handling_patterns()
        io_ops = self.find_i_o_operations()
        tools = self.check_for_tools()

        report = []
        report.append("=" * 80)
        report.append("CODEBASE HEALTH REPORT")
        report.append("=" * 80)
        report.append("")

        # Size metrics
        report.append("📊 CODEBASE SIZE")
        report.append("-" * 80)
        report.append(f"  Total files:        {len(self.py_files)}")
        report.append(f"  Total lines:        {total_lines:,}")
        report.append(f"  Code lines:         {code_lines:,}")
        report.append(f"  Comment lines:      {comment_lines:,}")
        report.append(f"  Comment ratio:      {(comment_lines/total_lines*100):.1f}%")
        report.append("")

        # Async usage
        async_ratio = (async_funcs / total_funcs * 100) if total_funcs > 0 else 0
        report.append("⚡ ASYNC/AWAIT USAGE")
        report.append("-" * 80)
        report.append(f"  Total functions:    {total_funcs}")
        report.append(f"  Async functions:    {async_funcs}")
        report.append(f"  Async ratio:        {async_ratio:.1f}%")
        report.append("")

        if async_ratio < 20:
            report.append("  ⚠️  RECOMMENDATION: Very low async usage")
            report.append("      → Add async to I/O operations for 5-10x speedup")
            report.append("      → See: examples/async_refactor_example.py")
            report.append("")

        # Type safety
        typed_ratio = (typed_funcs / total_funcs * 100) if total_funcs > 0 else 0
        report.append("🛡️  TYPE SAFETY")
        report.append("-" * 80)
        report.append(f"  Functions with type hints:  {typed_funcs}")
        report.append(f"  Type hint coverage:         {typed_ratio:.1f}%")
        report.append("")

        if typed_ratio < 50:
            report.append("  ⚠️  RECOMMENDATION: Low type hint coverage")
            report.append("      → Add type hints to prevent runtime errors")
            report.append("      → Run: mypy agents/ tools/ --strict")
            report.append("")

        # Error handling
        report.append("🔧 ERROR HANDLING")
        report.append("-" * 80)
        report.append(f"  Try/except blocks:   {error_patterns['try_except']}")
        report.append(f"  Retry decorators:    {error_patterns['retry_decorator']}")
        report.append(f"  Circuit breakers:    {error_patterns['circuit_breaker']}")
        report.append(f"  Timeout protection:  {error_patterns['timeout']}")
        report.append("")

        if error_patterns['retry_decorator'] == 0:
            report.append("  ⚠️  RECOMMENDATION: No retry logic detected")
            report.append("      → Add @retry decorator to API calls")
            report.append("      → Install: pip install tenacity")
            report.append("")

        # I/O operations
        report.append("🌐 I/O OPERATIONS (Should be async)")
        report.append("-" * 80)
        for op_type, files in io_ops.items():
            report.append(f"  {op_type:20} {len(set(files))} files")
        report.append("")

        if io_ops:
            report.append("  💡 TIP: These I/O operations should be async for better performance")
            report.append("")

        # Available tools
        report.append("🛠️  DEVELOPMENT TOOLS")
        report.append("-" * 80)
        for tool, installed in tools.items():
            status = "✅" if installed else "❌"
            report.append(f"  {status} {tool}")
        report.append("")

        missing_tools = [t for t, installed in tools.items() if not installed]
        if missing_tools:
            report.append("  📦 INSTALL MISSING TOOLS:")
            report.append(f"     pip install {' '.join(missing_tools)}")
            report.append("")

        # Overall score
        report.append("=" * 80)
        report.append("📈 HEALTH SCORE")
        report.append("=" * 80)

        scores = {
            'Async Usage': (async_ratio / 100, 0.3),
            'Type Safety': (typed_ratio / 100, 0.2),
            'Error Handling': (min(error_patterns['retry_decorator'] / 10, 1.0), 0.2),
            'Tooling': (sum(tools.values()) / len(tools), 0.3)
        }

        total_score = sum(score * weight for score, weight in scores.values())

        for category, (score, weight) in scores.items():
            bar_length = int(score * 50)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            report.append(f"  {category:20} {bar} {score*100:.0f}%")

        report.append("")
        report.append(f"  OVERALL HEALTH:      {'█' * int(total_score * 50)}{'░' * (50 - int(total_score * 50))} {total_score*100:.0f}%")
        report.append("")

        if total_score < 0.5:
            report.append("  🔴 STATUS: Needs significant improvement")
            report.append("     → Start with: QUICK_START_IMPROVEMENTS.md")
        elif total_score < 0.7:
            report.append("  🟡 STATUS: Good foundation, room for optimization")
            report.append("     → See: 100X_IMPROVEMENT_PLAN.md")
        else:
            report.append("  🟢 STATUS: Excellent! Production-ready")

        report.append("")
        report.append("=" * 80)
        report.append("📚 NEXT STEPS")
        report.append("=" * 80)
        report.append("")
        report.append("1. Read:  QUICK_START_IMPROVEMENTS.md (3 changes this week)")
        report.append("2. Demo:  python examples/async_refactor_example.py")
        report.append("3. Start: Refactor tools/screener_session.py to async")
        report.append("4. Guide: Use REFACTOR_TEMPLATE.md for patterns")
        report.append("5. Plan:  Follow 100X_IMPROVEMENT_PLAN.md roadmap")
        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


def main():
    """Run analysis and print report"""
    analyzer = CodebaseAnalyzer()
    report = analyzer.generate_report()
    print(report)

    # Save report
    with open('CODEBASE_HEALTH_REPORT.txt', 'w') as f:
        f.write(report)
    print("\n💾 Report saved to: CODEBASE_HEALTH_REPORT.txt")


if __name__ == "__main__":
    main()
