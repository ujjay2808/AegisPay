package com.aegispay.gateway.service;

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
import org.web3j.protocol.core.methods.response.EthGetTransactionReceipt;
import org.web3j.protocol.core.methods.response.EthSendRawTransaction;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.web3j.abi.FunctionEncoder;
import org.web3j.abi.datatypes.Function;
import org.web3j.abi.datatypes.generated.Bytes32;
import org.web3j.abi.datatypes.generated.Uint8;
import org.web3j.crypto.Credentials;
import org.web3j.crypto.RawTransaction;
import org.web3j.crypto.TransactionEncoder;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.core.methods.response.EthGetTransactionCount;
import org.web3j.protocol.core.methods.response.EthSendTransaction;
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

    public synchronized String logDecision(String decisionHashHex, int decisionEnumValue) {
        try {
            if (!decisionHashHex.startsWith("0x") || Numeric.hexStringToByteArray(decisionHashHex).length != 32
                    || decisionEnumValue < 0 || decisionEnumValue > 2)
                throw new IllegalArgumentException("Invalid decision payload");
            String data = FunctionEncoder.encode(
                    new Function("logDecision", List.of(new Bytes32(Numeric.hexStringToByteArray(decisionHashHex)),
                            new Uint8(BigInteger.valueOf(decisionEnumValue))), List.of()));

            BigInteger gasPrice = web3j.ethGasPrice().send().getGasPrice();
            gasPrice = gasPrice.multiply(BigInteger.valueOf(125)).divide(BigInteger.valueOf(100));

            EthGetTransactionCount nonceResponse = web3j.ethGetTransactionCount(
                    credentials.getAddress(), DefaultBlockParameterName.LATEST).send();
            BigInteger nonce = nonceResponse.getTransactionCount();
            // This is intentional: calls are serialized and we wait for the receipt, and it lets a new
            // tx replace a stuck pending tx at the same nonce.

            BigInteger gasLimit = BigInteger.valueOf(300000);
            RawTransaction raw = RawTransaction.createTransaction(nonce, gasPrice, gasLimit, contractAddress,
                    BigInteger.ZERO, data);

            byte[] signed = TransactionEncoder.signMessage(raw, 80002L, credentials);
            String hex = Numeric.toHexString(signed);
            EthSendTransaction sendResult = web3j.ethSendRawTransaction(hex).send();
            if (sendResult.hasError()) {
                throw new IllegalStateException(sendResult.getError().getMessage());
            }

            String txHash = sendResult.getTransactionHash();
            long deadlineMillis = System.currentTimeMillis() + 20000L;
            while (System.currentTimeMillis() < deadlineMillis) {
                EthGetTransactionReceipt receipt = web3j.ethGetTransactionReceipt(txHash).send();
                if (receipt != null && receipt.getTransactionReceipt().isPresent()) {
                    String status = receipt.getTransactionReceipt().get().getStatus();
                    if ("0x1".equals(status)) {
                        return txHash;
                    }
                    throw new AegisPayBlockchainException("Audit transaction reverted: " + txHash,
                            new IllegalStateException("Audit transaction reverted: " + txHash));
                }
                Thread.sleep(1000L);
            }
            throw new AegisPayBlockchainException("Audit transaction not mined within 20s: " + txHash,
                    new IllegalStateException("Audit transaction not mined within 20s: " + txHash));
        } catch (AegisPayBlockchainException exception) {
            throw exception;
        } catch (Exception exception) {
            System.err.println("BLOCKCHAIN CALL FAILED: " + exception);
            exception.printStackTrace();
            throw new AegisPayBlockchainException("Failed to log decision on-chain", exception);
        }
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
