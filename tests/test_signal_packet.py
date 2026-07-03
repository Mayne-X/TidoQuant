"""Test signal packet construction and debate transcript."""
from src.core.signal_packet import MayneResult, SignalPacket


class TestMayneResult:
    def test_defaults(self):
        r = MayneResult(score=65, passed_gate=True, direction="long")
        assert r.score == 65
        assert r.passed_gate
        assert r.direction == "long"
        assert r.ote_points == 0
        assert r.tf_scores == {}

    def test_minimal(self):
        r = MayneResult(score=0, passed_gate=False, direction="short")
        assert not r.passed_gate


class TestSignalPacket:
    def make_minimal_packet(self) -> SignalPacket:
        mayne = MayneResult(score=72, passed_gate=True, direction="long",
                            ote_points=20, sweep_points=25, fvg_points=25)
        return SignalPacket(
            symbol="BTCUSDT",
            direction="long",
            mayne=mayne,
            entry_price=50000.0,
            current_price=50100.0,
        )

    def test_basic_fields(self):
        p = self.make_minimal_packet()
        assert p.symbol == "BTCUSDT"
        # With no manager_confidence, total = mayne.score + 0
        assert p.total_confidence == 72

    def test_debate_transcript_empty(self):
        p = self.make_minimal_packet()
        assert p.debate_transcript() == ""

    def test_debate_transcript_full(self):
        p = self.make_minimal_packet()
        p.bull_thesis_r1 = "Strong momentum"
        p.bull_score_r1 = 80
        p.bear_rebuttal_r1 = "Overbought risk"
        p.bear_score_r1 = 60
        transcript = p.debate_transcript()
        assert "BULL R1" in transcript
        assert "BEAR R1" in transcript
        assert "Strong momentum" in transcript

    def test_manager_confidence_in_total(self):
        p = self.make_minimal_packet()
        p.manager_confidence = 85
        # total = mayne.score + manager_confidence
        assert p.total_confidence == 72 + 85

    def test_agent_errors(self):
        p = self.make_minimal_packet()
        p.agent_errors.append("researcher_crash: timeout")
        assert len(p.agent_errors) == 1

    def test_tf_candles_dict(self):
        p = self.make_minimal_packet()
        p.tf_candles = {"1h": [], "4h": [], "12h": []}
        assert len(p.tf_candles) == 3
