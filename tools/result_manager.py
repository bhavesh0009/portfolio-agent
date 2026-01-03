"""
Result Management
Consolidated module for storing and analyzing stock screening results.

Combines functionality from:
- result_storage.py (save/load operations)
- data_analyzer.py (statistical analysis)
"""

import json
import io
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from contextlib import redirect_stdout, redirect_stderr


# ============================================================================
# SECTION 1: Result Storage
# ============================================================================

class ResultManager:
    """Handles storage, retrieval, and analysis of stock screening results"""

    def __init__(self, cache_dir: str = ".cache/screening_results"):
        """
        Initialize result manager with cache directory

        Args:
            cache_dir: Directory to store result files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize analyzer components
        self.safe_globals = {
            'json': json,
            '__builtins__': {
                'len': len,
                'sum': sum,
                'min': min,
                'max': max,
                'round': round,
                'sorted': sorted,
                'list': list,
                'dict': dict,
                'set': set,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'enumerate': enumerate,
                'zip': zip,
                'range': range,
            }
        }

    def save(self, results: Dict[str, Any], query: str, metadata: Optional[Dict] = None) -> str:
        """
        Save screening results to JSON file

        Args:
            results: Screening results dictionary
            query: The query used to generate results
            metadata: Optional additional metadata

        Returns:
            str: Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        count = len(results.get('stocks', []))
        filename = f"screening_{timestamp}_{count}.json"

        # Prepare data to save
        data = {
            "query": query,
            "timestamp": timestamp,
            "result_count": count,
            "metadata": metadata or {},
            "results": results
        }

        # Save to file
        filepath = self.cache_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[RESULT_MANAGER] Saved {count} results to: {filepath}")
        return str(filepath)

    def load(self, filepath: str) -> Dict[str, Any]:
        """
        Load screening results from file

        Args:
            filepath: Path to saved results file

        Returns:
            dict: Loaded data including query, results, and metadata
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"[RESULT_MANAGER] Loaded {data.get('result_count', 0)} results from: {filepath}")
        return data

    def list_results(self, limit: int = 10) -> list:
        """
        List recent result files

        Args:
            limit: Maximum number of files to return

        Returns:
            list: List of tuples (filepath, timestamp, count)
        """
        files = sorted(self.cache_dir.glob("screening_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        results = []
        for filepath in files[:limit]:
            # Extract info from filename
            parts = filepath.stem.split('_')
            if len(parts) >= 3:
                timestamp = f"{parts[1]}_{parts[2]}"
                count = parts[3] if len(parts) > 3 else "unknown"
                results.append((str(filepath), timestamp, count))

        return results

    def cleanup_old_results(self, days: int = 7) -> int:
        """
        Delete result files older than specified days

        Args:
            days: Number of days to keep

        Returns:
            int: Number of files deleted
        """
        cutoff = time.time() - (days * 24 * 60 * 60)
        deleted = 0

        for filepath in self.cache_dir.glob("screening_*.json"):
            if filepath.stat().st_mtime < cutoff:
                filepath.unlink()
                deleted += 1

        if deleted > 0:
            print(f"[RESULT_MANAGER] Cleaned up {deleted} old result files")

        return deleted


    # ============================================================================
    # SECTION 2: Data Analysis
    # ============================================================================

    def analyze(self, stocks: List[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
        """
        Analyze stock data and generate summary

        Args:
            stocks: List of stock dictionaries
            query: Original query (for context)

        Returns:
            dict: Analysis results with summary, statistics, and markdown
        """
        if not stocks:
            return {
                "summary": "No stocks to analyze",
                "statistics": {},
                "suggestions": [],
                "markdown": "# Stock Screening Analysis\n\nNo stocks to analyze"
            }

        # Generate analysis code dynamically
        analysis_code = self._generate_analysis_code(stocks)

        # Execute the code
        try:
            result = self._execute_code(analysis_code, {'stocks': stocks})

            # Add formatted markdown
            result['markdown'] = self.format_analysis_markdown(result)

            return result
        except Exception as e:
            return {
                "summary": f"Analysis failed: {str(e)}",
                "statistics": {},
                "suggestions": [],
                "error": str(e),
                "markdown": f"# Stock Screening Analysis\n\nAnalysis failed: {str(e)}"
            }

    def _generate_analysis_code(self, stocks: List[Dict]) -> str:
        """
        Generate Python code to analyze the stocks

        Args:
            stocks: Sample stocks to inspect structure

        Returns:
            str: Python code for analysis
        """
        # Inspect first stock to determine columns
        if not stocks:
            return "result = {'summary': 'No data'}"

        first_stock = stocks[0]
        columns = list(first_stock.keys())

        # Identify numeric columns (simple heuristic)
        numeric_cols = []
        for col in columns:
            try:
                # Check if first value is numeric
                val = first_stock[col]
                if val is not None:
                    float(str(val).replace(',', ''))
                    numeric_cols.append(col)
            except (ValueError, TypeError):
                pass

        # Generate analysis code
        code = f"""
