// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract HashRegistry {
    event HashRegistered(bytes32 indexed hash, address sender, uint256 timestamp);
    event OwnerChanged(address indexed previousOwner, address indexed newOwner);

    address public owner;
    mapping(bytes32 => uint256) public registeredAt;
    mapping(bytes32 => uint256) public imageRegisteredAt;

    modifier onlyOwner() {
        require(msg.sender == owner, "no autorizado");
        _;
    }

    constructor(address _owner) {
        require(_owner != address(0), "owner invalido");
        owner = _owner;
    }

    function registerHash(bytes32 imageHash, bytes32 recordHash) external onlyOwner {
        require(imageRegisteredAt[imageHash] == 0, "Imagen ya registrada");
        require(registeredAt[recordHash] == 0, "Hash ya registrado");
        imageRegisteredAt[imageHash] = block.timestamp;
        registeredAt[recordHash] = block.timestamp;
        emit HashRegistered(recordHash, msg.sender, block.timestamp);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "owner invalido");
        emit OwnerChanged(owner, newOwner);
        owner = newOwner;
    }
}
