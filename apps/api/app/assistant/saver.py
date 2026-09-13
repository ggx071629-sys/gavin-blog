from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from .identity import ExecutionIdentity, normal_mutation_permit


class IdentityAwareSaver(BaseCheckpointSaver):
    """Fence LangGraph Saver I/O without modifying its pinned tables.

    The control check and Saver await deliberately use separate connections.
    The per-session lock, rather than a long SQLite transaction, closes the
    checkpoint-check -> DELETE -> commit race for the single API owner.
    """

    def __init__(self, online: Any, delegate: Any) -> None:
        super().__init__(serde=delegate.serde)
        self.online = online
        self.delegate = delegate
        self._identities: dict[str, ExecutionIdentity] = {}

    @property
    def config_specs(self):
        return self.delegate.config_specs

    def bind(self, identity: ExecutionIdentity) -> None:
        self._identities[identity.thread_id] = identity

    def unbind(self, identity: ExecutionIdentity) -> None:
        if self._identities.get(identity.thread_id) == identity:
            self._identities.pop(identity.thread_id, None)

    def _identity(self, config: dict[str, Any] | None) -> ExecutionIdentity:
        thread_id = str(((config or {}).get("configurable") or {}).get("thread_id") or "")
        identity = self._identities.get(thread_id)
        if identity is None:
            raise PermissionError("checkpoint execution identity is not bound")
        return identity

    def _permitted(self, identity: ExecutionIdentity) -> bool:
        return self.online.control.read(
            lambda conn: normal_mutation_permit(conn, identity, self.online.now())
        )

    def _terminal_committed(self, identity: ExecutionIdentity) -> bool:
        def _read(conn):
            row = conn.execute(
                """
                SELECT t.status, s.fencing_epoch, s.tombstoned_at
                FROM assistant_turns AS t
                JOIN assistant_sessions AS s ON s.id = t.session_id
                WHERE t.id = ? AND t.session_id = ?
                """,
                (identity.turn_id, identity.session_id),
            ).fetchone()
            return bool(
                row
                and row["status"] == "terminal"
                and row["tombstoned_at"] is None
                and int(row["fencing_epoch"]) == identity.fencing_epoch
            )

        return self.online.control.read(_read)

    async def aget_tuple(self, config):
        identity = self._identity(config)
        async with self.online.serialization.hold(identity.session_id):
            if not self._permitted(identity):
                raise PermissionError("checkpoint read fence rejected")
            return await self.delegate.aget_tuple(config)

    async def alist(
        self,
        config,
        *,
        filter: dict[str, Any] | None = None,
        before=None,
        limit: int | None = None,
    ) -> AsyncIterator[Any]:
        identity = self._identity(config)
        async with self.online.serialization.hold(identity.session_id):
            if not self._permitted(identity):
                raise PermissionError("checkpoint list fence rejected")
            items = [
                item
                async for item in self.delegate.alist(
                    config,
                    filter=filter,
                    before=before,
                    limit=limit,
                )
            ]
        for item in items:
            yield item

    async def aput(self, config, checkpoint, metadata, new_versions):
        identity = self._identity(config)
        async with self.online.serialization.hold(identity.session_id):
            if not self._permitted(identity):
                if self._terminal_committed(identity):
                    return config
                raise PermissionError("checkpoint write fence rejected")
            returned = await self.delegate.aput(config, checkpoint, metadata, new_versions)
            await self.online.saver_conn.commit()
            from .store import enforce_session_byte_cap

            self.online.control.immediate(
                lambda conn: enforce_session_byte_cap(
                    conn, identity.session_id, now=self.online.now()
                )
            )
            configurable = dict(config.get("configurable") or {})
            configurable.update(dict((returned or {}).get("configurable") or {}))
            configurable.update(
                {
                    "thread_id": identity.thread_id,
                    "assistant_session_id": identity.session_id,
                    "assistant_turn_id": identity.turn_id,
                    "assistant_fencing_epoch": identity.fencing_epoch,
                    "assistant_fencing_token": identity.fencing_token,
                    "assistant_operational_epoch": identity.operational_epoch,
                }
            )
            merged = dict(returned or config)
            merged["configurable"] = configurable
            return merged

    async def aput_writes(
        self,
        config,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        identity = self._identity(config)
        async with self.online.serialization.hold(identity.session_id):
            if not self._permitted(identity):
                if self._terminal_committed(identity):
                    return
                raise PermissionError("checkpoint writes fence rejected")
            await self.delegate.aput_writes(config, writes, task_id, task_path)
            await self.online.saver_conn.commit()
            from .store import enforce_session_byte_cap

            self.online.control.immediate(
                lambda conn: enforce_session_byte_cap(
                    conn, identity.session_id, now=self.online.now()
                )
            )

    # Intentionally replaces the base saver's thread-id API with an execution
    # identity (decision-public-qa-runtime-integrity).
    async def delete_thread(self, identity: ExecutionIdentity) -> bool:  # type: ignore[override]
        async with self.online.serialization.hold(identity.session_id):
            return await self.delete_thread_locked(identity)

    async def delete_thread_locked(self, identity: ExecutionIdentity) -> bool:
        await self.delegate.adelete_thread(identity.thread_id)
        await self.online.saver_conn.commit()
        return await self.thread_is_empty(identity.thread_id)

    async def thread_is_empty(self, thread_id: str) -> bool:
        async with self.online.saver_conn.execute(
            "SELECT (SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?) + "
            "(SELECT COUNT(*) FROM writes WHERE thread_id = ?)",
            (thread_id, thread_id),
        ) as cursor:
            row = await cursor.fetchone()
        return bool(row and int(row[0]) == 0)

    async def adelete_thread(self, thread_id: str) -> None:
        identity = self._identities.get(thread_id)
        if identity is None:
            raise PermissionError("checkpoint delete identity is not bound")
        if not await self.delete_thread(identity):
            raise RuntimeError("checkpoint rows remain after delete")