# Analysis code (dynamically generated)
result = {{}}
result['total_stocks'] = len(stocks)
result['columns'] = {columns}
result['numeric_columns'] = {numeric_cols}
result['statistics'] = {{}}
result['suggestions'] = []

# Analyze numeric columns
for col in {numeric_cols}:
    values = []
    for stock in stocks:
        val = stock.get(col)
        if val is not None:
            try:
                # Handle comma-separated numbers
                clean_val = float(str(val).replace(',', ''))
                values.append(clean_val)
            except:
                pass

    if values:
        values_sorted = sorted(values)
        n = len(values)

        result['statistics'][col] = {{
            'count': n,
            'min': round(min(values), 2),
            'max': round(max(values), 2),
            'mean': round(sum(values) / n, 2),
            'median': round(values_sorted[n // 2], 2) if n > 0 else 0,
            'q1': round(values_sorted[n // 4], 2) if n > 3 else 0,
            'q3': round(values_sorted[3 * n // 4], 2) if n > 3 else 0
        }}

# Generate summary text
summary_lines = []
summary_lines.append(f"Analyzed {{result['total_stocks']}} stocks with {{len(result['columns'])}} columns\\n")
summary_lines.append("Numeric Columns Summary:")

for col, stats in result['statistics'].items():
    summary_lines.append(f"- {{col}}: {{stats['min']}} - {{stats['max']}} (mean: {{stats['mean']}}, median: {{stats['median']}})")

result['summary'] = '\\n'.join(summary_lines)

# Generate suggestions
suggestions = []

# Check for wide ranges (suggesting refinement)
for col, stats in result['statistics'].items():
    if stats['max'] > stats['mean'] * 2:
        suggestions.append(f"Consider filtering {{col}}: wide range detected ({{stats['min']}} - {{stats['max']}})")

    # Suggest threshold adjustments based on percentiles
    if 'ROE' in col or 'Return on equity' in col:
        q3_val = stats.get('q3', 0)
        if q3_val > 0:
            suggestions.append(f"Top 25% of stocks have {{col}} > {{q3_val}}. Consider raising threshold.")

    if 'Market' in col and 'Cap' in col:
        median_val = stats.get('median', 0)
        if median_val > 1000:
            suggestions.append(f"Median {{col}}: {{median_val}}. Consider focusing on segment (large/mid/small cap).")

result['suggestions'] = suggestions
"""
        return code

    def _execute_code(self, code: str, local_vars: Dict) -> Dict[str, Any]:
        """
        Safely execute Python code

        Args:
            code: Python code to execute
            local_vars: Local variables to provide

        Returns:
            dict: Result from code execution
        """
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute code
                exec(code, self.safe_globals, local_vars)

            # Get result
            result = local_vars.get('result', {})

            # Add any stdout/stderr if present
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()

            if stdout_text:
                result['stdout'] = stdout_text
            if stderr_text:
                result['stderr'] = stderr_text

            return result

        except Exception as e:
            return {
                "summary": f"Code execution error: {str(e)}",
                "error": str(e),
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue()
            }

    def format_analysis_markdown(self, analysis: Dict[str, Any]) -> str:
        """
        Format analysis results as markdown

        Args:
            analysis: Analysis results dictionary

        Returns:
            str: Markdown formatted summary
        """
        lines = []
        lines.append("# Stock Screening Analysis\n")

        # Summary
        lines.append("## Summary")
        lines.append(analysis.get('summary', 'No summary available'))
        lines.append("")

        # Statistics table
        if analysis.get('statistics'):
            lines.append("## Detailed Statistics")
            lines.append("")
            lines.append("| Metric | Min | Max | Mean | Median | Q1 | Q3 |")
            lines.append("|--------|-----|-----|------|--------|----|----|")

            for col, stats in analysis['statistics'].items():
                lines.append(
                    f"| {col} | {stats.get('min', 'N/A')} | {stats.get('max', 'N/A')} | "
                    f"{stats.get('mean', 'N/A')} | {stats.get('median', 'N/A')} | "
                    f"{stats.get('q1', 'N/A')} | {stats.get('q3', 'N/A')} |"
                )
            lines.append("")

        # Suggestions
        if analysis.get('suggestions'):
            lines.append("## Refinement Suggestions")
            for suggestion in analysis['suggestions']:
                lines.append(f"- {suggestion}")
            lines.append("")

        return '\n'.join(lines)


    # ============================================================================
    # SECTION 3: Combined Operations
    # ============================================================================

    def save_and_analyze(
        self,
        results: Dict[str, Any],
        query: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Save results and analyze them in one operation

        Args:
            results: Screening results dictionary
            query: The query used
            metadata: Optional metadata

        Returns:
            dict: Contains 'filepath' and 'analysis' keys
        """
        # Save results
        filepath = self.save(results, query, metadata)

        # Analyze stocks
        stocks = results.get('stocks', [])
        analysis = self.analyze(stocks, query)

        return {
            'filepath': filepath,
            'analysis': analysis
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def save_screening_results(results: Dict[str, Any], query: str, metadata: Optional[Dict] = None) -> str:
    """
    Convenience function to save screening results

    Args:
        results: Screening results dictionary
        query: The query used
        metadata: Optional metadata

    Returns:
        str: Path to saved file
    """
    manager = ResultManager()
    return manager.save(results, query, metadata)


def load_screening_results(filepath: str) -> Dict[str, Any]:
    """
    Convenience function to load screening results

    Args:
        filepath: Path to saved file

    Returns:
        dict: Loaded results data
    """
    manager = ResultManager()
    return manager.load(filepath)


def analyze_screening_results(stocks: List[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
    """
    Convenience function to analyze screening results

    Args:
        stocks: List of stock dictionaries
        query: Original query

    Returns:
        dict: Analysis results with summary, statistics, and markdown
    """
    manager = ResultManager()
    return manager.analyze(stocks, query)


# ============================================================================
# Module Testing
# ============================================================================

if __name__ == "__main__":
    print("=== Result Manager Test Suite ===\n")

    # Test data
    test_stocks = [
        {"Name": "Stock A", "Market Capitalization": "5000", "ROE %": "25.5", "P/E": "15.2"},
        {"Name": "Stock B", "Market Capitalization": "8000", "ROE %": "30.1", "P/E": "12.8"},
        {"Name": "Stock C", "Market Capitalization": "3500", "ROE %": "18.7", "P/E": "20.5"},
    ]

    test_results = {
        "total_results": 3,
        "stocks": test_stocks
    }

    # Test 1: Storage
    print("TEST 1: Save Results")
    manager = ResultManager()
    filepath = manager.save(test_results, "Market Capitalization > 1000 AND ROE % > 15")
    print(f"Saved to: {filepath}\n")

    # Test 2: Analysis
    print("TEST 2: Analyze Results")
    analysis = manager.analyze(test_stocks, "Test query")
    print(f"Summary: {analysis['summary']}\n")
    print(f"Statistics: {analysis.get('statistics', {})}\n")

    # Test 3: Combined operation
    print("TEST 3: Save and Analyze")
    combined = manager.save_and_analyze(test_results, "Combined test query")
    print(f"Filepath: {combined['filepath']}")
    print(f"Analysis summary: {combined['analysis']['summary']}\n")

    # Test 4: Markdown formatting
    print("TEST 4: Markdown Output")
    print(analysis['markdown'])
