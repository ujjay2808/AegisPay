package com.aegispay.gateway.controller;

import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.aegispay.gateway.exception.AegisPayBlockchainException;
import com.aegispay.gateway.service.AuditLogService;

@RestController
@RequestMapping("/api/decisions")
public class AuditLogController {
    private final AuditLogService auditLogService;
    public AuditLogController(AuditLogService auditLogService) { this.auditLogService = auditLogService; }
    @PostMapping
    public ResponseEntity<?> log(@RequestBody DecisionRequest body) {
        try { return ResponseEntity.ok(Map.of("txHash", auditLogService.logDecision(body.decisionHash(), switch (body.decision().toUpperCase()) { case "APPROVED" -> 0; case "DENIED" -> 1; case "ESCALATED" -> 2; default -> throw new IllegalArgumentException("Invalid decision"); }))); }
        catch (AegisPayBlockchainException exception) { return ResponseEntity.internalServerError().body(Map.of("error", exception.getMessage())); }
        catch (Exception exception) { return ResponseEntity.internalServerError().body(Map.of("error", exception.getMessage())); }
    }
    record DecisionRequest(String decisionHash, String decision) {}
}
