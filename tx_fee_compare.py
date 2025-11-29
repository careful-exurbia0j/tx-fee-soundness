# tx_fee_compare.py
"""
Compatibility shim for older users.
Delegates to the new txfee package CLI.

Usage (old style):
    python tx_fee_compare.py --rpc ... 0xTXHASH
"""

from txfee.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
