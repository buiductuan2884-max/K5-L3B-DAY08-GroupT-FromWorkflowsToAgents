"""In-process transport with seeded faults: drop, duplicate, delay, reorder.

Each fault fires independently with probability `fault_rate` on every leg
(request and response). Delay only adds simulated ms to a counter; there is no sleep.
Reorder holds a response back and delivers it after the next call's responses.
"""

from __future__ import annotations

import json
import random
from typing import Any


def size(env: dict[str, Any]) -> int:
    return len(json.dumps(env, ensure_ascii=False, sort_keys=True).encode("utf-8"))


class Transport:
    def __init__(self, agent, *, fault_rate: float, seed: int, claim_id: str) -> None:
        self.agent = agent
        self.p = fault_rate
        self.rng = random.Random(f"{seed}:{claim_id}")
        self.log: list[dict[str, Any]] = []  # every envelope put on the wire
        self.pending: list[dict[str, Any]] = []
        self.stats = {
            "sent": 0, "delivered": 0, "bytes_req": 0, "bytes_resp": 0, "delay_ms": 0,
            "drop": 0, "duplicate": 0, "delay": 0, "reorder": 0, "leaks": 0,
        }

    def _leg(self, env: dict[str, Any], kind: str) -> tuple[int, bool]:
        """Count one send; return (copies delivered, held back for reordering)."""
        self.stats["sent"] += 1
        self.log.append(env)
        if "CANARY_" in json.dumps(env, ensure_ascii=False):
            self.stats["leaks"] += 1
        drop, dup, delay, reorder = (self.rng.random() < self.p for _ in range(4))
        ms = self.rng.randint(50, 500)
        if delay:
            self.stats["delay"] += 1
            self.stats["delay_ms"] += ms
        if drop:
            self.stats["drop"] += 1
            return 0, False
        copies = 2 if dup else 1
        self.stats["duplicate"] += dup
        held = reorder and kind == "bytes_resp"
        self.stats["reorder"] += held
        if not held:
            self._count(env, kind, copies)
        return copies, held

    def _count(self, env: dict[str, Any], kind: str, copies: int) -> None:
        self.stats["delivered"] += copies
        self.stats[kind] += copies * size(env)

    def send(self, env: dict[str, Any]) -> list[dict[str, Any]]:
        """Orchestrator -> agent -> orchestrator. Returns responses in arrival order."""
        older, self.pending = self.pending, []  # held back by earlier calls: arrive last
        arrived: list[dict[str, Any]] = []
        copies, _ = self._leg(env, "bytes_req")
        for _ in range(copies):
            resp = self.agent.handle(json.loads(json.dumps(env)))
            n, held = self._leg(resp, "bytes_resp")
            if held:
                self.pending.append(resp)
            arrived += [json.loads(json.dumps(resp)) for _ in range(n)]
        for resp in older:
            self._count(resp, "bytes_resp", 1)
            arrived.append(json.loads(json.dumps(resp)))
        return arrived
