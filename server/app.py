"""ASGI entrypoint for OpenEnv validators and deployment tooling."""

from .main import app as app
from .main import main as run_server


def main() -> None:
	"""Run the backend server entrypoint."""

	run_server()


if __name__ == "__main__":
	main()