"""
Script de deploy puntual de HashRegistry.sol en Polygon Amoy.
Uso: python contracts/deploy.py
"""
import json
import os

import solcx
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

CONTRACT_PATH = os.path.join(os.path.dirname(__file__), "HashRegistry.sol")
ABI_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "HashRegistry.abi.json")


def compile_contract():
    solcx.install_solc("0.8.20")
    with open(CONTRACT_PATH) as f:
        source = f.read()

    compiled = solcx.compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version="0.8.20",
    )
    contract_id, contract_interface = list(compiled.items())[0]
    return contract_interface["abi"], contract_interface["bin"]


def main():
    load_dotenv(override=True)
    rpc_url = os.getenv("POLYGON_RPC_URL")
    pk = os.getenv("PRIVATE_KEY")
    if not pk.startswith("0x"):
        pk = "0x" + pk

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    assert w3.is_connected(), "No se pudo conectar al RPC"

    account = Account.from_key(pk)
    print(f"Deploying desde: {account.address}")
    print(f"Chain ID: {w3.eth.chain_id}")

    abi, bytecode = compile_contract()

    HashRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    tx = HashRegistry.constructor().build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "gasPrice": gas_price,
        }
    )

    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Tx enviada: {tx_hash.hex()}")
    print("Esperando confirmacion...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    contract_address = receipt.contractAddress
    print(f"Contrato deployado en: {contract_address}")
    print(f"Bloque: {receipt.blockNumber}, gas usado: {receipt.gasUsed}")

    with open(ABI_OUTPUT_PATH, "w") as f:
        json.dump(abi, f, indent=2)
    print(f"ABI guardado en: {ABI_OUTPUT_PATH}")

    print("\n--- RESULTADO ---")
    print(f"CONTRACT_ADDRESS={contract_address}")
    print(f"TX_HASH={tx_hash.hex()}")


if __name__ == "__main__":
    main()
