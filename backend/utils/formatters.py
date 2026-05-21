"""
Utility functions for formatting data in QuantMind Pro.
QuantMind Pro v3.0
"""

import re
from datetime import datetime
from typing import Any, Union


def format_currency(amount: float, currency: str = "INR") -> str:
    """
    Format a number as currency with appropriate symbol and grouping.
    format_currency(amount: float, currency: str = "INR") -> str: "₹1,23,456.78" or "$1,234.56"

    Args:
        amount: The amount to format
        currency: Currency code (INR, USD, etc.)

    Returns:
        Formatted currency string
    """
    if currency.upper() == "INR":
        # Indian numbering system: lakhs and crores
        abs_amount = abs(amount)
        sign = "-" if amount < 0 else ""
        if abs_amount >= 10000000:  # 1 crore
            formatted = f"{abs_amount / 10000000:.2f}Cr"
        elif abs_amount >= 100000:  # 1 lakh
            formatted = f"{abs_amount / 100000:.2f}L"
        else:
            formatted = f"{abs_amount:,.2f}"
        # Remove trailing zeros and decimal if not needed
        if formatted.endswith(".00"):
            formatted = formatted[:-3]
        elif formatted.endswith(".0"):
            formatted = formatted[:-2]
        # Add currency symbol
        if currency.upper() == "INR":
            return f"{sign}₹{formatted}"
        else:
            return f"{sign}{currency} {formatted}"
    else:
        # Default to US formatting
        abs_amount = abs(amount)
        sign = "-" if amount < 0 else ""
        formatted = f"{abs_amount:,.2f}"
        if formatted.endswith(".00"):
            formatted = formatted[:-3]
        elif formatted.endswith(".0"):
            formatted = formatted[:-2]
        return f"{sign}{currency} {formatted}"


def format_percentage(value: float, decimal_places: int = 2) -> str:
    """
    Format a number as a percentage.
    format_percentage(value: float, decimal_places: int = 2) -> str: "+12.45%" or "-3.21%"

    Args:
        value: The value to format (as a decimal, e.g., 0.1234 for 12.34%)
        decimal_places: Number of decimal places to show

    Returns:
        Formatted percentage string
    """
    # Convert decimal to percentage
    percentage = value * 100
    sign = "+" if percentage >= 0 else ""
    # Format with specified decimal places
    formatted = f"{sign}{percentage:.{decimal_places}f}%"
    return formatted


def format_large_number(n: float) -> str:
    """
    Format a large number with appropriate suffixes.
    format_large_number(n: float) -> str: "1.2Cr", "45.6L", "1.2B", "890M" (Indian + US notation)

    Args:
        n: The number to format

    Returns:
        Formatted large number string
    """
    abs_n = abs(n)
    sign = "-" if n < 0 else ""

    if abs_n >= 10000000:  # 1 crore or higher
        if abs_n >= 1000000000:  # 1 billion or higher
            formatted = f"{abs_n / 1000000000:.1f}B"
        else:
            formatted = f"{abs_n / 10000000:.1f}Cr"
    elif abs_n >= 100000:  # 1 lakh or higher
        formatted = f"{abs_n / 100000:.1f}L"
    elif abs_n >= 1000:  # 1 thousand or higher
        formatted = f"{abs_n / 1000:.1f}K"
    else:
        formatted = f"{abs_n:.1f}"

    # Remove trailing zeros and decimal if not needed
    if formatted.endswith(".0"):
        formatted = formatted[:-2]

    return f"{sign}{formatted}"


