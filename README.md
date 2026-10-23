# PerfectDan RC1.1-C independent research

Only public research inputs, source/checkpoint manifests and audit helpers are included. No production game, checkpoint weights, credentials or formal holdout.

Read AGENTS.md, OWNER_CONTRACT.md, phases/rc11c.yaml and CLOUD_TASK_PROMPT.md. Restore original inputs with `python tools/materialize_public_inputs.py`; this does not load a model. Fetch upstream only at the fixed commit and verify source identities. Historical scripts under inputs/rc11 are immutable audit inputs, not a portable runner.

Owner approved strict R0 unknown54 for every variant. New helper: tools/observation_patch_strict.py. Local NumPy/source-AST reference validation passed 26 original public cases x4 variants, with no Torch import; this does not establish neural logits or actions. evidence/local_preflight is historical local evidence, never Cloud runtime results. Write new actual evidence in evidence/cloud.

Safety/runtime/network gates must pass before safe R0 load. A task name, SHA, failed DNS or Python monkeypatch is insufficient proof. Stop honestly when blocked. No training, tuning, V1 benchmark, Native bridge or production adoption. No claim of rerunning production tests.

Preparation and experiment have separate finite budgets. Preserve the Owner-approved preparation extension deadline. Experiment is one worker, initially two numeric threads, at most1800 active seconds total and at most16 upstream Matches. No budget reset or unattended continuation.
