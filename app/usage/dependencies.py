from fastapi import Depends

from app.usage.services import UsagePageService, UsageService


async def get_usage_service() -> UsageService:
    return UsageService()


async def get_usage_page_service(
    usage_service: UsageService = Depends(get_usage_service),
) -> UsagePageService:
    return UsagePageService(usage_service=usage_service)