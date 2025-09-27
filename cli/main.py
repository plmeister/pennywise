import typer
import httpx
import json
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from rich import print

app = typer.Typer()
session = PromptSession(history=InMemoryHistory())

def load_schema(client):
    res = client.get("/openapi.json")
    res.raise_for_status()
    return res.json()

def build_completer(schema):
    ops = []
    for path, methods in schema.get("paths", {}).items():
        for m in methods:
            ops.append(f"{m.upper()} {path}")
    return WordCompleter(ops, ignore_case=True)

@app.command()
def interactive(url: str = typer.Option("http://localhost:8000", help="Base URL of your FastAPI server")):
    """
    Start interactive CLI session connected to FastAPI backend.
    """
    client = httpx.Client(base_url=url)
    schema = load_schema(client)
    completer = build_completer(schema)

    print(f"[cyan]Connected to {url}[/cyan]. Type 'help' for commands.")

    while True:
        try:
            line = session.prompt("> ", completer=completer)
            if not line.strip():
                continue
            cmd = line.strip().split(" ", 2)
            verb = cmd[0].lower()

            if verb in ("exit", "quit"):
                break
            if verb == "help":
                print("[green]Available commands:[/green] GET, POST, PUT, PATCH, DELETE + path + optional JSON body")
                continue

            method, path = cmd[0], cmd[1]
            payload = {}
            if len(cmd) == 3:
                try:
                    payload = json.loads(cmd[2])
                except json.JSONDecodeError as e:
                    print(f"[red]❌ Invalid JSON:{e}[/red]")
                    continue

            resp = client.request(method=method.upper(), url=path, json=payload or None)
            print(f"[bold green]Status {resp.status_code}[/bold green]")
            try:
                data = resp.json()
                print(json.dumps(data, indent=2))
            except (ValueError, httpx.HTTPError):
                print(resp.text)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            print(f"[red]Error:[/red] {e}")

    client.close()

if __name__ == "__main__":
    app()
