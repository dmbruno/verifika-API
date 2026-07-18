// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Multisig minimo: cualquier owner puede proponer una transaccion,
/// que se ejecuta apenas junta `required` confirmaciones. Con required=1,
/// cada owner puede operar solo (sin latencia extra), y cualquiera de ellos
/// puede reemplazar a otro owner via addOwner/removeOwner si una clave se
/// pierde. No protege contra una clave robada actuando con mala intencion
/// (esa clave sigue pudiendo operar sola) — protege contra perdida de una
/// clave, no contra el compromiso de una clave. Para eso hace falta
/// required > 1, a costa de que cada operacion necesite mas de una firma.
contract SimpleMultisig {
    event OwnerAdded(address indexed owner);
    event OwnerRemoved(address indexed owner);
    event TransactionSubmitted(uint256 indexed txId, address indexed proposer, address to);
    event TransactionConfirmed(uint256 indexed txId, address indexed owner);
    event TransactionExecuted(uint256 indexed txId);

    address[] public owners;
    mapping(address => bool) public isOwner;
    uint256 public required;

    struct Transaction {
        address to;
        bytes data;
        bool executed;
        uint256 confirmations;
    }

    Transaction[] public transactions;
    mapping(uint256 => mapping(address => bool)) public confirmedBy;

    modifier onlyOwner() {
        require(isOwner[msg.sender], "no sos owner");
        _;
    }

    modifier onlySelf() {
        require(msg.sender == address(this), "solo via multisig");
        _;
    }

    constructor(address[] memory _owners, uint256 _required) {
        require(_owners.length > 0, "necesita al menos un owner");
        require(_required > 0 && _required <= _owners.length, "required invalido");
        for (uint256 i = 0; i < _owners.length; i++) {
            address o = _owners[i];
            require(o != address(0), "owner invalido");
            require(!isOwner[o], "owner duplicado");
            isOwner[o] = true;
            owners.push(o);
        }
        required = _required;
    }

    function submitTransaction(address to, bytes calldata data) external onlyOwner returns (uint256 txId) {
        txId = transactions.length;
        transactions.push(Transaction({to: to, data: data, executed: false, confirmations: 0}));
        emit TransactionSubmitted(txId, msg.sender, to);
        confirmTransaction(txId);
    }

    function confirmTransaction(uint256 txId) public onlyOwner {
        require(txId < transactions.length, "tx inexistente");
        require(!confirmedBy[txId][msg.sender], "ya confirmaste");
        require(!transactions[txId].executed, "ya ejecutada");

        confirmedBy[txId][msg.sender] = true;
        transactions[txId].confirmations += 1;
        emit TransactionConfirmed(txId, msg.sender);

        if (transactions[txId].confirmations >= required) {
            _executeTransaction(txId);
        }
    }

    function _executeTransaction(uint256 txId) internal {
        Transaction storage txn = transactions[txId];
        txn.executed = true;
        (bool success, ) = txn.to.call(txn.data);
        require(success, "ejecucion fallida");
        emit TransactionExecuted(txId);
    }

    /// @dev Gestion de owners: solo ejecutable a traves del propio multisig
    /// (o sea, pasando por submitTransaction/confirmTransaction como cualquier
    /// otra operacion, con target = address(this)).
    function addOwner(address newOwner) external onlySelf {
        require(newOwner != address(0), "owner invalido");
        require(!isOwner[newOwner], "ya es owner");
        isOwner[newOwner] = true;
        owners.push(newOwner);
        emit OwnerAdded(newOwner);
    }

    function removeOwner(address ownerToRemove) external onlySelf {
        require(isOwner[ownerToRemove], "no es owner");
        require(owners.length - 1 >= required, "quedarian menos owners que el minimo requerido");
        isOwner[ownerToRemove] = false;
        for (uint256 i = 0; i < owners.length; i++) {
            if (owners[i] == ownerToRemove) {
                owners[i] = owners[owners.length - 1];
                owners.pop();
                break;
            }
        }
        emit OwnerRemoved(ownerToRemove);
    }

    function ownersCount() external view returns (uint256) {
        return owners.length;
    }
}
