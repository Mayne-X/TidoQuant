"""Test binance client with mocked HTTP responses."""
from unittest.mock import Mock, patch
import pytest
from src.binance_client import BinanceFuturesClient, Candle


class TestBinanceClient:
    @patch.object(BinanceFuturesClient, "_get")
    def test_klines_parsing(self, mock_get):
        mock_get.return_value = [
            [1000000, "50000", "51000", "49000", "50500", "1000",
             2000000, "50000000", 500, "1000", "25000000", "0"],
        ]
        client = BinanceFuturesClient()
        candles = client.klines("BTCUSDT", "1h", limit=1)
        assert len(candles) == 1
        c = candles[0]
        assert isinstance(c, Candle)
        assert c.open == 50000.0
        assert c.high == 51000.0
        assert c.low == 49000.0
        assert c.close == 50500.0
        assert c.volume == 1000.0

    @patch.object(BinanceFuturesClient, "_get")
    def test_mark_price(self, mock_get):
        mock_get.return_value = {
            "symbol": "BTCUSDT",
            "markPrice": "50100.0",
            "indexPrice": "50050.0",
            "lastFundingRate": "0.0001",
            "nextFundingTime": "2000000",
        }
        client = BinanceFuturesClient()
        info = client.mark_price("BTCUSDT")
        assert info["mark"] == 50100.0
        assert info["rate"] == 0.0001

    @patch.object(BinanceFuturesClient, "_get")
    def test_funding_rate(self, mock_get):
        mock_get.return_value = [{"fundingRate": "0.0001", "fundingTime": "1000000"}]
        client = BinanceFuturesClient()
        info = client.funding_rate("BTCUSDT")
        assert info["rate"] == 0.0001

    @patch.object(BinanceFuturesClient, "_get")
    def test_open_interest_history(self, mock_get):
        mock_get.return_value = [
            {"sumOpenInterest": "50000", "sumOpenInterestValue": "2500000000",
             "timestamp": "1000000"}
        ]
        client = BinanceFuturesClient()
        rows = client.open_interest_history("BTCUSDT")
        assert len(rows) == 1
        assert float(rows[0]["sumOpenInterest"]) == 50000.0

    def test_candle_open_time_property(self):
        c = Candle(
            open_time_ms=1719878400000,
            open=100, high=101, low=99, close=100,
            volume=1000, close_time_ms=1719882000000,
            quote_volume=100000, trades=500,
        )
        dt = c.open_time
        assert dt.year == 2024
        assert dt.month == 7

    @patch.object(BinanceFuturesClient, "_get")
    def test_empty_funding_rate(self, mock_get):
        mock_get.return_value = []
        client = BinanceFuturesClient()
        info = client.funding_rate("BTCUSDT")
        assert info["rate"] == 0.0
        assert info["time"] == 0
