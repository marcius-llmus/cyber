import logging

from llama_index.core.workflow import Context, Workflow

from app.agents.repositories import WorkflowStateRepository

logger = logging.getLogger(__name__)

class WorkflowService:
    def __init__(self, workflow_repo: WorkflowStateRepository):
        self.workflow_repo = workflow_repo

    async def get_context(self, session_id: int, workflow: Workflow) -> Context:
        """Hydrates a Context from the DB or creates a new one if none exists."""
        state_record = await self.workflow_repo.get_by_session_id(session_id)
        if state_record and state_record.state:
            return Context.from_dict(workflow, state_record.state)
        return Context(workflow)

    async def save_context(self, session_id: int, context: Context) -> None:
        """Persists the current Context state to the DB."""
        await self.workflow_repo.save_state(session_id, context.to_dict())
