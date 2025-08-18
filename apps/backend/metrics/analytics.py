import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import math

from config import Config
from state.portfolio import PortfolioSimulator, Trade, Position

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Performance metrics for portfolio analysis"""
    
    def __init__(self):
        self.total_return: float = 0.0
        self.annualized_return: float = 0.0
        self.volatility: float = 0.0
        self.sharpe_ratio: float = 0.0
        self.sortino_ratio: float = 0.0
        self.max_drawdown: float = 0.0
        self.calmar_ratio: float = 0.0
        self.win_rate: float = 0.0
        self.profit_factor: float = 0.0
        self.avg_win: float = 0.0
        self.avg_loss: float = 0.0
        self.largest_win: float = 0.0
        self.largest_loss: float = 0.0

class RiskMetrics:
    """Risk metrics for portfolio analysis"""
    
    def __init__(self):
        self.var_95: float = 0.0  # Value at Risk (95% confidence)
        self.var_99: float = 0.0  # Value at Risk (99% confidence)
        self.expected_shortfall: float = 0.0
        self.beta: float = 0.0
        self.correlation: float = 0.0
        self.treynor_ratio: float = 0.0
        self.information_ratio: float = 0.0
        self.ulcer_index: float = 0.0
        self.gain_to_pain_ratio: float = 0.0

class PortfolioAnalytics:
    """Advanced portfolio analytics and performance metrics"""
    
    def __init__(self, portfolio_simulator: PortfolioSimulator):
        self.portfolio = portfolio_simulator
        self.performance_metrics = PerformanceMetrics()
        self.risk_metrics = RiskMetrics()
        self.last_calculation = None
        
    def calculate_all_metrics(self) -> Dict:
        """Calculate all performance and risk metrics"""
        try:
            # Calculate performance metrics
            self._calculate_performance_metrics()
            
            # Calculate risk metrics
            self._calculate_risk_metrics()
            
            # Calculate asset allocation metrics
            allocation_metrics = self._calculate_allocation_metrics()
            
            # Calculate arbitrage performance metrics
            arbitrage_metrics = self._calculate_arbitrage_metrics()
            
            # Calculate correlation and diversification metrics
            diversification_metrics = self._calculate_diversification_metrics()
            
            self.last_calculation = datetime.now(timezone.utc)
            
            return {
                "timestamp": self.last_calculation.isoformat(),
                "performance": self._performance_to_dict(),
                "risk": self._risk_to_dict(),
                "allocation": allocation_metrics,
                "arbitrage": arbitrage_metrics,
                "diversification": diversification_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate metrics: {e}")
            return {}
    
    def _calculate_performance_metrics(self):
        """Calculate performance metrics from portfolio data"""
        try:
            trades = self.portfolio.trades
            if not trades:
                return
            
            # Calculate returns
            initial_balance = float(self.portfolio.initial_balance_usd)
            current_value = float(self.portfolio.get_portfolio_summary()["total_market_value_usd"])
            
            self.performance_metrics.total_return = (current_value - initial_balance) / initial_balance
            
            # Calculate time-weighted return
            if len(trades) > 1:
                first_trade = trades[0].timestamp
                last_trade = trades[-1].timestamp
                days = (last_trade - first_trade).days
                if days > 0:
                    self.performance_metrics.annualized_return = (
                        (1 + self.performance_metrics.total_return) ** (365 / days) - 1
                    )
            
            # Calculate volatility from trade returns
            if len(trades) > 10:
                returns = self._calculate_trade_returns(trades)
                if returns:
                    self.performance_metrics.volatility = np.std(returns) * math.sqrt(365 * 24 * 60)  # Annualized
                    
                    # Calculate Sharpe ratio (assuming 0% risk-free rate for crypto)
                    if self.performance_metrics.volatility > 0:
                        self.performance_metrics.sharpe_ratio = (
                            self.performance_metrics.annualized_return / self.performance_metrics.volatility
                        )
                    
                    # Calculate Sortino ratio (downside deviation)
                    downside_returns = [r for r in returns if r < 0]
                    if downside_returns:
                        downside_deviation = np.std(downside_returns) * math.sqrt(365 * 24 * 60)
                        if downside_deviation > 0:
                            self.performance_metrics.sortino_ratio = (
                                self.performance_metrics.annualized_return / downside_deviation
                            )
            
            # Calculate drawdown
            self.performance_metrics.max_drawdown = self._calculate_max_drawdown(trades)
            
            # Calculate Calmar ratio
            if self.performance_metrics.max_drawdown > 0:
                self.performance_metrics.calmar_ratio = (
                    self.performance_metrics.annualized_return / self.performance_metrics.max_drawdown
                )
            
            # Calculate trade statistics
            self._calculate_trade_statistics(trades)
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
    
    def _calculate_risk_metrics(self):
        """Calculate risk metrics from portfolio data"""
        try:
            trades = self.portfolio.trades
            if not trades or len(trades) < 10:
                return
            
            returns = self._calculate_trade_returns(trades)
            if not returns:
                return
            
            # Calculate Value at Risk
            sorted_returns = sorted(returns)
            var_95_index = int(len(sorted_returns) * 0.05)
            var_99_index = int(len(sorted_returns) * 0.01)
            
            if var_95_index < len(sorted_returns):
                self.risk_metrics.var_95 = sorted_returns[var_95_index]
            if var_99_index < len(sorted_returns):
                self.risk_metrics.var_99 = sorted_returns[var_99_index]
            
            # Calculate Expected Shortfall (Conditional VaR)
            if var_95_index < len(sorted_returns):
                tail_returns = sorted_returns[:var_95_index]
                if tail_returns:
                    self.risk_metrics.expected_shortfall = np.mean(tail_returns)
            
            # Calculate Beta (market sensitivity - simplified)
            # In a real implementation, this would be vs a market index
            self.risk_metrics.beta = 1.0  # Placeholder
            
            # Calculate correlation (portfolio vs market - simplified)
            self.risk_metrics.correlation = 0.85  # Placeholder
            
            # Calculate Treynor ratio
            if self.risk_metrics.beta > 0:
                self.risk_metrics.treynor_ratio = (
                    self.performance_metrics.annualized_return / self.risk_metrics.beta
                )
            
            # Calculate Information ratio
            benchmark_return = 0.0  # Placeholder - would be market return
            tracking_error = self.performance_metrics.volatility  # Simplified
            if tracking_error > 0:
                self.risk_metrics.information_ratio = (
                    (self.performance_metrics.annualized_return - benchmark_return) / tracking_error
                )
            
            # Calculate Ulcer Index (measure of downside risk)
            self.risk_metrics.ulcer_index = self._calculate_ulcer_index(trades)
            
            # Calculate Gain-to-Pain ratio
            if self.performance_metrics.avg_loss != 0:
                self.risk_metrics.gain_to_pain_ratio = (
                    self.performance_metrics.avg_win / abs(self.performance_metrics.avg_loss)
                )
            
        except Exception as e:
            logger.error(f"Failed to calculate risk metrics: {e}")
    
    def _calculate_allocation_metrics(self) -> Dict:
        """Calculate asset allocation and concentration metrics"""
        try:
            summary = self.portfolio.get_portfolio_summary()
            positions = summary["positions"]
            
            total_value = summary["total_market_value_usd"]
            if total_value == 0:
                return {}
            
            allocation_data = {}
            concentration_metrics = {
                "herfindahl_index": 0.0,
                "largest_position_pct": 0.0,
                "top_3_concentration": 0.0,
                "diversification_score": 0.0
            }
            
            # Calculate allocation percentages
            position_sizes = []
            for symbol, position in positions.items():
                if position["market_value_usd"] > 0:
                    pct = (position["market_value_usd"] / total_value) * 100
                    allocation_data[symbol] = {
                        "allocation_pct": pct,
                        "market_value_usd": position["market_value_usd"],
                        "unrealized_pnl_usd": position["unrealized_pnl_usd"],
                        "pnl_pct": position["pnl_pct"]
                    }
                    position_sizes.append(pct)
            
            # Calculate concentration metrics
            if position_sizes:
                # Herfindahl-Hirschman Index (concentration measure)
                concentration_metrics["herfindahl_index"] = sum(pct ** 2 for pct in position_sizes)
                
                # Largest position percentage
                concentration_metrics["largest_position_pct"] = max(position_sizes)
                
                # Top 3 concentration
                sorted_sizes = sorted(position_sizes, reverse=True)
                concentration_metrics["top_3_concentration"] = sum(sorted_sizes[:3])
                
                # Diversification score (0-100, higher = more diversified)
                concentration_metrics["diversification_score"] = max(0, 100 - concentration_metrics["herfindahl_index"])
            
            return {
                "allocations": allocation_data,
                "concentration": concentration_metrics,
                "total_positions": len([p for p in positions.values() if p["market_value_usd"] > 0])
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate allocation metrics: {e}")
            return {}
    
    def _calculate_arbitrage_metrics(self) -> Dict:
        """Calculate arbitrage-specific performance metrics"""
        try:
            trades = self.portfolio.trades
            arbitrage_trades = [t for t in trades if t.arbitrage_profit_bps]
            
            if not arbitrage_trades:
                return {
                    "total_arbitrage_trades": 0,
                    "success_rate": 0.0,
                    "avg_profit_bps": 0.0,
                    "total_profit_usd": 0.0
                }
            
            # Calculate arbitrage metrics
            total_profit = sum(float(t.arbitrage_profit_bps) for t in arbitrage_trades)
            avg_profit_bps = total_profit / len(arbitrage_trades)
            
            # Calculate success rate (profitable trades)
            profitable_trades = [t for t in arbitrage_trades if float(t.arbitrage_profit_bps) > 0]
            success_rate = len(profitable_trades) / len(arbitrage_trades) * 100
            
            # Calculate total profit in USD
            total_profit_usd = sum(float(t.arbitrage_profit_bps) * float(t.total_usd) / 10000 for t in arbitrage_trades)
            
            return {
                "total_arbitrage_trades": len(arbitrage_trades),
                "success_rate": success_rate,
                "avg_profit_bps": avg_profit_bps,
                "total_profit_usd": total_profit_usd,
                "profitable_trades": len(profitable_trades),
                "unprofitable_trades": len(arbitrage_trades) - len(profitable_trades)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate arbitrage metrics: {e}")
            return {}
    
    def _calculate_diversification_metrics(self) -> Dict:
        """Calculate portfolio diversification metrics"""
        try:
            summary = self.portfolio.get_portfolio_summary()
            positions = summary["positions"]
            
            # Calculate effective number of positions
            active_positions = [p for p in positions.values() if p["market_value_usd"] > 0]
            if not active_positions:
                return {"effective_positions": 0, "diversification_benefit": 0.0}
            
            # Calculate weights
            total_value = summary["total_market_value_usd"]
            weights = [p["market_value_usd"] / total_value for p in active_positions]
            
            # Effective number of positions (inverse of Herfindahl index)
            herfindahl = sum(w ** 2 for w in weights)
            effective_positions = 1 / herfindahl if herfindahl > 0 else 0
            
            # Diversification benefit (how much risk is reduced vs single asset)
            diversification_benefit = max(0, (len(active_positions) - effective_positions) / len(active_positions) * 100)
            
            return {
                "effective_positions": effective_positions,
                "diversification_benefit": diversification_benefit,
                "position_count": len(active_positions)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate diversification metrics: {e}")
            return {}
    
    def _calculate_trade_returns(self, trades: List[Trade]) -> List[float]:
        """Calculate returns from trade sequence"""
        try:
            if len(trades) < 2:
                return []
            
            returns = []
            for i in range(1, len(trades)):
                prev_trade = trades[i-1]
                curr_trade = trades[i]
                
                # Calculate return based on trade P&L
                if prev_trade.side == "buy" and curr_trade.side == "sell":
                    # Simple return calculation
                    if prev_trade.total_usd > 0:
                        return_pct = (float(curr_trade.total_usd) - float(prev_trade.total_usd)) / float(prev_trade.total_usd)
                        returns.append(return_pct)
            
            return returns
            
        except Exception as e:
            logger.error(f"Failed to calculate trade returns: {e}")
            return []
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """Calculate maximum drawdown from trade sequence"""
        try:
            if not trades:
                return 0.0
            
            # Calculate cumulative P&L over time
            cumulative_pnl = []
            running_pnl = 0.0
            
            for trade in trades:
                if trade.arbitrage_profit_bps:
                    profit_usd = float(trade.arbitrage_profit_bps) * float(trade.total_usd) / 10000
                    running_pnl += profit_usd
                else:
                    # Estimate P&L from trade
                    if trade.side == "sell":
                        running_pnl += float(trade.total_usd) * 0.001  # Assume 0.1% profit
                    else:
                        running_pnl -= float(trade.total_usd) * 0.001  # Assume 0.1% cost
                
                cumulative_pnl.append(running_pnl)
            
            # Calculate drawdown
            peak = cumulative_pnl[0]
            max_drawdown = 0.0
            
            for pnl in cumulative_pnl:
                if pnl > peak:
                    peak = pnl
                drawdown = (peak - pnl) / peak if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        except Exception as e:
            logger.error(f"Failed to calculate max drawdown: {e}")
            return 0.0
    
    def _calculate_trade_statistics(self, trades: List[Trade]):
        """Calculate trade statistics"""
        try:
            if not trades:
                return
            
            # Separate profitable and unprofitable trades
            profitable_trades = []
            unprofitable_trades = []
            
            for trade in trades:
                if trade.arbitrage_profit_bps and float(trade.arbitrage_profit_bps) > 0:
                    profitable_trades.append(trade)
                else:
                    unprofitable_trades.append(trade)
            
            # Calculate win rate
            self.performance_metrics.win_rate = len(profitable_trades) / len(trades) * 100
            
            # Calculate profit factor
            if unprofitable_trades:
                total_profit = sum(float(t.arbitrage_profit_bps) * float(t.total_usd) / 10000 for t in profitable_trades)
                total_loss = abs(sum(float(t.arbitrage_profit_bps) * float(t.total_usd) / 10000 for t in unprofitable_trades))
                self.performance_metrics.profit_factor = total_profit / total_loss if total_loss > 0 else 0
            
            # Calculate average win/loss
            if profitable_trades:
                self.performance_metrics.avg_win = np.mean([
                    float(t.arbitrage_profit_bps) * float(t.total_usd) / 10000 for t in profitable_trades
                ])
            
            if unprofitable_trades:
                self.performance_metrics.avg_loss = np.mean([
                    float(t.arbitrage_profit_bps) * float(t.total_usd) / 10000 for t in unprofitable_trades
                ])
            
            # Calculate largest win/loss
            if profitable_trades:
                self.performance_metrics.largest_win = max([
                    float(t.arbitrage_profit_bps) * float(t.total_usd) / 10000 for t in profitable_trades
                ])
            
            if unprofitable_trades:
                self.performance_metrics.largest_loss = min([
                    float(t.arbitrage_profit_bps) * float(t.total_usd) / 10000 for t in unprofitable_trades
                ])
            
        except Exception as e:
            logger.error(f"Failed to calculate trade statistics: {e}")
    
    def _calculate_ulcer_index(self, trades: List[Trade]) -> float:
        """Calculate Ulcer Index (measure of downside risk)"""
        try:
            if len(trades) < 10:
                return 0.0
            
            # Calculate drawdowns over time
            cumulative_pnl = []
            running_pnl = 0.0
            
            for trade in trades:
                if trade.arbitrage_profit_bps:
                    profit_usd = float(trade.arbitrage_profit_bps) * float(trade.total_usd) / 10000
                    running_pnl += profit_usd
                cumulative_pnl.append(running_pnl)
            
            # Calculate drawdowns
            peak = cumulative_pnl[0]
            drawdowns = []
            
            for pnl in cumulative_pnl:
                if pnl > peak:
                    peak = pnl
                drawdown = (peak - pnl) / peak if peak > 0 else 0
                drawdowns.append(drawdown)
            
            # Calculate Ulcer Index
            if drawdowns:
                ulcer_index = math.sqrt(sum(dd ** 2 for dd in drawdowns) / len(drawdowns))
                return ulcer_index
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate ulcer index: {e}")
            return 0.0
    
    def _performance_to_dict(self) -> Dict:
        """Convert performance metrics to dictionary"""
        return {
            "total_return": self.performance_metrics.total_return,
            "annualized_return": self.performance_metrics.annualized_return,
            "volatility": self.performance_metrics.volatility,
            "sharpe_ratio": self.performance_metrics.sharpe_ratio,
            "sortino_ratio": self.performance_metrics.sortino_ratio,
            "max_drawdown": self.performance_metrics.max_drawdown,
            "calmar_ratio": self.performance_metrics.calmar_ratio,
            "win_rate": self.performance_metrics.win_rate,
            "profit_factor": self.performance_metrics.profit_factor,
            "avg_win": self.performance_metrics.avg_win,
            "avg_loss": self.performance_metrics.avg_loss,
            "largest_win": self.performance_metrics.largest_win,
            "largest_loss": self.performance_metrics.largest_loss
        }
    
    def _risk_to_dict(self) -> Dict:
        """Convert risk metrics to dictionary"""
        return {
            "var_95": self.risk_metrics.var_95,
            "var_99": self.risk_metrics.var_99,
            "expected_shortfall": self.risk_metrics.expected_shortfall,
            "beta": self.risk_metrics.beta,
            "correlation": self.risk_metrics.correlation,
            "treynor_ratio": self.risk_metrics.treynor_ratio,
            "information_ratio": self.risk_metrics.information_ratio,
            "ulcer_index": self.risk_metrics.ulcer_index,
            "gain_to_pain_ratio": self.risk_metrics.gain_to_pain_ratio
        }
