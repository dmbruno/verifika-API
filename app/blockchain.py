import json
import os
from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.middleware import ExtraDataToPOAMiddleware

w3 = Web3(Web3.HTTPProvider(os.environ["POLYGON_RPC_URL"]))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

CONTRACTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contracts"
)

with open(os.path.join(CONTRACTS_DIR, "HashRegistry.abi.json")) as f:
    CONTRACT_ABI = json.load(f)
with open(os.path.join(CONTRACTS_DIR, "SimpleMultisig.abi.json")) as f:
    MULTISIG_ABI = json.load(f)

contract = w3.eth.contract(address=os.environ["CONTRACT_ADDRESS"], abi=CONTRACT_ABI)
multisig = w3.eth.contract(address=os.environ["MULTISIG_ADDRESS"], abi=MULTISIG_ABI)


class HashAlreadyRegisteredError(Exception):
    """El contrato revirtio el require() porque el hash ya estaba anclado."""


class ImageAlreadyRegisteredError(HashAlreadyRegisteredError):
    """La imagen (image_hash) ya fue registrada antes, sin importar el record."""


class RecordAlreadyRegisteredError(HashAlreadyRegisteredError):
    """Este record_hash exacto (imagen+timestamp+ubicacion) ya fue anclado antes."""


def check_image_registered(image_hash_hex: str) -> int:
    hash_bytes = bytes.fromhex(image_hash_hex)
    return contract.functions.imageRegisteredAt(hash_bytes).call()


def check_registered(record_hash_hex: str) -> int:
    hash_bytes = bytes.fromhex(record_hash_hex)
    return contract.functions.registeredAt(hash_bytes).call()


def anchor_hash(image_hash_hex: str, record_hash_hex: str) -> str:
    image_hash_bytes = bytes.fromhex(image_hash_hex)
    record_hash_bytes = bytes.fromhex(record_hash_hex)

    # Chequeo on-chain preventivo: evita gastar gas en una tx condenada a revertir.
    if check_image_registered(image_hash_hex) > 0:
        raise ImageAlreadyRegisteredError("Esta imagen ya fue registrada anteriormente")
    if check_registered(record_hash_hex) > 0:
        raise RecordAlreadyRegisteredError("Este registro exacto ya fue anclado anteriormente")

    # registerHash ya no se llama directo: HashRegistry solo acepta llamadas
    # de su owner (el multisig), asi que se propone como una transaccion del
    # multisig. Con required=1, la propia propuesta la auto-confirma y
    # ejecuta en el mismo paso — sin latencia extra para quien usa la API.
    calldata = contract.encode_abi("registerHash", args=[image_hash_bytes, record_hash_bytes])

    submit_fn = multisig.functions.submitTransaction(os.environ["CONTRACT_ADDRESS"], calldata)
    tx_params = {
        "from": os.environ["SERVER_ADDRESS"],
        "nonce": w3.eth.get_transaction_count(os.environ["SERVER_ADDRESS"]),
    }

    # Guardar `bytes` arbitrarios en storage dentro del multisig sale mucho
    # mas caro que llamar registerHash directo, asi que estimamos el gas en
    # vez de hardcodear un limite (ademas, si esto revierte, lo hace aca con
    # el motivo real en vez de fallar por gas insuficiente mas adelante).
    try:
        gas_estimate = submit_fn.estimate_gas(tx_params)
    except ContractLogicError as exc:
        raise HashAlreadyRegisteredError(str(exc)) from exc
    except ValueError as exc:
        if "revert" in str(exc).lower():
            raise HashAlreadyRegisteredError(str(exc)) from exc
        raise

    tx = submit_fn.build_transaction({**tx_params, "gas": int(gas_estimate * 1.3)})
    signed_tx = w3.eth.account.sign_transaction(tx, os.environ["PRIVATE_KEY"])
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 0:
        raise HashAlreadyRegisteredError(
            f"La transaccion {receipt.transactionHash.hex()} revirtio de forma "
            "inesperada (posible condicion de carrera con otra verificacion "
            "concurrente)."
        )
    return receipt.transactionHash.hex()
