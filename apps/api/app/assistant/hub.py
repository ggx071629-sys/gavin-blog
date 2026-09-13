from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .constants import CODE_STREAM_LIMITED, SSE_SUBSCRIBERS_PER_IP, SSE_SUBSCRIBERS_PER_TURN
from .errors import limited


@dataclass
class TurnHub:
    turn_subs: dict[str, list[asyncio.Queue]] = field(default_factory=dict)
    ip_counts: dict[str, int] = field(default_factory=dict)
    turn_ips: dict[int, str] = field(default_factory=dict)

    def subscribe(self, turn_id: str, ip: str) -> asyncio.Queue:
        current = self.turn_subs.get(turn_id, [])
        if len(current) >= SSE_SUBSCRIBERS_PER_TURN:
            raise limited(CODE_STREAM_LIMITED, 5)
        if self.ip_counts.get(ip, 0) >= SSE_SUBSCRIBERS_PER_IP:
            raise limited(CODE_STREAM_LIMITED, 5)
        queue: asyncio.Queue = asyncio.Queue()
        self.turn_subs.setdefault(turn_id, []).append(queue)
        self.ip_counts[ip] = self.ip_counts.get(ip, 0) + 1
        self.turn_ips[id(queue)] = ip
        return queue

    def unsubscribe(self, turn_id: str, queue: asyncio.Queue) -> None:
        subs = self.turn_subs.get(turn_id, [])
        if queue in subs:
            subs.remove(queue)
        ip = self.turn_ips.pop(id(queue), None)
        if ip:
            self.ip_counts[ip] = max(0, self.ip_counts.get(ip, 1) - 1)

    def publish(self, turn_id: str, event_name: str, data_json: str) -> None:
        payload = {"event": event_name, "data": data_json}
        for queue in list(self.turn_subs.get(turn_id, [])):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                continue

    def close(self, turn_id: str) -> None:
        for queue in list(self.turn_subs.get(turn_id, [])):
            try:
                queue.put_nowait({"event": "_end", "data": "{}"})
            except asyncio.QueueFull:
                continue
