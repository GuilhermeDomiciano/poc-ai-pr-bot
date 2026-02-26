import importlib
import sys
from types import ModuleType
import unittest


class _FakeAgent:
    def __init__(self, role: str, goal: str, backstory: str, verbose: bool) -> None:
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.verbose = verbose


class _FakeTask:
    def __init__(
        self,
        description: str,
        expected_output: str,
        agent: _FakeAgent,
        context: list["_FakeTask"] | None = None,
    ) -> None:
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
        self.context = context or []


class _FakeCrew:
    def __init__(self, agents: list[_FakeAgent], tasks: list[_FakeTask], verbose: bool) -> None:
        self.agents = agents
        self.tasks = tasks
        self.verbose = verbose


class CrewFlowTests(unittest.TestCase):
    def _build_crew(self) -> _FakeCrew:
        fake_crewai_module = ModuleType("crewai")
        fake_crewai_module.Agent = _FakeAgent
        fake_crewai_module.Task = _FakeTask
        fake_crewai_module.Crew = _FakeCrew

        previous_crewai = sys.modules.get("crewai")
        previous_crew_flow = sys.modules.get("infrastructure.ai.crew_flow")
        try:
            sys.modules["crewai"] = fake_crewai_module
            if "infrastructure.ai.crew_flow" in sys.modules:
                del sys.modules["infrastructure.ai.crew_flow"]
            crew_flow_module = importlib.import_module("infrastructure.ai.crew_flow")
            return crew_flow_module.build_crew("Issue title", "Issue body", "repo tree")
        finally:
            if previous_crewai is None:
                sys.modules.pop("crewai", None)
            else:
                sys.modules["crewai"] = previous_crewai

            if previous_crew_flow is None:
                sys.modules.pop("infrastructure.ai.crew_flow", None)
            else:
                sys.modules["infrastructure.ai.crew_flow"] = previous_crew_flow

    def test_build_crew_creates_five_expected_agents(self) -> None:
        built_crew = self._build_crew()
        agent_roles = [agent.role for agent in built_crew.agents]
        self.assertEqual(
            agent_roles,
            [
                "Backend Dev",
                "Frontend Dev",
                "Integration Engineer",
                "QA Reviewer",
                "Git Integrator",
            ],
        )

    def test_build_crew_orders_tasks_and_contexts(self) -> None:
        built_crew = self._build_crew()

        self.assertEqual(len(built_crew.tasks), 5)
        backend_task, frontend_task, integration_task, qa_task, git_task = built_crew.tasks

        self.assertEqual(backend_task.agent.role, "Backend Dev")
        self.assertEqual(frontend_task.agent.role, "Frontend Dev")
        self.assertEqual(integration_task.agent.role, "Integration Engineer")
        self.assertEqual(qa_task.agent.role, "QA Reviewer")
        self.assertEqual(git_task.agent.role, "Git Integrator")

        self.assertEqual(frontend_task.context, [backend_task])
        self.assertEqual(integration_task.context, [backend_task, frontend_task])
        self.assertEqual(qa_task.context, [backend_task, frontend_task, integration_task])
        self.assertEqual(git_task.context, [backend_task, frontend_task, integration_task, qa_task])

        self.assertIn("ONLY files under `backend/`", backend_task.description)
        self.assertIn("ONLY files under `frontend/`", frontend_task.description)
        self.assertIn("`VITE_API_BASE_URL`", frontend_task.description)
        self.assertIn("`/workflow/run`", frontend_task.description)
        self.assertIn("You may edit files in BOTH `backend/` and `frontend/`", integration_task.description)
        self.assertIn("Return JSON only", git_task.description)


if __name__ == "__main__":
    unittest.main()
