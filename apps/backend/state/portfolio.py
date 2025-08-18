import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_DOWN

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Individual asset position in portfolio"""
    symbol: str
    quantity: Decimal = Decimal('0')
    avg_price_usd: Decimal = Decimal('0')
    total_cost_usd: Decimal = Decimal('0')
    unrealized_pnl_usd: Decimal = Decimal('0')
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def market_value_usd(self) -> Decimal:
        """Current market value of position"""
        return self.quantity * self.avg_price_usd
    
    @property
    def pnl_pct(self) -> Decimal:
        """Unrealized P&L as percentage"""
        if self.total_cost_usd == 0:
            return Decimal('0')
        return (self.unrealized_pnl_usd / self.total_cost_usd) * 100

@dataclass
class Trade:
    """Record of a completed trade"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: Decimal
    price_usd: Decimal
    total_usd: Decimal
    venue: str
    timestamp: datetime
    fees_usd: Decimal = Decimal('0')
    arbitrage_profit_bps: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)

@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity"""
    symbol: str
    buy_venue: str
    sell_venue: str
    buy_price: Decimal
    sell_price: Decimal
    spread_bps: Decimal
    estimated_profit_usd: Decimal
    max_trade_size: Decimal
    confidence_score: float
    timestamp: datetime
    expires_at: datetime
    
    def is_expired(self) -> bool:
        """Check if opportunity has expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_profitable(self, min_profit_bps: Decimal) -> bool:
        """Check if opportunity meets minimum profit threshold"""
        return self.spread_bps >= min_profit_bps

