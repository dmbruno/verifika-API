// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract HashRegistry {
    event HashRegistered(bytes32 indexed hash, address sender, uint256 timestamp);

    mapping(bytes32 => uint256) public registeredAt;
    mapping(bytes32 => uint256) public imageRegisteredAt;

    function registerHash(bytes32 imageHash, bytes32 recordHash) external {
        require(imageRegisteredAt[imageHash] == 0, "Imagen ya registrada");
        require(registeredAt[recordHash] == 0, "Hash ya registrado");
        imageRegisteredAt[imageHash] = block.timestamp;
        registeredAt[recordHash] = block.timestamp;
        emit HashRegistered(recordHash, msg.sender, block.timestamp);
    }
}
