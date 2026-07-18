"""
Script de deploy de SimpleMultisig.sol + HashRegistry.sol en Polygon Amoy.

Deploya primero el multisig (con la wallet operativa del .env como owner
"caliente" y una segunda wallet de respaldo como owner de recuperacion),
y despues HashRegistry con el multisig como dueno.

Uso: python contracts/deploy.py
"""
import json
import os

import solcx
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

CONTRACTS_DIR = os.path.dirname(__file__)
MULTISIG_PATH = os.path.join(CONTRACTS_DIR, "SimpleMultisig.sol")
REGISTRY_PATH = os.path.join(CONTRACTS_DIR, "HashRegistry.sol")

# Direccion publica de la clave de respaldo (owner #2 del multisig).
# La private key correspondiente NO vive en este repo ni en el servidor —
# se guarda offline, fuera de la infraestructura que opera la API.
BACKUP_OWNER_ADDRESS = "0x3F1777e725F414A97898298A99C6bFa0E3388412"


def compile_contract(path, contract_name):
    solcx.install_solc("0.8.20")
    with open(path) as f:
        source = f.read()
    compiled = solcx.compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version="0.8.20",
    )
    for key, interface in compiled.items():
        if key.endswith(":" + contract_name):
            return interface["abi"], interface["bin"]
    raise RuntimeError(f"No se encontro el contrato {contract_name} en {path}")


def deploy(w3, account, abi, bytecode, constructor_args):
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    tx = contract.constructor(*constructor_args).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "gasPrice": gas_price,
        }
    )
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return receipt.contractAddress, tx_hash.hex(), receipt.blockNumber, receipt.gasUsed


def main():
    load_dotenv(override=True)
    rpc_url = os.getenv("POLYGON_RPC_URL")
    pk = os.getenv("PRIVATE_KEY")
    if not pk.startswith("0x"):
        pk = "0x" + pk

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    assert w3.is_connected(), "No se pudo conectar al RPC"

    account = Account.from_key(pk)
    print(f"Deploying desde (owner caliente del multisig): {account.address}")
    print(f"Owner de respaldo del multisig: {BACKUP_OWNER_ADDRESS}")
    print(f"Chain ID: {w3.eth.chain_id}")

    # 1. Deploy SimpleMultisig
    print("\n--- Deployando SimpleMultisig ---")
    multisig_abi, multisig_bin = compile_contract(MULTISIG_PATH, "SimpleMultisig")
    owners = [account.address, BACKUP_OWNER_ADDRESS]
    required = 1
    multisig_address, tx1, block1, gas1 = deploy(
        w3, account, multisig_abi, multisig_bin, [owners, required]
    )
    print(f"SimpleMultisig deployado en: {multisig_address}")
    print(f"Tx: {tx1} | Bloque: {block1} | Gas: {gas1}")

    with open(os.path.join(CONTRACTS_DIR, "SimpleMultisig.abi.json"), "w") as f:
        json.dump(multisig_abi, f, indent=2)

    # 2. Deploy HashRegistry, con el multisig como owner
    print("\n--- Deployando HashRegistry ---")
    registry_abi, registry_bin = compile_contract(REGISTRY_PATH, "HashRegistry")
    registry_address, tx2, block2, gas2 = deploy(
        w3, account, registry_abi, registry_bin, [multisig_address]
    )
    print(f"HashRegistry deployado en: {registry_address}")
    print(f"Tx: {tx2} | Bloque: {block2} | Gas: {gas2}")

    with open(os.path.join(CONTRACTS_DIR, "HashRegistry.abi.json"), "w") as f:
        json.dump(registry_abi, f, indent=2)

    print("\n--- RESULTADO ---")
    print(f"MULTISIG_ADDRESS={multisig_address}")
    print(f"CONTRACT_ADDRESS={registry_address}")
    print(f"MULTISIG_TX_HASH={tx1}")
    print(f"REGISTRY_TX_HASH={tx2}")


if __name__ == "__main__":
    main()
