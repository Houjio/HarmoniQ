import argparse
from harmoniq.webserver import app
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Lancer l'interface web",)
    parser.add_argument(
        "--debug", action="store_true", help="Activer le mode debug",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Adresse IP du serveur",
    )
    parser.add_argument(
        "--port", default=5000, help="Port du serveur",
    )

    args = parser.parse_args()
    uvicorn.run(
        "harmoniq.webserver:app", host=args.host, port=int(args.port), reload=args.debug
    )


if __name__ == "__main__":
    main()
