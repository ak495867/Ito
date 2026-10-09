from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import BinaryIO, Iterable, Iterator, List, Optional, Tuple


@dataclass(frozen=True)
class ItchSystemEvent:
    locate_id: int
    timestamp_ns: int
    event_code: str


@dataclass(frozen=True)
class ItchAddOrder:
    locate_id: int
    timestamp_ns: int
    order_ref: int
    side: str
    shares: int
    stock: str
    price_ticks: int


@dataclass(frozen=True)
class ItchOrderExecuted:
    locate_id: int
    timestamp_ns: int
    order_ref: int
    executed_shares: int
    match_number: int


@dataclass(frozen=True)
class ItchOrderCancel:
    locate_id: int
    timestamp_ns: int
    order_ref: int
    canceled_shares: int


@dataclass(frozen=True)
class ItchOrderDelete:
    locate_id: int
    timestamp_ns: int
    order_ref: int


@dataclass(frozen=True)
class MoldPacket:
    session: str
    sequence_number: int
    count: int
    messages: list[bytes]


def parse_uint48_be(raw: bytes) -> int:
    hi, lo = struct.unpack(">HI", raw)
    return (hi << 32) | lo


def encode_uint48_be(val: int) -> bytes:
    hi = (val >> 32) & 0xFFFF
    lo = val & 0xFFFFFFFF
    return struct.pack(">HI", hi, lo)


def encode_itch_add_order(
    locate_id: int,
    timestamp_ns: int,
    order_ref: int,
    side: str,
    shares: int,
    stock: str,
    price_ticks: int,
) -> bytes:
    ts_bytes = encode_uint48_be(timestamp_ns)
    stock_padded = stock.ljust(8)[:8].encode("ascii")
    side_byte = side.encode("ascii")[0:1]
    return b"A" + struct.pack(">HH", locate_id, 0) + ts_bytes + struct.pack(">QcI8sI", order_ref, side_byte, shares, stock_padded, price_ticks)


def encode_itch_order_executed(
    locate_id: int,
    timestamp_ns: int,
    order_ref: int,
    executed_shares: int,
    match_number: int,
) -> bytes:
    ts_bytes = encode_uint48_be(timestamp_ns)
    return b"E" + struct.pack(">HH", locate_id, 0) + ts_bytes + struct.pack(">QIQ", order_ref, executed_shares, match_number)


def encode_itch_order_cancel(
    locate_id: int,
    timestamp_ns: int,
    order_ref: int,
    canceled_shares: int,
) -> bytes:
    ts_bytes = encode_uint48_be(timestamp_ns)
    return b"X" + struct.pack(">HH", locate_id, 0) + ts_bytes + struct.pack(">QI", order_ref, canceled_shares)


def encode_itch_order_delete(
    locate_id: int,
    timestamp_ns: int,
    order_ref: int,
) -> bytes:
    ts_bytes = encode_uint48_be(timestamp_ns)
    return b"D" + struct.pack(">HH", locate_id, 0) + ts_bytes + struct.pack(">Q", order_ref)


def encode_mold_packet(session: str, sequence_number: int, messages: list[bytes]) -> bytes:
    sess_bytes = session.ljust(10)[:10].encode("ascii")
    header = struct.pack(">10sQH", sess_bytes, sequence_number, len(messages))
    payload = bytearray(header)
    for msg in messages:
        payload.extend(struct.pack(">H", len(msg)))
        payload.extend(msg)
    return bytes(payload)


def parse_mold_packet(raw: bytes) -> MoldPacket:
    if len(raw) < 20:
        raise ValueError("packet_too_short")
    sess_raw, seq, count = struct.unpack(">10sQH", raw[:20])
    session = sess_raw.decode("ascii", errors="replace").strip()
    offset = 20
    msgs: list[bytes] = []
    for _ in range(count):
        if offset + 2 > len(raw):
            break
        msg_len = struct.unpack(">H", raw[offset:offset+2])[0]
        offset += 2
        if offset + msg_len > len(raw):
            break
        msgs.append(raw[offset:offset+msg_len])
        offset += msg_len
    return MoldPacket(session=session, sequence_number=seq, count=count, messages=msgs)


def parse_itch_message(raw: bytes) -> object:
    if not raw:
        return None
    msg_type = chr(raw[0])
    if msg_type == "A" and len(raw) >= 36:
        locate, _ = struct.unpack(">HH", raw[1:5])
        ts = parse_uint48_be(raw[5:11])
        order_ref, side_byte, shares, stock_raw, price = struct.unpack(">QcI8sI", raw[11:36])
        return ItchAddOrder(
            locate_id=locate,
            timestamp_ns=ts,
            order_ref=order_ref,
            side=side_byte.decode("ascii"),
            shares=shares,
            stock=stock_raw.decode("ascii").strip(),
            price_ticks=price,
        )
    elif msg_type == "E" and len(raw) >= 31:
        locate, _ = struct.unpack(">HH", raw[1:5])
        ts = parse_uint48_be(raw[5:11])
        order_ref, executed_shares, match_num = struct.unpack(">QIQ", raw[11:31])
        return ItchOrderExecuted(
            locate_id=locate,
            timestamp_ns=ts,
            order_ref=order_ref,
            executed_shares=executed_shares,
            match_number=match_num,
        )
    elif msg_type == "X" and len(raw) >= 23:
        locate, _ = struct.unpack(">HH", raw[1:5])
        ts = parse_uint48_be(raw[5:11])
        order_ref, canceled_shares = struct.unpack(">QI", raw[11:23])
        return ItchOrderCancel(
            locate_id=locate,
            timestamp_ns=ts,
            order_ref=order_ref,
            canceled_shares=canceled_shares,
        )
    elif msg_type == "D" and len(raw) >= 19:
        locate, _ = struct.unpack(">HH", raw[1:5])
        ts = parse_uint48_be(raw[5:11])
        order_ref = struct.unpack(">Q", raw[11:19])[0]
        return ItchOrderDelete(
            locate_id=locate,
            timestamp_ns=ts,
            order_ref=order_ref,
        )
    return None


