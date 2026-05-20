from .base import LoginStrategy, LoginFailedError, MFARequiredError
from .linkedin import LinkedInStrategy
from .gmail import GmailStrategy
from .github import GitHubStrategy

STRATEGY_REGISTRY: dict[str, LoginStrategy] = {
    "linkedin": LinkedInStrategy(),
    "gmail": GmailStrategy(),
    "github": GitHubStrategy(),
}
