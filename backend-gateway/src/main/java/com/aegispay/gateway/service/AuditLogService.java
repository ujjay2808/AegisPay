package com.aegispay.gateway.service;

import java.io.IOException;
import java.math.BigInteger;
import java.util.List;
import java.util.Optional;
import org.web3j.abi.FunctionReturnDecoder;
import org.web3j.abi.TypeReference;
import org.web3j.abi.datatypes.Address;
import org.web3j.abi.datatypes.Type;
import org.web3j.abi.datatypes.generated.Uint256;
import org.web3j.protocol.core.DefaultBlockParameterName;
import org.web3j.protocol.core.methods.request.Transaction;
import org.web3j.protocol.core.methods.response.EthCall;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.web3j.abi.FunctionEncoder;
import org.web3j.abi.datatypes.Function;
import org.web3j.abi.datatypes.generated.Bytes32;
import org.web3j.abi.datatypes.generated.Uint8;
import org.web3j.crypto.Credentials;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.core.methods.response.EthGetTransactionReceipt;
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

            BigInteger gasPrice = web3j.ethGasPrice().send().getGasPrice();
            if (gasPrice == null || gasPrice.signum() <= 0) {
                gasPrice = BigInteger.valueOf(30_000_000_000L);
            }

            EthSendTransaction tx = new RawTransactionManager(web3j, credentials, 80002L).sendTransaction(
                    gasPrice, BigInteger.valueOf(300000), contractAddress, data, BigInteger.ZERO, false);
            if (tx.hasError()) {
                throw new IllegalStateException(tx.getError().getMessage());
            }

            String txHash = tx.getTransactionHash();
            waitForReceipt(txHash);
            return txHash;
        } catch (Exception exception) {
            System.err.println("BLOCKCHAIN CALL FAILED: " + exception);
            exception.printStackTrace();
            throw new AegisPayBlockchainException("Failed to log decision on-chain", exception);
        }
    }

    private void waitForReceipt(String txHash) throws InterruptedException, IOException {
        for (int attempt = 0; attempt < 40; attempt++) {
            EthGetTransactionReceipt receipt = web3j.ethGetTransactionReceipt(txHash).send();
            if (receipt != null && receipt.getTransactionReceipt().isPresent()) {
                if (!receipt.getTransactionReceipt().get().isStatusOK()) {
                    throw new IllegalStateException("On-chain transaction reverted");
                }
                return;
            }
            Thread.sleep(1000L);
        }
        throw new IllegalStateException("Timed out waiting for transaction receipt");
    }

    public record AuditRecordView(String decisionHash, String decision, long timestamp, String submittedBy) {}

    public Optional<AuditRecordView> getRecordByHash(String decisionHashHex) {
        if (decisionHashHex == null || !decisionHashHex.startsWith("0x")
                || Numeric.hexStringToByteArray(decisionHashHex).length != 32)
            throw new IllegalArgumentException("Invalid decision hash");
        try {
            Function function = new Function("getRecordByHash",
                    List.of(new Bytes32(Numeric.hexStringToByteArray(decisionHashHex))),
                    List.of(new TypeReference<Bytes32>() {}, new TypeReference<Uint8>() {},
                            new TypeReference<Uint256>() {}, new TypeReference<Address>() {}));
            EthCall call = web3j.ethCall(
                    Transaction.createEthCallTransaction(credentials.getAddress(), contractAddress,
                            FunctionEncoder.encode(function)),
                    DefaultBlockParameterName.LATEST).send();
            if (call.hasError()) {
                String message = String.valueOf(call.getError().getMessage());
                if (message.toLowerCase().contains("revert")) return Optional.empty();
                throw new IllegalStateException(message);
            }
            String value = call.getValue();
            if (value == null || value.equals("0x")) return Optional.empty();
            @SuppressWarnings("rawtypes")
            List<Type> out = FunctionReturnDecoder.decode(value, function.getOutputParameters());
            if (out.size() != 4) return Optional.empty();
            String[] names = {"APPROVED", "DENIED", "ESCALATED"};
            int decisionIndex = ((Uint8) out.get(1)).getValue().intValue();
            return Optional.of(new AuditRecordView(
                    Numeric.toHexString((byte[]) out.get(0).getValue()),
                    decisionIndex < names.length ? names[decisionIndex] : "UNKNOWN",
                    ((Uint256) out.get(2)).getValue().longValue(),
                    ((Address) out.get(3)).getValue()));
        } catch (Exception exception) {
            throw new AegisPayBlockchainException("Failed to read decision from chain", exception);
        }
    }
}
