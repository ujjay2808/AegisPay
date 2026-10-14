package com.aegispay.gateway.controller;

import java.util.Map;
import java.util.Optional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

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

    @GetMapping("/{hash}")
    public ResponseEntity<?> get(@PathVariable String hash) {
        try {
            Optional<AuditLogService.AuditRecordView> record = auditLogService.getRecordByHash(hash);
            if (record.isPresent()) return ResponseEntity.ok(record.get());
            return ResponseEntity.status(404).body(Map.of("error", "Record not found"));
        } catch (IllegalArgumentException exception) {
            return ResponseEntity.badRequest().body(Map.of("error", String.valueOf(exception.getMessage())));
        } catch (Exception exception) {
            return ResponseEntity.internalServerError().body(Map.of("error", String.valueOf(exception.getMessage())));
        }
    }
}
