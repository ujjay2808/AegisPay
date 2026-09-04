package com.aegispay.gateway.service;

import java.math.BigInteger;
import java.util.List;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.web3j.abi.FunctionEncoder;
import org.web3j.abi.datatypes.Function;
import org.web3j.abi.datatypes.generated.Bytes32;
import org.web3j.abi.datatypes.generated.Uint8;
import org.web3j.crypto.Credentials;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.core.methods.response.EthSendTransaction;
import org.web3j.tx.RawTransactionManager;
import org.web3j.utils.Numeric;

import com.aegispay.gateway.exception.AegisPayBlockchainException;

@Service
public class AuditLogService {
    private final Web3j web3j;
    private final Credentials credentials;
    private final String contractAddress;

    public AuditLogService(Web3j web3j, Credentials credentials,
            @Value("${aegispay.contract.address}") String contractAddress) {
        this.web3j = web3j;
        this.credentials = credentials;
        this.contractAddress = contractAddress;
    }

    public String logDecision(String decisionHashHex, int decisionEnumValue) {
        try {
            if (!decisionHashHex.startsWith("0x") || Numeric.hexStringToByteArray(decisionHashHex).length != 32
                    || decisionEnumValue < 0 || decisionEnumValue > 2)
                throw new IllegalArgumentException("Invalid decision payload");
            String data = FunctionEncoder.encode(
                    new Function("logDecision", List.of(new Bytes32(Numeric.hexStringToByteArray(decisionHashHex)),
                            new Uint8(BigInteger.valueOf(decisionEnumValue))), List.of()));
                            EthSendTransaction tx = new RawTransactionManager(web3j, credentials, 80002L).sendTransaction(
                                BigInteger.valueOf(30_000_000_000L), BigInteger.valueOf(300000), contractAddress, data, BigInteger.ZERO, false);
            if (tx.hasError())
                throw new IllegalStateException(tx.getError().getMessage());
            return tx.getTransactionHash();
        } catch (Exception exception) {
            System.err.println("BLOCKCHAIN CALL FAILED: " + exception);
            exception.printStackTrace();
            throw new AegisPayBlockchainException("Failed to log decision on-chain", exception);
        }
    }
}
