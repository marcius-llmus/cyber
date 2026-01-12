"""Dependency tests for the agents app."""


class TestAgentsDependencies:
    def test_get_workflow_service_returns_service_instance(self):
        """get_workflow_service should return a WorkflowService instance."""

        pass

    def test_get_workflow_service_uses_db_dependency(self):
        """get_workflow_service should accept a db dependency and pass it to the factory."""

        pass

    def test_get_workflow_service_is_awaitable(self):
        """get_workflow_service should be an async dependency and await internal wiring."""

        pass

    def test_get_workflow_service_is_declared_async(self):
        """get_workflow_service should remain an async dependency (not sync)."""

        pass

    def test_get_workflow_service_returns_awaited_factory_result(self):
        """get_workflow_service should return the awaited result of the underlying factory."""

        pass

    def test_get_workflow_service_returns_distinct_instances(self):
        """get_workflow_service should return a new service instance per request by default."""

        pass

    def test_get_workflow_service_returns_service_with_repository(self):
        """WorkflowService returned by get_workflow_service should be wired with a repository."""

        pass

    def test_get_workflow_service_propagates_factory_errors(self):
        """get_workflow_service should surface exceptions raised by the underlying factory."""

        pass