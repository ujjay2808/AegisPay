package com.aegispay.gateway.config;

import java.io.IOException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import org.web3j.crypto.exception.CipherException;
import org.web3j.crypto.Credentials;
import org.web3j.crypto.WalletUtils;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.http.HttpService;

@Configuration
public class Web3jConfig {

    private static final Logger log = LoggerFactory.getLogger(Web3jConfig.class);

    @Value("${aegispay.keystore.path}")
    private String keystorePath;

    @Value("${aegispay.keystore.password}")
    private String keystorePassword;

    @Value("${aegispay.amoy.rpc-url}")
    private String rpcUrl;

    @Value("${aegispay.contract.address}")
    private String contractAddress;

    @Bean
    public Web3j web3j() {
        return Web3j.build(new HttpService(rpcUrl));
    }

    @Bean
    public Credentials credentials() {
        log.info("Keystore path resolved to: {}", keystorePath);
        log.info("Keystore password length resolved to: {}", keystorePassword.length());

        try {
            Credentials credentials = WalletUtils.loadCredentials(keystorePassword, keystorePath);
            log.info("Loaded AegisPay credentials for account {}", credentials.getAddress());
            return credentials;
            
        } catch (IOException exception) {
            throw new RuntimeException(
                "Failed to load AegisPay keystore from '" + keystorePath + "'. Verify the file exists and the path is correct.",
                exception
            );
        } catch (CipherException exception) {
            throw new RuntimeException(
                "Failed to load AegisPay credentials from '" + keystorePath + "'. Verify the password is correct.",
                exception
            );
        }
    }
}