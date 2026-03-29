"""CLI bootstrap for local development."""

import uvicorn



def main() -> None:
    uvicorn.run("beta_engine.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
