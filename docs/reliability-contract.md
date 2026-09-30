# Reliability contract

This work implements the node-operations promises in architecture-v0.1.md.

1. Observations are measured facts. A failed or empty real observation never
   produces mock network data. Paths are snapshots, not received announces or
   discovered peers. Collection failure and freshness must be visible.
2. Interface commands report verified execution, failure, or unsupported
   capability. Changing a control-plane field is not execution success.
3. Persisted desired state distinguishes an intentional stop from a crash.
   Recovery reconciles actual state against desired state.
4. Saved configuration is distinct from active configuration. Saving cannot
   partially mutate the active service graph. Applying requires validation,
   consistent activation, and recovery on failure.
5. Runtime mutation has one cross-process authority. Restarting the management
   server alone does not stop forwarding. CLI and background recovery must not
   race runtime operations.
6. Backups use a consistent database snapshot. Restore validates all inputs
   before changes, preserves local deployment paths, and rolls back partial
   failure within an exclusive maintenance boundary.
7. Dependency upgrades must be resolved and tested; package metadata alone is
   not proof of compatibility.

Regression tests must exercise these public behavior boundaries, including
failures, empty observations, competing callers, and recovery after restart.
