"""
Replacement Stock Finder

Orchestrates screening and market research to find replacement stocks
when positions are exited.
"""

import json
from typing import Dict, Any, List, Optional
from configparser import ConfigParser

from utils.logger import get_logger
from agents.stock_screening_agent import run_stock_screening
from agents.market_research_agent import run_market_research

logger = get_logger(__name__)


class ReplacementStockFinder:
    """Find replacement stocks using enhanced screening with market context"""

    def __init__(self, config: ConfigParser = None):
        """
        Initialize replacement finder

        Args:
            config: ConfigParser instance. If None, loads from config.ini
        """
        if config is None:
            config = ConfigParser()
            config.read('config.ini')

        self.config = config
        logger.info("ReplacementStockFinder initialized")

    def find_replacement(
        self,
        exited_stock: Dict[str, Any],
        portfolio_profile: str,
        available_capital: float,
        current_holdings: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find replacement stock using two-phase approach

        Args:
            exited_stock: Stock that was exited (with ticker, sector, etc.)
            portfolio_profile: 'aggressive', 'moderate', or 'defensive'
            available_capital: Available cash for new position
            current_holdings: List of current active stocks

        Returns:
            Stock entry data dict or None if no suitable candidate found
        """
        ticker = exited_stock.get('ticker', 'UNKNOWN')
        sector = exited_stock.get('sector', 'Unknown')

        logger.info("="*80)
        logger.info(f"FINDING REPLACEMENT FOR: {ticker} ({sector})")
        logger.info(f"  Profile: {portfolio_profile}")
        logger.info(f"  Available Capital: Rs. {available_capital:,.0f}")
        logger.info(f"  Current Holdings: {len(current_holdings)} stocks")
        logger.info("="*80)

        # PHASE 1: Market Context Analysis
        logger.info("\n[Phase 1/4] Analyzing market context...")
        market_context = self._analyze_market_context(sector, portfolio_profile)

        if not market_context:
            logger.warning("Failed to analyze market context")
            return None

        # PHASE 2: Build Screening Query
        logger.info("\n[Phase 2/4] Building screening query...")
        avoid_sectors = self._get_overweight_sectors(current_holdings)
        target_sector = sector if market_context.get('sector_favorable', False) else None

        screening_query = self._build_screening_query(
            profile=portfolio_profile,
            market_context=market_context,
            avoid_sectors=avoid_sectors,
            target_sector=target_sector
        )

        logger.info(f"Screening query: {screening_query[:200]}...")

        # PHASE 3: Run Screening
        logger.info("\n[Phase 3/4] Running stock screening...")
        candidates = self._run_screening(screening_query)

        if not candidates:
            logger.warning("No replacement candidates found from screening")
            return None

        logger.info(f"Found {len(candidates)} candidates")

        # PHASE 4: Select Best Candidate
        logger.info("\n[Phase 4/4] Selecting best candidate...")
        best_candidate = self._select_best_candidate(
            candidates=candidates,
            market_context=market_context,
            available_capital=available_capital,
            profile=portfolio_profile
        )

        if not best_candidate:
            logger.warning("No suitable candidate after selection")
            return None

        # Prepare stock entry data
        stock_data = self._prepare_stock_entry_data(
            stock=best_candidate,
            profile=portfolio_profile,
            exited_stock=exited_stock
        )

        logger.info(f"✓ Selected replacement: {stock_data['name']} ({stock_data['ticker']})")
        logger.info("="*80)

        return stock_data

    def _analyze_market_context(
        self,
        exited_sector: str,
        portfolio_profile: str
    ) -> Optional[Dict[str, Any]]:
        """
        Use market_research_agent to assess current market conditions

        Args:
            exited_sector: Sector of the exited stock
            portfolio_profile: Portfolio profile

        Returns:
            Dict with market context or None on failure
        """
        query = f"""
Analyze the current Indian market environment for portfolio rebalancing:

1. Overall market trend: Is the market currently bullish, bearish, or sideways?
2. Sector performance: Which sectors are showing strength and momentum?
3. {exited_sector} sector outlook: Is the {exited_sector} sector favorable for re-entry right now?
4. Sector recommendations: Which 2-3 sectors show the best opportunities for a {portfolio_profile} investor?
5. Key risks: Any major macro risks or concerns to be aware of?

Provide a structured analysis with your assessment and confidence level.
        """

        try:
            analysis = run_market_research(query, model='mid')

            # Parse response - look for key indicators
            analysis_lower = analysis.lower()

            # Determine market trend
            if 'bullish' in analysis_lower or 'uptrend' in analysis_lower:
                market_trend = 'bullish'
            elif 'bearish' in analysis_lower or 'downtrend' in analysis_lower:
                market_trend = 'bearish'
            else:
                market_trend = 'sideways'

            # Check if exited sector is favorable
            sector_favorable = (
                exited_sector.lower() in analysis_lower and
                ('favorable' in analysis_lower or 'positive' in analysis_lower or 'strength' in analysis_lower)
            )

            # Extract favorable sectors (simplified extraction)
            favorable_sectors = []
            common_sectors = ['IT', 'Pharma', 'Banking', 'Auto', 'FMCG', 'Metals', 'Energy', 'Realty']
            for sector in common_sectors:
                if sector.lower() in analysis_lower and (
                    'strong' in analysis_lower or 'favorable' in analysis_lower or 'positive' in analysis_lower
                ):
                    favorable_sectors.append(sector)

            # If no sectors found, include exited sector if favorable
            if not favorable_sectors and sector_favorable:
                favorable_sectors = [exited_sector]

            context = {
                'market_trend': market_trend,
                'favorable_sectors': favorable_sectors[:3],  # Top 3
                'sector_favorable': sector_favorable,
                'confidence': 75,  # Default confidence
                'full_analysis': analysis
            }

            logger.info(
                f"Market context: trend={market_trend}, "
                f"favorable_sectors={favorable_sectors}, "
                f"sector_favorable={sector_favorable}"
            )

            return context

        except Exception as e:
            logger.error(f"Failed to analyze market context: {e}")
            return None

    def _build_screening_query(
        self,
        profile: str,
        market_context: Dict[str, Any],
        avoid_sectors: List[str],
        target_sector: Optional[str]
    ) -> str:
        """
        Build context-aware screening query

        Args:
            profile: Portfolio profile
            market_context: Market context from analysis
            avoid_sectors: Sectors to avoid (over-allocated)
            target_sector: Preferred sector (optional)

        Returns:
            Screening query string
        """
        # Get risk parameters from config
        if profile == 'aggressive':
            base_criteria = "Market Capitalization > 5000 AND Return on equity > 20 AND Debt to equity < 1"
        elif profile == 'moderate':
            base_criteria = "Market Capitalization > 10000 AND Return on equity > 15 AND Debt to equity < 0.5"
        else:  # defensive
            base_criteria = "Market Capitalization > 20000 AND Return on equity > 12 AND Debt to equity < 0.3"

        # Build query components
        components = [
            f"Find 5-10 high-quality stocks for a {profile} portfolio.",
            f"\nScreening criteria: {base_criteria}"
        ]

        # Add sector preferences
        if target_sector:
            components.append(f"\nFocus on {target_sector} sector stocks.")
        elif market_context.get('favorable_sectors'):
            components.append(
                f"\nPrefer stocks from these sectors: {', '.join(market_context['favorable_sectors'])}."
            )

        # Add sector avoidance
        if avoid_sectors:
            components.append(f"\nExclude or deprioritize these sectors (over-allocated): {', '.join(avoid_sectors)}.")

        # Add market context
        components.append(
            f"\nMarket context: Current trend is {market_context.get('market_trend', 'neutral')}. "
            f"Look for stocks with strong fundamentals and positive momentum."
        )

        # Final ask
        components.append("\nReturn stocks with detailed financial metrics and rationale.")

        query = ''.join(components)
        return query

    def _run_screening(self, query: str) -> List[Dict[str, Any]]:
        """
        Run stock screening agent

        Args:
            query: Screening query

        Returns:
            List of candidate stocks
        """
        try:
            result = run_stock_screening(query, model='mid')

            # Extract stocks from result
            if isinstance(result, dict):
                candidates = result.get('stocks', [])
            elif isinstance(result, list):
                candidates = result
            elif isinstance(result, str):
                # String response might be an error or description
                logger.warning(f"Screening returned string response (likely no matches): {result[:200]}")
                candidates = []
            else:
                logger.warning(f"Unexpected screening result type: {type(result)}")
                logger.debug(f"Result content: {result}")
                candidates = []

            logger.info(f"Screening returned {len(candidates)} candidates")
            return candidates

        except Exception as e:
            logger.error(f"Failed to run screening: {e}")
            return []

    def _select_best_candidate(
        self,
        candidates: List[Dict[str, Any]],
        market_context: Dict[str, Any],
        available_capital: float,
        profile: str
    ) -> Optional[Dict[str, Any]]:
        """
        Select best replacement from candidates using scoring

        Args:
            candidates: List of candidate stocks
            market_context: Market context
            available_capital: Available capital
            profile: Portfolio profile

        Returns:
            Best candidate or None
        """
        if not candidates:
            return None

        scored_candidates = []

        for candidate in candidates:
            score = 0

            # Fundamental score (40%)
            roe = candidate.get('Return on equity', 0)
            if roe:
                score += min((roe / 30) * 40, 40)  # Cap at 30% ROE = full score

            # Sector alignment (30%)
            sector = candidate.get('sector', 'Unknown')
            if sector in market_context.get('favorable_sectors', []):
                score += 30

            # Valuation score (20%)
            pe = candidate.get('Price to Earning', 25)
            if pe:
                if pe < 15:
                    score += 20
                elif pe < 25:
                    score += 10

            # Price affordability (10%)
            price = candidate.get('CMP Rs.', 0)
            if price and price > 0:
                shares_possible = available_capital / price
                if shares_possible >= 10:  # Can buy at least 10 shares
                    score += 10
                elif shares_possible >= 5:
                    score += 5

            scored_candidates.append({
                'stock': candidate,
                'score': score
            })

            logger.debug(
                f"  {candidate.get('Name', 'Unknown')}: score={score:.1f} "
                f"(ROE={roe}, PE={pe}, Sector={sector})"
            )

        # Return highest scored
        if scored_candidates:
            best = max(scored_candidates, key=lambda x: x['score'])
            logger.info(
                f"Selected {best['stock'].get('Name', 'Unknown')} "
                f"(score: {best['score']:.1f})"
            )
            return best['stock']

        return None

    def _prepare_stock_entry_data(
        self,
        stock: Dict[str, Any],
        profile: str,
        exited_stock: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert screened stock to portfolio entry format

        Args:
            stock: Screened stock data
            profile: Portfolio profile
            exited_stock: Exited stock (for reference)

        Returns:
            Stock entry data dict
        """
        entry_price = stock.get('CMP Rs.', 0)

        # Get risk parameters from config
        if profile == 'aggressive':
            stop_loss_pct = self.config.getfloat('RISK_PARAMETERS', 'aggressive_stop_loss_pct', fallback=15)
            target_pct = self.config.getfloat('RISK_PARAMETERS', 'aggressive_target_min_pct', fallback=40)
        elif profile == 'moderate':
            stop_loss_pct = self.config.getfloat('RISK_PARAMETERS', 'moderate_stop_loss_pct', fallback=12)
            target_pct = self.config.getfloat('RISK_PARAMETERS', 'moderate_target_min_pct', fallback=25)
        else:  # defensive
            stop_loss_pct = self.config.getfloat('RISK_PARAMETERS', 'defensive_stop_loss_pct', fallback=8)
            target_pct = self.config.getfloat('RISK_PARAMETERS', 'defensive_target_min_pct', fallback=15)

        # Build rationale
        roe = stock.get('Return on equity', 'N/A')
        pe = stock.get('Price to Earning', 'N/A')
        market_cap = stock.get('Market Capitalization', 'N/A')

        rationale = (
            f"Replacement for {exited_stock.get('ticker', 'exited position')}. "
            f"Strong fundamentals: ROE={roe}%, PE={pe}, Market Cap={market_cap} Cr. "
            f"Selected through AI-powered screening with market context analysis."
        )

        return {
            'name': stock.get('Name', 'Unknown'),
            'ticker': stock.get('ticker', stock.get('Symbol', 'UNKNOWN')),
            'exchange': stock.get('exchange', stock.get('Exchange', 'NSE')),
            'sector': stock.get('sector', 'Unknown'),
            'entry_price': entry_price,
            'stop_loss_pct': stop_loss_pct,
            'stop_loss_price': entry_price * (1 - stop_loss_pct / 100),
            'target_pct': target_pct,
            'target_price': entry_price * (1 + target_pct / 100),
            'rationale': rationale,
            'key_metrics': {
                'ROE': roe,
                'PE': pe,
                'Market Cap': market_cap,
                'Debt to Equity': stock.get('Debt to equity', 'N/A')
            }
        }

    def _get_overweight_sectors(
        self,
        current_holdings: List[Dict[str, Any]],
        threshold_pct: float = 30.0
    ) -> List[str]:
        """
        Get sectors that are over-allocated

        Args:
            current_holdings: List of current stocks
            threshold_pct: Threshold for considering sector overweight

        Returns:
            List of overweight sector names
        """
        sector_allocations = {}

        for stock in current_holdings:
            if stock.get('allocation_pct', 0) > 0:
                sector = stock.get('sector', 'Unknown')
                sector_allocations[sector] = sector_allocations.get(sector, 0) + stock['allocation_pct']

        overweight = [
            sector for sector, allocation in sector_allocations.items()
            if allocation > threshold_pct
        ]

        if overweight:
            logger.info(f"Overweight sectors (>{threshold_pct}%): {overweight}")

        return overweight
