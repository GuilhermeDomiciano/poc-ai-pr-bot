CONTRACT_ERROR_PREFIX = "Integration contract violation"


class ContractViolationError(RuntimeError):
    """Raised when the AI payload violates the integration contract."""


def contract_error(details: str) -> ContractViolationError:
    return ContractViolationError(f"{CONTRACT_ERROR_PREFIX}: {details}")
