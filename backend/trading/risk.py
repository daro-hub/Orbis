from dataclasses import dataclass, field


@dataclass
class RiskConfig:
    max_position_size_pct: float = 10.0  # max % of capital per trade
    max_daily_loss_pct: float = 5.0  # stop trading if daily loss exceeds this %
    max_open_positions: int = 3
    default_stop_loss_pct: float = 2.0
    default_take_profit_pct: float = 4.0


class RiskManager:
    """Basic risk management layer."""

    def __init__(self, config: RiskConfig = RiskConfig()):
        self.config = config
        self.daily_pnl: float = 0.0
        self.open_positions_count: int = 0

    def can_open_position(self, capital: float, position_value: float) -> tuple[bool, str]:
        position_pct = (position_value / capital) * 100
        if position_pct > self.config.max_position_size_pct:
            return False, f"Position size {position_pct:.1f}% exceeds max {self.config.max_position_size_pct}%"

        if self.open_positions_count >= self.config.max_open_positions:
            return False, f"Max open positions ({self.config.max_open_positions}) reached"

        daily_loss_pct = abs(self.daily_pnl / capital * 100) if self.daily_pnl < 0 else 0
        if daily_loss_pct >= self.config.max_daily_loss_pct:
            return False, f"Daily loss limit ({self.config.max_daily_loss_pct}%) reached"

        return True, "OK"

    def calculate_position_size(self, capital: float, price: float) -> float:
        max_value = capital * (self.config.max_position_size_pct / 100)
        return max_value / price

    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        sl_offset = entry_price * (self.config.default_stop_loss_pct / 100)
        if side == "buy":
            return entry_price - sl_offset
        return entry_price + sl_offset

    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        tp_offset = entry_price * (self.config.default_take_profit_pct / 100)
        if side == "buy":
            return entry_price + tp_offset
        return entry_price - tp_offset

    def update_pnl(self, pnl: float):
        self.daily_pnl += pnl

    def reset_daily(self):
        self.daily_pnl = 0.0