class PortfolioSimulator:
    """Paper trading portfolio simulator with arbitrage execution"""
    
    def __init__(self, initial_balance_usd: float = None):
        self.initial_balance_usd = Decimal(str(initial_balance_usd or Config.INITIAL_PORTFOLIO_USD))
        self.cash_usd = self.initial_balance_usd
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.arbitrage_opportunities: List[ArbitrageOpportunity] = []
        self.total_pnl_usd = Decimal('0')
        self.total_fees_usd = Decimal('0')
        self.trades_executed = 0
        self.arbitrage_trades = 0
        
        # Initialize positions for all configured assets
        for symbol in Config.SYMBOLS:
            self.positions[symbol] = Position(symbol=symbol)
        
        logger.info(f"Portfolio simulator initialized with ${self.initial_balance_usd:,.2f}")
    
    def get_portfolio_summary(self) -> dict:
        """Get comprehensive portfolio summary"""
        total_market_value = self.cash_usd
        total_cost_basis = Decimal('0')
        
        for position in self.positions.values():
            total_market_value += position.market_value_usd
            total_cost_basis += position.total_cost_usd
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "initial_balance_usd": float(self.initial_balance_usd),
            "cash_usd": float(self.cash_usd),
            "total_market_value_usd": float(total_market_value),
            "total_cost_basis_usd": float(total_cost_basis),
            "total_pnl_usd": float(self.total_pnl_usd),
            "total_pnl_pct": float((self.total_pnl_usd / self.initial_balance_usd) * 100),
            "total_fees_usd": float(self.total_fees_usd),
            "trades_executed": self.trades_executed,
            "arbitrage_trades": self.arbitrage_trades,
            "positions": {
                symbol: {
                    "quantity": float(pos.quantity),
                    "avg_price_usd": float(pos.avg_price_usd),
                    "market_value_usd": float(pos.market_value_usd),
                    "unrealized_pnl_usd": float(pos.unrealized_pnl_usd),
                    "pnl_pct": float(pos.pnl_pct)
                }
                for symbol, pos in self.positions.items()
            }
        }
    
    def execute_arbitrage(self, opportunity: ArbitrageOpportunity, trade_size_usd: float) -> Optional[Trade]:
        """Execute arbitrage trade if profitable"""
        try:
            if opportunity.is_expired():
                logger.warning(f"Arbitrage opportunity expired: {opportunity.symbol}")
                return None
            
            if not opportunity.is_profitable(Config.MIN_PROFIT_THRESHOLD_BPS):
                logger.info(f"Opportunity below profit threshold: {opportunity.spread_bps} bps")
                return None
            
            # Check if we have enough cash
            if self.cash_usd < Decimal(str(trade_size_usd)):
                logger.warning(f"Insufficient cash for arbitrage: ${trade_size_usd} > ${self.cash_usd}")
                return None
            
            # Calculate trade details
            trade_size_decimal = Decimal(str(trade_size_usd))
            quantity = trade_size_decimal / opportunity.buy_price
            
            # Execute buy on lower-priced venue
            buy_trade = self._execute_trade(
                symbol=opportunity.symbol,
                side="buy",
                quantity=quantity,
                price_usd=opportunity.buy_price,
                venue=opportunity.buy_venue,
                is_arbitrage=True,
                arbitrage_profit_bps=opportunity.spread_bps
            )
            
            if buy_trade:
                # Execute sell on higher-priced venue
                sell_trade = self._execute_trade(
                    symbol=opportunity.symbol,
                    side="sell",
                    quantity=quantity,
                    price_usd=opportunity.sell_price,
                    venue=opportunity.sell_venue,
                    is_arbitrage=True,
                    arbitrage_profit_bps=opportunity.spread_bps
                )
                
                if sell_trade:
                    self.arbitrage_trades += 1
                    logger.info(f"Arbitrage executed: {opportunity.symbol} {opportunity.spread_bps} bps profit")
                    return sell_trade  # Return the sell trade as the completion
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to execute arbitrage: {e}")
            return None
    
    def _execute_trade(self, symbol: str, side: str, quantity: Decimal, 
                       price_usd: Decimal, venue: str, is_arbitrage: bool = False,
                       arbitrage_profit_bps: Optional[Decimal] = None) -> Optional[Trade]:
        """Execute a single trade and update portfolio"""
        try:
            trade_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{side}_{symbol}_{venue}"
            total_usd = quantity * price_usd
            
            # Calculate fees (simplified - could be made more sophisticated)
            fees_usd = total_usd * Decimal('0.001')  # 0.1% fee
            
            # Update cash
            if side == "buy":
                if self.cash_usd < (total_usd + fees_usd):
                    logger.warning(f"Insufficient cash for buy: ${total_usd + fees_usd} > ${self.cash_usd}")
                    return None
                
                self.cash_usd -= (total_usd + fees_usd)
                
                # Update position
                position = self.positions[symbol]
                if position.quantity == 0:
                    position.avg_price_usd = price_usd
                else:
                    # Weighted average price
                    total_cost = position.total_cost_usd + total_usd
                    total_quantity = position.quantity + quantity
                    position.avg_price_usd = total_cost / total_quantity
                
                position.quantity += quantity
                position.total_cost_usd += total_usd
                
            else:  # sell
                position = self.positions[symbol]
                if position.quantity < quantity:
                    logger.warning(f"Insufficient {symbol} for sell: {quantity} > {position.quantity}")
                    return None
                
                self.cash_usd += (total_usd - fees_usd)
                
                # Update position
                position.quantity -= quantity
                if position.quantity == 0:
                    position.avg_price_usd = Decimal('0')
                    position.total_cost_usd = Decimal('0')
                else:
                    # Reduce cost basis proportionally
                    reduction_ratio = quantity / (position.quantity + quantity)
                    position.total_cost_usd *= (1 - reduction_ratio)
            
            # Update position timestamp
            position.last_updated = datetime.now(timezone.utc)
            
            # Create trade record
            trade = Trade(
                id=trade_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price_usd=price_usd,
                total_usd=total_usd,
                venue=venue,
                timestamp=datetime.now(timezone.utc),
                fees_usd=fees_usd,
                arbitrage_profit_bps=arbitrage_profit_bps
            )
            
            self.trades.append(trade)
            self.trades_executed += 1
            self.total_fees_usd += fees_usd
            
            # Update P&L
            self._update_pnl()
            
            logger.info(f"Trade executed: {side} {quantity} {symbol} @ ${price_usd} on {venue}")
            return trade
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return None
    
    def _update_pnl(self):
        """Update portfolio P&L"""
        total_pnl = Decimal('0')
        
        for position in self.positions.values():
            if position.quantity > 0:
                # For now, use avg price as current price (in real implementation, this would be live market price)
                current_price = position.avg_price_usd
                market_value = position.quantity * current_price
                position.unrealized_pnl_usd = market_value - position.total_cost_usd
                total_pnl += position.unrealized_pnl_usd
        
        self.total_pnl_usd = total_pnl
    
    def add_arbitrage_opportunity(self, opportunity: ArbitrageOpportunity):
        """Add detected arbitrage opportunity to portfolio"""
        # Remove expired opportunities
        self.arbitrage_opportunities = [opp for opp in self.arbitrage_opportunities if not opp.is_expired()]
        
        # Add new opportunity
        self.arbitrage_opportunities.append(opportunity)
        
        # Keep only recent opportunities (last 100)
        if len(self.arbitrage_opportunities) > 100:
            self.arbitrage_opportunities = self.arbitrage_opportunities[-100:]
    
    def get_arbitrage_opportunities(self, symbol: Optional[str] = None) -> List[ArbitrageOpportunity]:
        """Get current arbitrage opportunities"""
        opportunities = [opp for opp in self.arbitrage_opportunities if not opp.is_expired()]
        
        if symbol:
            opportunities = [opp for opp in opportunities if opp.symbol == symbol]
        
        return sorted(opportunities, key=lambda x: x.spread_bps, reverse=True)
    
    def reset_portfolio(self):
        """Reset portfolio to initial state"""
        self.cash_usd = self.initial_balance_usd
        self.positions = {}
        self.trades = []
        self.arbitrage_opportunities = []
        self.total_pnl_usd = Decimal('0')
        self.total_fees_usd = Decimal('0')
        self.trades_executed = 0
        self.arbitrage_trades = 0
        
        # Reinitialize positions
        for symbol in Config.SYMBOLS:
            self.positions[symbol] = Position(symbol=symbol)
        
        logger.info("Portfolio reset to initial state")