class ItchOrderBookTracker:
    def __init__(self, target_stock: str) -> None:
        self.target_stock = target_stock.strip()
        self.orders: dict[int, ItchAddOrder] = {}
        self.bids: dict[int, int] = {}
        self.asks: dict[int, int] = {}

    def process(self, msg: object) -> None:
        if isinstance(msg, ItchAddOrder):
            if msg.stock == self.target_stock:
                self.orders[msg.order_ref] = msg
                ladder = self.bids if msg.side == "B" else self.asks
                ladder[msg.price_ticks] = ladder.get(msg.price_ticks, 0) + msg.shares
        elif isinstance(msg, ItchOrderExecuted):
            order = self.orders.get(msg.order_ref)
            if order is not None:
                ladder = self.bids if order.side == "B" else self.asks
                ladder[order.price_ticks] = max(0, ladder.get(order.price_ticks, 0) - msg.executed_shares)
                if ladder[order.price_ticks] == 0:
                    del ladder[order.price_ticks]
                rem = order.shares - msg.executed_shares
                if rem <= 0:
                    del self.orders[msg.order_ref]
                else:
                    self.orders[msg.order_ref] = ItchAddOrder(
                        locate_id=order.locate_id,
                        timestamp_ns=order.timestamp_ns,
                        order_ref=order.order_ref,
                        side=order.side,
                        shares=rem,
                        stock=order.stock,
                        price_ticks=order.price_ticks,
                    )
        elif isinstance(msg, ItchOrderCancel):
            order = self.orders.get(msg.order_ref)
            if order is not None:
                ladder = self.bids if order.side == "B" else self.asks
                ladder[order.price_ticks] = max(0, ladder.get(order.price_ticks, 0) - msg.canceled_shares)
                if ladder[order.price_ticks] == 0:
                    del ladder[order.price_ticks]
                rem = order.shares - msg.canceled_shares
                if rem <= 0:
                    del self.orders[msg.order_ref]
                else:
                    self.orders[msg.order_ref] = ItchAddOrder(
                        locate_id=order.locate_id,
                        timestamp_ns=order.timestamp_ns,
                        order_ref=order.order_ref,
                        side=order.side,
                        shares=rem,
                        stock=order.stock,
                        price_ticks=order.price_ticks,
                    )
        elif isinstance(msg, ItchOrderDelete):
            order = self.orders.pop(msg.order_ref, None)
            if order is not None:
                ladder = self.bids if order.side == "B" else self.asks
                ladder[order.price_ticks] = max(0, ladder.get(order.price_ticks, 0) - order.shares)
                if ladder.get(order.price_ticks, 0) == 0 and order.price_ticks in ladder:
                    del ladder[order.price_ticks]

    @property
    def best_bid(self) -> int:
        return max(self.bids.keys(), default=0)

    @property
    def best_ask(self) -> int:
        return min(self.asks.keys(), default=0)

    def depth_ladders(self) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        bids = sorted(self.bids.items(), key=lambda x: -x[0])
        asks = sorted(self.asks.items(), key=lambda x: x[0])
        return bids, asks


def write_synthetic_pcap(filepath: str, packets_payloads: list[bytes]) -> None:
    pcap_hdr = struct.pack(
        "<IHHiIII",
        0xA1B2C3D4,
        2,
        4,
        0,
        0,
        65535,
        1,
    )
    with open(filepath, "wb") as f:
        f.write(pcap_hdr)
        ts_sec = 1700000000
        for idx, payload in enumerate(packets_payloads):
            eth_ip_udp = b"\x00" * 42
            full_frame = eth_ip_udp + payload
            pkt_hdr = struct.pack("<IIII", ts_sec + idx, idx * 1000, len(full_frame), len(full_frame))
            f.write(pkt_hdr)
            f.write(full_frame)


def read_pcap_payloads(filepath: str) -> list[bytes]:
    payloads: list[bytes] = []
    with open(filepath, "rb") as f:
        header = f.read(24)
        if len(header) < 24:
            return payloads
        while True:
            pkt_hdr = f.read(16)
            if len(pkt_hdr) < 16:
                break
            _, _, caplen, _ = struct.unpack("<IIII", pkt_hdr)
            frame = f.read(caplen)
            if len(frame) > 42:
                payloads.append(frame[42:])
    return payloads
