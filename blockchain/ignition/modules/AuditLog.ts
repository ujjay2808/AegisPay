import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("AuditLogModule", (m) => {
  const auditLog = m.contract("AuditLog");
  return { auditLog };
});