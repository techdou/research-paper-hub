# Upstream synchronization policy

The hub tracks CCFA-Skills and nature-skills independently. It does not hard-merge their repositories.

## Why project-local vendor copies

Synchronized upstream skill folders are copied into `.research/vendor/` and treated as playbooks. They are not deployed as top-level discoverable skills by default. This avoids host-level implicit invocation collisions while preserving the detailed upstream workflow.

## Safety rules

- check automatically or opportunistically; apply only on explicit user request;
- update by skill, source, or recommended set;
- keep the previous project-local copy before replacement;
- store source repo, branch, commit, git tree SHA, local content SHA-256, and timestamp;
- never edit upstream playbooks in place; user customizations go in `.research/overrides/`;
- copy upstream repository license notices into the vendor source folder;
- support rollback to the previous local copy;
- record the capability version used by every run.

## Shared dependencies

The registry may declare source-level support dependencies. In particular, CCFA skills may rely on `ccf-common`, and Nature skills may rely on `nature-shared`. Synchronization must include these when required rather than copying only the visible skill directory.
