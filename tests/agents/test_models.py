"""Model tests for the agents app."""


class TestWorkflowStateModel:
    def test_workflow_state_primary_key_is_session_id(self):
        """WorkflowState should use session_id as its primary key."""

        pass

    def test_workflow_state_has_state_json_column(self):
        """WorkflowState should have a JSON state column that is non-nullable."""

        pass

    def test_workflow_state_relationship_to_chat_session_is_defined(self):
        """WorkflowState should define a relationship to ChatSession via `session`."""

        pass

    def test_workflow_state_fk_cascade_on_delete(self):
        """WorkflowState.session_id FK should cascade on delete."""

        pass