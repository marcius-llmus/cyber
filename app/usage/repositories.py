from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert

from app.commons.repositories import BaseRepository
from app.usage.models import GlobalProviderUsage, SessionUsage


class UsageRepository(BaseRepository[SessionUsage]):
    model = SessionUsage

    async def get_by_session_id(self, session_id: int) -> SessionUsage | None:
        stmt = select(self.model).where(self.model.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_usage(
        self,
        session_id: int,
        cost: Decimal,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
    ) -> SessionUsage:
        stmt = (
            insert(self.model)
            .values(
                session_id=session_id,
                cost=cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
            )
            .on_conflict_do_update(
                index_elements=[self.model.session_id],
                set_={
                    "cost": self.model.cost + cost,
                    "input_tokens": self.model.input_tokens + input_tokens,
                    "output_tokens": self.model.output_tokens + output_tokens,
                    "cached_tokens": self.model.cached_tokens + cached_tokens,
                },
            )
            .returning(self.model)
        )

        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one()


class GlobalUsageRepository(BaseRepository[GlobalProviderUsage]):
    model = GlobalProviderUsage

    async def get_total_global_cost(self) -> Decimal:
        stmt = select(func.sum(self.model.total_cost))
        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar() or 0.0))

    async def increment_provider_usage(
        self,
        provider: str,
        cost: Decimal,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
    ) -> GlobalProviderUsage:
        # Atomic UPSERT ensures thread-safety without explicit locking. The DB handles the lock.
        stmt = (
            insert(self.model)
            .values(
                provider=provider,
                total_cost=cost,
                total_input_tokens=input_tokens,
                total_output_tokens=output_tokens,
                total_cached_tokens=cached_tokens,
            )
            .on_conflict_do_update(
                index_elements=[self.model.provider],
                set_={
                    "total_cost": self.model.total_cost + cost,
                    "total_input_tokens": self.model.total_input_tokens + input_tokens,
                    "total_output_tokens": self.model.total_output_tokens
                    + output_tokens,
                    "total_cached_tokens": self.model.total_cached_tokens
                    + cached_tokens,
                },
            )
            .returning(self.model)
        )

        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one()
