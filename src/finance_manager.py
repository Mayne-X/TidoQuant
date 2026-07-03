"""Finance Manager.

Handles position sizing, leverage, risk management.
"""
from .config import RISK_BRACKETS, STARTING_EQUITY

def calculate_position(score: int, equity: float) -> dict:
    # Find bracket
    for bracket in RISK_BRACKETS:
        if bracket.score_min <= score <= bracket.score_max:
            risk_amt = equity * bracket.risk_pct
            return {
                "risk_amount": risk_amt,
                "leverage": bracket.leverage,
                "position_size": risk_amt * bracket.leverage
            }
    return {"risk_amount": 0, "leverage": 1, "position_size": 0}
