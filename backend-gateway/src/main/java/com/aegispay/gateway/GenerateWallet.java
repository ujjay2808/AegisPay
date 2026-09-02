package com.aegispay.gateway;

import org.web3j.crypto.WalletUtils;

public class GenerateWallet {
    public static void main(String[] args) throws Exception {
        String password = "AegisPayDev2026"; // plain letters+digits only, no $ or special chars
        String fileName = WalletUtils.generateNewWalletFile(password, new java.io.File("./"));
        System.out.println("Wallet file created: " + fileName);
    }
}