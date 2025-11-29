# txfee/__main__.py

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Optional

from .core import TxFeeConfig, inspect_transaction


def _format_timestamp(ts: Optional[int]) -> str:
    if ts is None:
        return "n/a"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _emoji_ok(ok: bool, no_emoji: bool) -> str:
    if no_emoji:
        return "OK" if ok else "FAIL"
    return "✅" if ok else "❌"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="txfee",
        description="Inspect an Ethereum transaction's fee and soundness across RPCs.",
    )
    parser.add_argument("tx_hash", help="Transaction hash (0x...)")
    parser.add_argument("--rpc", required=True, help="HTTP RPC endpoint URL")
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="RPC request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--min-confirmations",
        type=int,
        default=0,
        help="Require at least N confirmations (0 = no requirement)",
    )
    parser.add_argument(
        "--short",
        action="store_true",
        help="Print a single-line summary instead of verbose output",
    )
    parser.add_argument(
        "--no-emoji",
        action="store_true",
        help="Disable emoji in the output",
    )

    args = parser.parse_args(argv)

    cfg = TxFeeConfig(
        rpc_url=args.rpc,
        tx_hash=args.tx_hash,
        timeout=args.timeout,
        min_confirmations=args.min_confirmations,
    )

    try:
        result = inspect_transaction(cfg)
    except Exception as e:
        print(f"[txfee] Error: {e}", file=sys.stderr)
        return 1

    status_str = "pending" if result.pending else ("success" if result.status else "reverted")
    status_ok = (result.status is True) and (not result.pending)
    ok_emoji = _emoji_ok(status_ok, args.no_emoji)

    if args.short:
        print(
            f"{ok_emoji} chain={result.chain_id} "
            f"tx={result.tx_hash} "
            f"status={status_str} "
            f"fee={result.total_fee_eth:.6f} ETH "
            f"conf={result.confirmations}"
        )
    else:
        print(f"Connected to chainId {result.chain_id}")
        print(f"Tx Hash: {result.tx_hash}")
        print(f"From: {result.from_address}")
        print(f"To: {result.to_address or '<contract creation>'}")
        print(f"Status: {ok_emoji} {status_str}")
        print(f"Block: {result.block_number or 'pending'}")
        print(f"Block Time: {_format_timestamp(result.block_timestamp)}")
        print(f"Gas Used: {result.gas_used}")
        print(f"Gas Price: {result.gas_price_gwei:.2f} Gwei")
        print(f"Total Fee: {result.total_fee_eth:.6f} ETH")
        print(f"Confirmations: {result.confirmations}")

        if args.min_confirmations and result.confirmations < args.min_confirmations:
            warn = "WARN" if args.no_emoji else "⚠️"
            print(
                f"{warn} Only {result.confirmations} confirmations; "
                f"required: {args.min_confirmations}"
            )

    # Exit code: 0 = script ran; 1 = error in RPC or logic
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
