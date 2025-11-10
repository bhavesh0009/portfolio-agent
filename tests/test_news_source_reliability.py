"""
News Source Reliability Test Script

Tests news scraping and article extraction for Indian stock market sources.
Analyzes source frequency, reliability, and extraction success rates.

Identifies which sources are most reliable for financial news scraping.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.news_scraper import scrape_news
from tools.article_extractor import extract_article
from utils.logger import get_logger

logger = get_logger("tests.news_source_reliability")


class NewsSourceReliabilityTest:
    """Test news source reliability for Indian stock market queries"""

    # Test queries covering different aspects of Indian stock market
    TEST_QUERIES = [
        "Indian stock market today",
        "Nifty 50 news",
        "Indian IT sector stocks",
        "Reliance Industries stock news",
        "Indian banking sector",
        "TCS INFY stock market",
        "Indian market sentiment"
    ]

    def __init__(self):
        """Initialize test runner"""
        self.all_articles = []
        self.source_frequency = Counter()
        self.source_articles = defaultdict(list)  # source -> [article URLs]
        self.extraction_results = {}  # source -> {success, partial, failed, errors, methods}
        self.test_start_time = datetime.now()
        self.method_stats = defaultdict(lambda: {'success': 0, 'partial': 0, 'failed': 0})  # Track by method

    def phase1_scrape_news(self):
        """Phase 1: Scrape news for all test queries"""
        logger.info("=" * 80)
        logger.info("PHASE 1: NEWS SCRAPING - Testing Indian Stock Market Queries")
        logger.info("=" * 80)

        logger.info(f"Queries to test: {len(self.TEST_QUERIES)}")
        for i, query in enumerate(self.TEST_QUERIES, 1):
            logger.info(f"\n[{i}/{len(self.TEST_QUERIES)}] Query: {query}")

            try:
                result = scrape_news(
                    query=query,
                    region="IN",
                    period="7d",
                    max_results=15,
                    language="en"
                )

                articles = result.get('articles', [])
                logger.info(f"Found {len(articles)} articles")

                # Track articles and sources
                for article in articles:
                    source = article.get('media', 'Unknown').strip()
                    url = article.get('link', '')

                    self.all_articles.append({
                        'query': query,
                        'title': article.get('title', ''),
                        'source': source,
                        'url': url,
                        'date': article.get('date', ''),
                        'desc': article.get('desc', '')
                    })

                    if source and url:
                        self.source_frequency[source] += 1
                        if url not in self.source_articles[source]:
                            self.source_articles[source].append(url)

                logger.trace(f"Collected articles from sources: {[a.get('media', 'Unknown') for a in articles[:5]]}")

            except Exception as e:
                logger.error(f"Failed to scrape news for query '{query}': {str(e)}")

        logger.info(f"\n--- Phase 1 Summary ---")
        logger.info(f"Total articles collected: {len(self.all_articles)}")
        logger.info(f"Unique sources found: {len(self.source_frequency)}")
        logger.info(f"Top 10 sources by frequency:")
        for source, count in self.source_frequency.most_common(10):
            logger.info(f"  {source}: {count} articles")

    def phase2_test_extraction(self):
        """Phase 2: Test article extraction for each source"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2: EXTRACTION TESTING - Testing Article Extraction by Source")
        logger.info("=" * 80)

        # Test top 20 sources by frequency
        top_sources = [source for source, _ in self.source_frequency.most_common(20)]
        logger.info(f"Testing extraction for top {len(top_sources)} sources")

        for i, source in enumerate(top_sources, 1):
            logger.info(f"\n[{i}/{len(top_sources)}] Testing source: {source}")

            urls = self.source_articles[source][:2]  # Test up to 2 URLs per source
            logger.debug(f"Testing {len(urls)} articles from {source}")

            success_count = 0
            partial_count = 0
            failed_count = 0
            errors = []
            methods_used = []

            for j, url in enumerate(urls, 1):
                logger.trace(f"[{j}/{len(urls)}] Extracting: {url[:80]}...")

                try:
                    result = extract_article(url, language='en', perform_nlp=False)
                    text_length = len(result.get('text', ''))
                    extraction_method = result.get('extraction_method', 'unknown')
                    methods_used.append(extraction_method)

                    if text_length > 200:
                        logger.debug(f"SUCCESS: Extracted {text_length} chars from {source} (via {extraction_method})")
                        success_count += 1
                        self.method_stats[extraction_method]['success'] += 1
                    elif text_length > 50:
                        logger.debug(f"PARTIAL: Extracted only {text_length} chars from {source} (via {extraction_method})")
                        partial_count += 1
                        self.method_stats[extraction_method]['partial'] += 1
                    else:
                        logger.debug(f"FAILED: Text too short ({text_length} chars) from {source} (via {extraction_method})")
                        failed_count += 1
                        self.method_stats[extraction_method]['failed'] += 1
                        errors.append("text_too_short")

                except Exception as e:
                    error_type = type(e).__name__
                    logger.warning(f"FAILED: {error_type} from {source}: {str(e)[:100]}")
                    failed_count += 1
                    self.method_stats['failed_to_extract']['failed'] += 1
                    errors.append(error_type)

                # Delay between requests (rate limiting)
                time.sleep(1)

            # Store results
            self.extraction_results[source] = {
                'success': success_count,
                'partial': partial_count,
                'failed': failed_count,
                'errors': errors,
                'methods_used': methods_used,
                'total_tested': len(urls)
            }

            total = success_count + partial_count + failed_count
            if total > 0:
                success_rate = (success_count / total) * 100
                logger.info(f"Result: {success_count} success, {partial_count} partial, {failed_count} failed ({success_rate:.0f}% success)")

        logger.info(f"\n--- Phase 2 Summary ---")
        logger.info(f"Sources tested: {len(self.extraction_results)}")

    def phase3_generate_report(self):
        """Phase 3: Generate comprehensive analysis report"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3: ANALYSIS AND REPORT GENERATION")
        logger.info("=" * 80)

        # Section 1: Overview
        logger.info("\n[SECTION 1] TEST OVERVIEW")
        logger.info(f"Test Start Time: {self.test_start_time.isoformat()}")
        logger.info(f"Test Queries Executed: {len(self.TEST_QUERIES)}")
        logger.info(f"Total Articles Collected: {len(self.all_articles)}")
        logger.info(f"Unique Sources Found: {len(self.source_frequency)}")

        # Section 2: Source Frequency
        logger.info("\n[SECTION 2] SOURCE FREQUENCY ANALYSIS (Top 20)")
        logger.info(f"{'Rank':<5} {'Source':<40} {'Count':<10} {'Pct':<8}")
        logger.info("-" * 65)

        total_articles = sum(self.source_frequency.values())
        for rank, (source, count) in enumerate(self.source_frequency.most_common(20), 1):
            pct = (count / total_articles * 100) if total_articles > 0 else 0
            logger.info(f"{rank:<5} {source:<40} {count:<10} {pct:>6.1f}%")

        # Section 3: Extraction Results Summary
        if self.extraction_results:
            logger.info("\n[SECTION 3] EXTRACTION TEST RESULTS SUMMARY")
            logger.info(f"{'Source':<40} {'Success':<10} {'Partial':<10} {'Failed':<10} {'Rate':<8}")
            logger.info("-" * 80)

            total_success = 0
            total_partial = 0
            total_failed = 0
            total_tested = 0

            for source in sorted(self.extraction_results.keys()):
                result = self.extraction_results[source]
                success = result['success']
                partial = result['partial']
                failed = result['failed']
                total = result['total_tested']

                if total > 0:
                    success_rate = (success / total) * 100
                else:
                    success_rate = 0

                logger.info(f"{source:<40} {success:<10} {partial:<10} {failed:<10} {success_rate:>6.0f}%")

                total_success += success
                total_partial += partial
                total_failed += failed
                total_tested += total

            # Summary statistics
            logger.info("-" * 80)
            total_all = total_success + total_partial + total_failed
            if total_all > 0:
                overall_success_rate = (total_success / total_all) * 100
                overall_partial_rate = (total_partial / total_all) * 100
                overall_failed_rate = (total_failed / total_all) * 100
            else:
                overall_success_rate = overall_partial_rate = overall_failed_rate = 0

            logger.info(f"{'TOTAL':<40} {total_success:<10} {total_partial:<10} {total_failed:<10} {overall_success_rate:>6.0f}%")
            logger.info(f"\nExtraction Rate Breakdown:")
            logger.info(f"  Successful (>200 chars): {total_success}/{total_all} ({overall_success_rate:.1f}%)")
            logger.info(f"  Partial (50-200 chars): {total_partial}/{total_all} ({overall_partial_rate:.1f}%)")
            logger.info(f"  Failed (<50 chars or error): {total_failed}/{total_all} ({overall_failed_rate:.1f}%)")

            # Section 3.5: Extraction Method Statistics
            logger.info("\n[SECTION 3.5] EXTRACTION METHOD PERFORMANCE")
            if self.method_stats:
                logger.info(f"{'Method':<20} {'Success':<10} {'Partial':<10} {'Failed':<10} {'Success Rate':<15}")
                logger.info("-" * 65)
                for method, stats in sorted(self.method_stats.items()):
                    total_method = stats['success'] + stats['partial'] + stats['failed']
                    if total_method > 0:
                        method_success_rate = (stats['success'] / total_method) * 100
                    else:
                        method_success_rate = 0
                    logger.info(f"{method:<20} {stats['success']:<10} {stats['partial']:<10} {stats['failed']:<10} {method_success_rate:>13.0f}%")

            # Section 4: Reliable Sources (High frequency + High success)
            logger.info("\n[SECTION 4] RELIABLE SOURCES (Frequency >= 2 AND Success Rate >= 50%)")
            reliable = []
            for source, result in self.extraction_results.items():
                frequency = self.source_frequency[source]
                total = result['total_tested']
                if total > 0:
                    success_rate = (result['success'] / total) * 100
                else:
                    success_rate = 0

                if frequency >= 2 and success_rate >= 50:
                    reliable.append((source, frequency, success_rate, result['success']))

            if reliable:
                reliable.sort(key=lambda x: (-x[1], -x[2]))  # Sort by frequency desc, then success rate desc
                logger.info(f"Found {len(reliable)} reliable sources:")
                logger.info(f"{'Source':<40} {'Frequency':<12} {'Success':<12}")
                logger.info("-" * 65)
                for source, freq, success_rate, _ in reliable:
                    logger.info(f"{source:<40} {freq:<12} {success_rate:>10.0f}%")
            else:
                logger.info("No highly reliable sources found. Consider using diverse sources.")

            # Section 5: Problematic Sources
            logger.info("\n[SECTION 5] PROBLEMATIC SOURCES (Failed Extraction)")
            problematic = []
            for source, result in self.extraction_results.items():
                if result['failed'] > 0:
                    frequency = self.source_frequency[source]
                    total = result['total_tested']
                    if total > 0:
                        fail_rate = (result['failed'] / total) * 100
                    else:
                        fail_rate = 0

                    error_types = Counter(result['errors'])
                    problematic.append((source, frequency, fail_rate, dict(error_types)))

            if problematic:
                problematic.sort(key=lambda x: -x[2])  # Sort by failure rate desc
                logger.info(f"Found {len(problematic)} problematic sources:")
                logger.info(f"{'Source':<40} {'Frequency':<12} {'Fail Rate':<12} {'Error Types':<20}")
                logger.info("-" * 85)
                for source, freq, fail_rate, errors in problematic:
                    error_str = ", ".join([f"{k}({v})" for k, v in errors.items()])[:20]
                    logger.info(f"{source:<40} {freq:<12} {fail_rate:>10.0f}% {error_str:<20}")
            else:
                logger.info("No problematic sources found. All tested sources had some success.")

            # Section 6: Recommendations
            logger.info("\n[SECTION 6] RECOMMENDATIONS FOR PROMPT ENHANCEMENT")
            logger.info(f"\nBased on test results:")

            if reliable:
                logger.info(f"\n1. PREFERRED SOURCES (recommend first in searches):")
                top_reliable = reliable[:5]
                for source, _, _, _ in top_reliable:
                    logger.info(f"   - {source}")

                logger.info(f"\n2. SOURCE PREFERENCE IN SYSTEM PROMPT:")
                logger.info(f"   When analyzing news, prioritize articles from reliable financial sources:")
                logger.info(f"   Preferred: {', '.join([s[0] for s in top_reliable])}")
                logger.info(f"   These sources have {overall_success_rate:.0f}% extraction success rate")

            if problematic:
                logger.info(f"\n3. SOURCES TO AVOID or USE WITH CAUTION:")
                worst_sources = [s[0] for s in problematic[:3]]
                logger.info(f"   These sources have extraction issues:")
                logger.info(f"   {', '.join(worst_sources)}")

            logger.info(f"\n4. NEXT STEPS:")
            logger.info(f"   a) Update system prompts to prefer reliable sources")
            logger.info(f"   b) Add region='IN' parameter for Indian market news queries")
            logger.info(f"   c) Consider fallback extraction methods for problematic sites")
            logger.info(f"   d) Monitor cache hit rate for repeated queries")

        # Section 7: Test Statistics
        logger.info("\n[SECTION 7] TEST STATISTICS")
        test_end_time = datetime.now()
        test_duration = (test_end_time - self.test_start_time).total_seconds()
        logger.info(f"Test Duration: {test_duration:.1f} seconds")
        logger.info(f"Average time per query: {test_duration / len(self.TEST_QUERIES):.1f} seconds")

    def run(self):
        """Run complete test suite"""
        logger.separator('=', 80)
        logger.info("NEWS SOURCE RELIABILITY TEST SUITE")
        logger.info(f"Start Time: {self.test_start_time.isoformat()}")
        logger.separator('=', 80)

        try:
            # Execute phases
            self.phase1_scrape_news()
            self.phase2_test_extraction()
            self.phase3_generate_report()

            # Final summary
            logger.info("\n" + "=" * 80)
            logger.info("TEST SUITE COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Check logs folder for detailed execution log")
            logger.info(f"Run time: {(datetime.now() - self.test_start_time).total_seconds():.1f} seconds")

        except Exception as e:
            logger.error(f"Test suite failed: {str(e)}", exc_info=True)
            raise


def run_test_suite():
    """Convenience function to run the test suite"""
    test = NewsSourceReliabilityTest()
    test.run()


if __name__ == "__main__":
    run_test_suite()
