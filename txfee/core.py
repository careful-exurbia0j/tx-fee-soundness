# txfee/core.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from web3 import Web3
from web3.types import TxData, TxReceipt


@dataclass
class TxFeeConfig:
    rpc_url: str
    tx_hash: str
    timeout: int = 10
    min_confirmations: int = 0


@dataclass
class TxFeeResult:
    chain_id: int
    tx_hash: str
    from_address: str
    to_address: Optional[str]
    block_number: Optional[int]
    block_timestamp: Optional[int]
    status: Optional[bool]
    gas_used: int
    gas_price_gwei: float
    total_fee_eth: float
    confirmations: int
    pending: bool


def _get_web3(rpc_url: str, timeout: int) -> Web3:
    provider = Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": timeout})
    w3 = Web3(provider)
    if not w3.is_connected():
        raise RuntimeError(f"Could not connect to RPC at {rpc_url}")
    return w3


def _get_tx_and_receipt(w3: Web3, tx_hash: str) -> tuple[TxData, Optional[TxReceipt]]:
    tx = w3.eth.get_transaction(tx_hash)
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception:
        # pending transactions can legitimately not have a receipt yet
        receipt = None
    return tx, receipt


def _get_effective_gas_price(w3: Web3, tx: TxData, receipt: Optional[TxReceipt]) -> int:
    """
    Try to compute the effective gas price in wei.

    Prefer EIP-1559 effectiveGasPrice if available, otherwise
    fall back to legacy gasPrice from the transaction.
    """
    if receipt is not None and hasattr(receipt, "effectiveGasPrice"):
        return int(receipt.effectiveGasPrice)
    # legacy tx gas price
    return int(tx.get("gasPrice", 0))


def inspect_transaction(config: TxFeeConfig) -> TxFeeResult:
    """
    Core entry point: given a TxFeeConfig, return a TxFeeResult
    without printing to stdout. This can be used by CLIs, UIs, or tests.
    """
    w3 = _get_web3(config.rpc_url, config.timeout)

    tx, receipt = _get_tx_and_receipt(w3, config.tx_hash)

    chain_id = int(w3.eth.chain_id)

    from_address = tx["from"]
    to_address = tx["to"]

    block_number = receipt["blockNumber"] if receipt is not None else None
    block_timestamp: Optional[int]
    confirmations: int

    if block_number is not None:
        block = w3.eth.get_block(block_number)
        block_timestamp = int(block["timestamp"])
        latest_block = int(w3.eth.block_number)
        confirmations = max(0, latest_block - int(block_number))
    else:
        block_timestamp = None
        confirmations = 0

    # Determine status and gas used
    if receipt is not None:
        status = bool(receipt["status"])
        gas_used = int(receipt["gasUsed"])
        pending = False
    else:
        status = None
        gas_used = 0
        pending = True

    gas_price_wei = _get_effective_gas_price(w3, tx, receipt)
    gas_price_gwei = gas_price_wei / 1e9 if gas_price_wei else 0.0
    total_fee_eth = (gas_price_wei * gas_used) / 1e18 if gas_price_wei and gas_used else 0.0

    # Optionally enforce minimum confirmations
    if config.min_confirmations and confirmations < config.min_confirmations:
        # We still return the data, but this can be inspected by callers
        pass

    return TxFeeResult(
        chain_id=chain_id,
        tx_hash=config.tx_hash,
        from_address=from_address,
        to_address=to_address,
        block_number=int(block_number) if block_number is not None else None,
        block_timestamp=block_timestamp,
        status=status,
        gas_used=gas_used,
        gas_price_gwei=gas_price_gwei,
        total_fee_eth=total_fee_eth,
        confirmations=confirmations,
        pending=pending,
    )
