from __future__ import annotations

import json
from pathlib import Path


def validate_registers(
    register_map: dict[str, object],
) -> tuple[int, list[dict[str, object]]]:
    frame_bytes = int(register_map.get("frame_bytes", 0))
    frame_bits = int(register_map.get("frame_bits", 0))
    if frame_bytes <= 0 or frame_bits != frame_bytes * 8:
        raise ValueError("frame_dimensions_invalid")
    registers = register_map.get("registers")
    if not isinstance(registers, list) or not registers:
        raise ValueError("registers_missing")
    occupied: set[int] = set()
    normalized: list[dict[str, object]] = []
    for register in registers:
        if not isinstance(register, dict):
            raise ValueError("register_invalid")
        name = str(register.get("name", ""))
        offset = int(register.get("offset", -1))
        width = int(register.get("bytes", 0))
        if not name or offset < 0 or width <= 0 or offset + width > frame_bytes:
            raise ValueError(f"register_bounds_invalid:{name}")
        positions = set(range(offset, offset + width))
        if occupied & positions:
            raise ValueError(f"register_overlap:{name}")
        occupied.update(positions)
        normalized.append(
            {
                "name": name,
                "offset": offset,
                "bytes": width,
                "access": str(register.get("access", "")),
                "fields": register.get("fields", []),
            }
        )
    return frame_bytes, normalized


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    register_map = json.loads(
        (root / "interfaces/register_maps/risk_gate.json").read_text(encoding="utf-8")
    )
    frame_bytes, registers = validate_registers(register_map)
    version = int(register_map["register_map_version"])
    frame_bits = frame_bytes * 8
    rust_lines = [
        f"pub const REGISTER_MAP_VERSION: u64 = {version};",
        f"pub const FRAME_BYTES: usize = {frame_bytes};",
        f"pub const FRAME_BITS: usize = {frame_bits};",
    ]
    sv_lines = [
        "package ito_risk_frame_pkg;",
        f"localparam integer REGISTER_MAP_VERSION = {version};",
        f"localparam integer FRAME_BYTES = {frame_bytes};",
        f"localparam integer FRAME_BITS = {frame_bits};",
    ]
    for register in registers:
        constant = str(register["name"]).upper()
        offset = int(register["offset"])
        rust_lines.append(f"pub const OFFSET_{constant}: usize = {offset};")
        sv_lines.append(f"localparam integer OFFSET_{constant} = {offset};")
    sv_lines.append("endpackage")
    generated_json = {
        "register_map_version": version,
        "frame_bytes": frame_bytes,
        "frame_bits": frame_bits,
        "registers": registers,
    }
    (root / "rust/risk_service/src/generated.rs").write_text(
        "\n".join(rust_lines) + "\n", encoding="utf-8"
    )
    (root / "rtl/common/generated/risk_frame_pkg.sv").write_text(
        "\n".join(sv_lines) + "\n", encoding="utf-8"
    )
    (root / "interfaces/generated/risk_frame_layout.json").write_text(
        json.dumps(generated_json, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("risk_interface_generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
