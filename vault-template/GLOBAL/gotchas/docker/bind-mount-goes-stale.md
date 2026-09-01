---
title: A bind mount can go stale — container sees an empty folder, host is full
type: gotcha
tags: [docker, wsl2, mounts]
severity: danger
date: 2026-09-01
---

# A bind mount can go stale — container sees an empty folder, host is full

> [!danger] The server reports "healthy" and finds nothing
> After a host-side re-sync the container's bind mount can point at a folder that no longer
> exists. Every read returns "not found" while the host path is visibly full.

<!-- EXAMPLE NOTE — this is what a good gotcha looks like. Delete it once you have your own. -->

## Problem

The service is up and answers health checks. A full re-index inserts zero documents. Reads of
files that demonstrably exist on the host return "not found". Nothing in the logs looks wrong,
which is what makes this expensive: every instinct says to debug the application.

## Cause

On WSL2 with Docker Desktop and a cloud-synced folder, the sync client can replace the directory
inode. The container keeps the old reference — the mount is still *mounted*, just at nothing.
Host and container disagree, and only the container is wrong.

## Fix

```bash
docker exec <container> sh -c 'ls /data | wc -l'   # 0  → mount is orphaned
ls "<HOST_PATH>" | wc -l                           # >0 → host is fine
docker restart <container> && sleep 4
docker exec <container> sh -c 'ls /data | wc -l'   # now >0
```

Only a real `docker restart` fixes it. An idempotent `ensure-up.sh` will **not**: the container
*is* running, so the script correctly does nothing.

## Prevention

Make the start script probe for **content**, not for a running container — test for one sentinel
file you know exists rather than for a non-empty listing, so a partially visible mount is caught
too:

```bash
docker exec "$NAME" sh -c "test -e '/data/$SENTINEL'" || docker restart "$NAME"
```

Then write the whole procedure into `CLAUDE.md` as a self-healing rule, so the agent recognises
the symptom pattern and repairs it without you.

## Navigation

- [[GLOBAL/gotchas/_INDEX|Global gotchas]]