def format_market_cap(value: float, exchange: str) -> str:
    """
    Format market cap based on exchange (auto-detects INR vs USD).
    format_market_cap(value: float, exchange: str) -> str: auto-detects INR vs USD

    Args:
        value: Market cap value
        exchange: Exchange identifier (e.g., "NSE", "BSE", "NASDAQ", "NYSE")

    Returns:
        Formatted market cap string
    """
    # Determine currency based on exchange
    if exchange.upper() in ["NSE", "BSE"]:
        currency = "INR"
    else:
        currency = "USD"

    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if currency == "INR":
        # Indian numbering system
        if abs_value >= 10000000:  # 1 crore
            if abs_value >= 1000000000:  # 100 crores = 1 billion
                formatted = f"{abs_value / 10000000:.1f}Cr"
            else:
                formatted = f"{abs_value / 10000000:.1f}Cr"
        elif abs_value >= 100000:  # 1 lakh
            formatted = f"{abs_value / 100000:.1f}L"
        else:
            formatted = f"{abs_value:,.0f}"
    else:
        # US numbering system
        if abs_value >= 1000000000:  # 1 billion
            formatted = f"{abs_value / 1000000000:.1f}B"
        elif abs_value >= 1000000:  # 1 million
            formatted = f"{abs_value / 1000000:.1f}M"
        elif abs_value >= 1000:  # 1 thousand
            formatted = f"{abs_value / 1000:.1f}K"
        else:
            formatted = f"{abs_value:,.0f}"

    # Remove trailing zeros and decimal if not needed
    if formatted.endswith(".0"):
        formatted = formatted[:-2]

    if currency == "INR":
        return f"{sign}₹{formatted}"
    else:
        return f"{sign}${formatted}"


def normalize_symbol(symbol: str, exchange: str) -> str:
    """
    Normalize symbol for yfinance compatibility.
    normalize_symbol(symbol: str, exchange: str) -> str: "RELIANCE" → "RELIANCE.NS" for yfinance

    Args:
        symbol: Stock symbol (e.g., "RELIANCE")
        exchange: Exchange identifier (e.g., "NSE", "BSE")

    Returns:
        Normalized symbol for yfinance
    """
    symbol = symbol.upper().strip()

    if exchange.upper() == "NSE":
        if not symbol.endswith(".NS"):
            return f"{symbol}.NS"
        return symbol
    elif exchange.upper() == "BSE":
        if not symbol.endswith(".BO"):
            return f"{symbol}.BO"
        return symbol
    else:
        # For other exchanges, return as-is
        return symbol


def denormalize_symbol(symbol: str) -> str:
    """
    Denormalize symbol from yfinance format.
    denormalize_symbol(symbol: str) -> str: "RELIANCE.NS" → "RELIANCE"

    Args:
        symbol: Normalized symbol (e.g., "RELIANCE.NS")

    Returns:
        Denormalized symbol
    """
    symbol = symbol.upper().strip()

    if symbol.endswith(".NS"):
        return symbol[:-3]
    elif symbol.endswith(".BO"):
        return symbol[:-3]
    else:
        return symbol


def date_to_unix(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp for TradingView Lightweight Charts.
    date_to_unix(dt: datetime) -> int: for TradingView Lightweight Charts

    Args:
        dt: datetime object

    Returns:
        Unix timestamp (seconds)
    """
    return int(dt.timestamp())


def unix_to_date(ts: int) -> datetime:
    """
    Convert Unix timestamp to datetime.
    unix_to_date(ts: int) -> datetime

    Args:
        ts: Unix timestamp (seconds)

    Returns:
        datetime object
    """
    return datetime.fromtimestamp(ts)


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert any value to float.
    safe_float(value: Any, default: float = 0.0) -> float: converts safely, returns default on error

    Args:
        value: Value to convert to float
        default: Default value to return if conversion fails

    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def truncate_text(text: str, max_chars: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.
    truncate_text(text: str, max_chars: int, suffix: str = "...") -> str

    Args:
        text: Text to truncate
        max_chars: Maximum characters allowed
        suffix: Suffix to append when truncating (default "...")

    Returns:
        Truncated text string
    """
    if not text or len(text) <= max_chars:
        return text

    # Ensure we have room for the suffix
    if len(suffix) >= max_chars:
        return suffix[:max_chars]

    return text[:max_chars - len(suffix)] + suffix