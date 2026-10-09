import conftest
import os
import tempfile
import unittest

from engine import (
    BookLevel,
    L2OrderBook,
    MarketTrade,
    MicrostructureConfig,
    MicrostructureEngine,
    Quote,
    Signal,
)
from portfolio import (
    FactorModel,
    InstrumentSpec,
    Portfolio,
    PortfolioLimits,
    PortfolioError,
    QuoteMark,
)
from itch_handler import (
    ItchAddOrder,
    ItchOrderBookTracker,
    ItchOrderCancel,
    ItchOrderDelete,
    ItchOrderExecuted,
    encode_itch_add_order,
    encode_itch_order_cancel,
    encode_itch_order_delete,
    encode_itch_order_executed,
    encode_mold_packet,
    parse_itch_message,
    parse_mold_packet,
    read_pcap_payloads,
    write_synthetic_pcap,
)


class QuantMicrostructureTests(unittest.TestCase):
    def test_multi_asset_portfolio_notionals_and_contract_multipliers(self):
        es_spec = InstrumentSpec(
            instrument_id=1,
            symbol="ES",
            tick_size=0.25,
            multiplier=50.0,
            taker_fee_bps=0.2,
        )
        aapl_spec = InstrumentSpec(
            instrument_id=2,
            symbol="AAPL",
            tick_size=0.01,
            multiplier=1.0,
            taker_fee_bps=0.5,
        )
        limits = PortfolioLimits(
            max_net_position=1000,
            max_gross_position=2000,
            max_gross_notional_ticks=10_000_000,
            max_concentration_ticks=5_000_000,
            max_loss_ticks=500_000,
            allow_short=True,
        )
        portfolio = Portfolio(limits, specs={1: es_spec, 2: aapl_spec})

        portfolio.apply_fill(instrument_id=1, side=1, quantity=2, price_ticks=5000)
        portfolio.apply_fill(instrument_id=2, side=1, quantity=100, price_ticks=220)

        snapshot = portfolio.snapshot({1: 5050, 2: 225})
        self.assertEqual(snapshot["net_position"], 102)
        self.assertGreater(snapshot["gross_notional_cash"], 100_000)
        self.assertAlmostEqual(snapshot["realized_pnl_cash"], 0.0)
        self.assertGreater(snapshot["unrealized_pnl_cash"], 0.0)
        self.assertGreater(snapshot["total_fees_paid_cash"], 0.0)

    def test_factor_model_variance_and_var_limits(self):
        factors = ["Market", "Tech"]
        loadings = {
            1: {"Market": 1.2, "Tech": 0.8},
            2: {"Market": 0.7, "Tech": 0.2},
        }
        cov = {
            "Market": {"Market": 0.04, "Tech": 0.02},
            "Tech": {"Market": 0.02, "Tech": 0.06},
        }
        spec_var = {1: 0.01, 2: 0.01}
        model = FactorModel(factors, loadings, cov, spec_var)

        limits = PortfolioLimits(
            max_net_position=1000,
            max_gross_position=1000,
            max_gross_notional_ticks=1_000_000,
            max_concentration_ticks=1_000_000,
            max_loss_ticks=100_000,
            allow_short=True,
            max_expected_shortfall_cash=5000.0,
        )
        spec1 = InstrumentSpec(instrument_id=1, tick_size=1.0, multiplier=1.0)
        portfolio = Portfolio(limits, specs={1: spec1}, factor_model=model)

        portfolio.apply_fill(1, 1, 50, 100)
        snapshot = portfolio.snapshot({1: 100})
        self.assertIn("factor_metrics", snapshot)
        self.assertGreater(snapshot["factor_metrics"]["expected_shortfall_cash"], 0.0)

        ok, reason = portfolio.validate_order(1, 1, 500, 100)
        self.assertFalse(ok)
        self.assertEqual(reason, "expected_shortfall_limit")

    def test_short_borrow_locates_and_rejection_when_unlocated(self):
        meme_spec = InstrumentSpec(
            instrument_id=99,
            symbol="MEME",
            locate_required=True,
        )
        limits = PortfolioLimits(
            max_net_position=100,
            max_gross_position=100,
            max_gross_notional_ticks=50_000,
            max_concentration_ticks=50_000,
            max_loss_ticks=10_000,
            allow_short=True,
        )
        portfolio = Portfolio(limits, specs={99: meme_spec})

        ok, reason = portfolio.validate_order(99, -1, 50, 100)
        self.assertFalse(ok)
        self.assertEqual(reason, "short_locate_insufficient")

        with self.assertRaises(PortfolioError):
            portfolio.apply_fill(99, -1, 50, 100)

        portfolio.register_locate(99, 50)
        ok, reason = portfolio.validate_order(99, -1, 50, 100)
        self.assertTrue(ok)
        self.assertEqual(reason, "approved")

        pos = portfolio.apply_fill(99, -1, 50, 100)
        self.assertEqual(pos.quantity, -50)

    def test_mid_quote_and_stale_mark_detection(self):
        limits = PortfolioLimits(100, 100, 100000, 50000, 10000)
        portfolio = Portfolio(limits)
        portfolio.apply_fill(1, 1, 10, 100)

        quote = QuoteMark(bid_ticks=102, ask_ticks=106, timestamp_ns=1_000_000)
        snap_mid = portfolio.snapshot({1: quote}, mark_method="mid")
        self.assertEqual(snap_mid["unrealized_pnl_ticks"], 40)

        snap_liq = portfolio.snapshot({1: quote}, mark_method="liquidation")
        self.assertEqual(snap_liq["unrealized_pnl_ticks"], 20)

        snap_stale = portfolio.snapshot(
            {1: quote},
            mark_method="mid",
            current_time_ns=10_000_000,
            max_stale_ns=5_000_000,
        )
        self.assertIn(1, snap_stale["stale_positions"])

    def test_microstructure_depth_walking_and_slippage(self):
        engine = MicrostructureEngine(max_position=500)
        quote = Quote(
            timestamp_ns=1000,
            bid_ticks=99,
            ask_ticks=101,
            bids=[(99, 100), (98, 200)],
            asks=[(101, 50), (102, 50), (103, 100)],
        )
        engine.on_quote(quote)

        signal = Signal(timestamp_ns=1500, side=1, quantity=80, order_type="market")
        fills = engine.submit_order(signal)

        self.assertEqual(len(fills), 2)
        self.assertEqual(fills[0].price_ticks, 101)
        self.assertEqual(fills[0].quantity, 50)
        self.assertEqual(fills[1].price_ticks, 102)
        self.assertEqual(fills[1].quantity, 30)
        self.assertEqual(engine.position, 80)
        self.assertGreater(fills[1].slippage_ticks, fills[0].slippage_ticks)

    def test_passive_queue_priority_and_decay(self):
        config = MicrostructureConfig(
            wire_latency_ns=100,
            engine_latency_ns=50,
            queue_cancellation_rate=0.5,
            maker_fee_bps=-0.1,
            adverse_selection_alpha=0.5,
        )
        engine = MicrostructureEngine(max_position=100, config=config)
        quote = Quote(
            timestamp_ns=1000,
            bid_ticks=100,
            ask_ticks=102,
            bid_size=100,
            ask_size=100,
        )
        engine.on_quote(quote)

        signal = Signal(
            timestamp_ns=1010,
            side=1,
            quantity=10,
            order_type="limit",
            limit_price_ticks=100,
        )
        fills = engine.submit_order(signal)
        self.assertEqual(len(fills), 0)
        self.assertEqual(len(engine.resting_orders), 1)

        trade1 = MarketTrade(
            timestamp_ns=1500,
            price_ticks=100,
            quantity=30,
            aggressor_side=-1,
        )
        fills1 = engine.on_market_trade(trade1)
        self.assertEqual(len(fills1), 0)

        trade2 = MarketTrade(
            timestamp_ns=1600,
            price_ticks=100,
            quantity=40,
            aggressor_side=-1,
        )
        fills2 = engine.on_market_trade(trade2)
        self.assertEqual(len(fills2), 1)
        self.assertEqual(fills2[0].quantity, 10)
        self.assertTrue(fills2[0].is_maker)
        self.assertLess(fills2[0].fee_ticks, 0.0)
        self.assertGreater(fills2[0].adverse_selection_cost_ticks, 0.0)

    def test_multi_packet_bursts_and_latency_offsets(self):
        engine = MicrostructureEngine(max_position=100)
        events = [
            Quote(timestamp_ns=5000, bid_ticks=100, ask_ticks=102),
            Quote(timestamp_ns=5000, bid_ticks=101, ask_ticks=103),
            Signal(timestamp_ns=5010, side=1, quantity=5, order_type="market", latency_ns=200),
        ]
        fills = engine.run_simulation(events)
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0].price_ticks, 103)
        self.assertEqual(fills[0].timestamp_ns, 5210)

    def test_binary_itch_and_moldudp64_packet_parsing(self):
        msg_add1 = encode_itch_add_order(1, 1000000, 101, "B", 100, "AAPL", 15000)
        msg_add2 = encode_itch_add_order(1, 1000010, 102, "S", 200, "AAPL", 15050)
        packet_bytes = encode_mold_packet("SESSION01", 1, [msg_add1, msg_add2])

        packet = parse_mold_packet(packet_bytes)
        self.assertEqual(packet.session, "SESSION01")
        self.assertEqual(packet.sequence_number, 1)
        self.assertEqual(packet.count, 2)

        tracker = ItchOrderBookTracker("AAPL")
        for raw in packet.messages:
            msg = parse_itch_message(raw)
            tracker.process(msg)

        self.assertEqual(tracker.best_bid, 15000)
        self.assertEqual(tracker.best_ask, 15050)

        msg_exec = encode_itch_order_executed(1, 1000020, 101, 40, 999)
        tracker.process(parse_itch_message(msg_exec))
        self.assertEqual(tracker.orders[101].shares, 60)
        self.assertEqual(tracker.bids[15000], 60)

        msg_cancel = encode_itch_order_cancel(1, 1000030, 102, 50)
        tracker.process(parse_itch_message(msg_cancel))
        self.assertEqual(tracker.asks[15050], 150)

        msg_del = encode_itch_order_delete(1, 1000040, 101)
        tracker.process(parse_itch_message(msg_del))
        self.assertNotIn(101, tracker.orders)
        self.assertNotIn(15000, tracker.bids)

    def test_synthetic_pcap_write_and_read(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pcap_path = os.path.join(temp_dir, "test_market_data.pcap")
            msg1 = encode_itch_add_order(1, 10000, 1, "B", 50, "SPY", 45000)
            pkt1 = encode_mold_packet("SESS1", 1, [msg1])
            write_synthetic_pcap(pcap_path, [pkt1])

            payloads = read_pcap_payloads(pcap_path)
            self.assertEqual(len(payloads), 1)
            parsed_pkt = parse_mold_packet(payloads[0])
            self.assertEqual(parsed_pkt.sequence_number, 1)
            parsed_msg = parse_itch_message(parsed_pkt.messages[0])
            self.assertIsInstance(parsed_msg, ItchAddOrder)
            self.assertEqual(parsed_msg.stock, "SPY")


if __name__ == "__main__":
    unittest.main()
