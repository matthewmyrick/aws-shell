"""Command registry for AWS Shell."""
from rich.console import Console

console = Console()


class CommandRegistry:
    def __init__(self, config, session_manager):
        self.config = config
        self.session_manager = session_manager
        self._commands = {}
        self._register_all()

    def _register_all(self):
        from .general import register as register_general
        from .help_cmd import register as register_help
        from .ec2 import register as register_ec2
        from .s3 import register as register_s3
        from .lambda_cmd import register as register_lambda
        from .iam import register as register_iam
        from .sts import register as register_sts
        from .cloudformation import register as register_cfn
        from .python_cmd import register as register_python
        from .ses import register as register_ses
        from .sqs import register as register_sqs
        from .rds import register as register_rds
        from .opensearch import register as register_opensearch
        from .route53 import register as register_route53
        from .globalaccelerator import register as register_ga
        from .cloudfront import register as register_cloudfront
        from .cloudwatch import register as register_cw
        from .secrets import register as register_secrets
        from .dynamodb import register as register_dynamodb
        from .ssm import register as register_ssm
        from .ecs import register as register_ecs
        from .sso import register as register_sso
        from .cache import register as register_cache
        from .cognito import register as register_cognito
        from .kms import register as register_kms
        from .vpc import register as register_vpc
        from .search_cmd import register as register_search
        from .ai_cmd import register as register_ai

        register_general(self)
        register_help(self)
        register_ec2(self)
        register_s3(self)
        register_lambda(self)
        register_iam(self)
        register_sts(self)
        register_cfn(self)
        register_python(self)
        register_ses(self)
        register_sqs(self)
        register_rds(self)
        register_opensearch(self)
        register_route53(self)
        register_ga(self)
        register_cloudfront(self)
        register_cw(self)
        register_secrets(self)
        register_dynamodb(self)
        register_ssm(self)
        register_ecs(self)
        register_sso(self)
        register_cache(self)
        register_cognito(self)
        register_kms(self)
        register_vpc(self)
        register_search(self)
        register_ai(self)

    def register(self, name, handler, help_text=""):
        self._commands[name] = {
            "handler": handler,
            "help": help_text,
        }

    def dispatch(self, command, args):
        if command in self._commands:
            try:
                self._commands[command]["handler"](
                    args, self.config, self.session_manager
                )
            except (EOFError, KeyboardInterrupt):
                raise
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
        else:
            console.print(
                f"[bold red]Unknown command:[/bold red] {command}\n"
                f"Type [bold cyan]help[/bold cyan] to see available commands."
            )

    def get_all_commands(self):
        return self._commands
