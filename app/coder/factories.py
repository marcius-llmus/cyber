from app.coder.services.messaging import MessagingTurnEventHandler


async def build_messaging_turn_event_handler() -> MessagingTurnEventHandler:
    return MessagingTurnEventHandler()
