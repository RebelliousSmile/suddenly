"""
Railway Debug Script

Interroge l'API GraphQL Railway pour récupérer les infos de déploiement.
Lit RAILWAY_TOKEN depuis le fichier .env — le token ne transite jamais par le chat.

Usage:
    python scripts/railway_debug.py
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


RAILWAY_API = "https://backboard.railway.app/graphql/v2"


def load_env(env_path: Path) -> dict[str, str]:
    """Charge les variables depuis le fichier .env."""
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def gql(token: str, query: str, variables: dict | None = None) -> dict:
    """Exécute une requête GraphQL Railway."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        RAILWAY_API,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "railway-debug/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[HTTP {e.code}] {body}", file=sys.stderr)
        sys.exit(1)


def print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("="*60)


def main() -> None:
    # Charger le token
    env_path = Path(__file__).parent.parent / ".env"
    env = load_env(env_path)
    token = env.get("RAILWAY_TOKEN", "")
    if not token:
        print("RAILWAY_TOKEN manquant dans .env", file=sys.stderr)
        sys.exit(1)

    # 1. Projets
    print_section("PROJETS")
    result = gql(token, """
        query {
            projects {
                edges {
                    node {
                        id
                        name
                        environments {
                            edges {
                                node { id name }
                            }
                        }
                        services {
                            edges {
                                node { id name }
                            }
                        }
                    }
                }
            }
        }
    """)
    projects = result.get("data", {}).get("projects", {}).get("edges", [])
    if not projects:
        print("Aucun projet trouvé.")
        sys.exit(0)

    for p_edge in projects:
        project = p_edge["node"]
        print(f"\nProjet : {project['name']} (id={project['id']})")
        envs = project.get("environments", {}).get("edges", [])
        services = project.get("services", {}).get("edges", [])
        for e in envs:
            print(f"  Env    : {e['node']['name']} (id={e['node']['id']})")
        for s in services:
            print(f"  Service: {s['node']['name']} (id={s['node']['id']})")

    # Utiliser le premier projet/service/env
    project = projects[0]["node"]
    project_id = project["id"]
    service_edges = project.get("services", {}).get("edges", [])
    env_edges = project.get("environments", {}).get("edges", [])

    if not service_edges or not env_edges:
        print("Aucun service ou environnement disponible.")
        sys.exit(0)

    service_id = service_edges[0]["node"]["id"]
    service_name = service_edges[0]["node"]["name"]
    environment_id = env_edges[0]["node"]["id"]
    environment_name = env_edges[0]["node"]["name"]

    print(f"\nCible : service={service_name}, env={environment_name}")

    # 2. Dernier déploiement
    print_section("DERNIER DÉPLOIEMENT")
    result = gql(token, """
        query($serviceId: String!, $environmentId: String!) {
            deployments(
                first: 1
                input: { serviceId: $serviceId, environmentId: $environmentId }
            ) {
                edges {
                    node {
                        id
                        status
                        createdAt
                        url
                        staticUrl
                    }
                }
            }
        }
    """, {"serviceId": service_id, "environmentId": environment_id})

    deployments = result.get("data", {}).get("deployments", {}).get("edges", [])
    if not deployments:
        print("Aucun déploiement trouvé.")
        sys.exit(0)

    deployment = deployments[0]["node"]
    deployment_id = deployment["id"]
    print(f"ID     : {deployment_id}")
    print(f"Status : {deployment['status']}")
    print(f"Créé   : {deployment['createdAt']}")
    print(f"URL    : {deployment.get('url') or deployment.get('staticUrl') or 'N/A'}")

    # 3. Build logs
    print_section("LOGS DE BUILD (100 dernières lignes)")
    result = gql(token, """
        query($deploymentId: String!) {
            buildLogs(deploymentId: $deploymentId, limit: 100) {
                message
                severity
                timestamp
            }
        }
    """, {"deploymentId": deployment_id})

    build_logs = result.get("data", {}).get("buildLogs", [])
    if build_logs:
        for log in build_logs:
            ts = log.get("timestamp", "")[:19]
            sev = log.get("severity", "INFO")
            msg = log.get("message", "")
            print(f"[{ts}] [{sev}] {msg}")
    else:
        print("Aucun log de build.")
        if result.get("errors"):
            print("Erreur API:", result["errors"])

    # 4. Runtime logs
    print_section("LOGS RUNTIME (100 dernières lignes)")
    result = gql(token, """
        query($deploymentId: String!) {
            deploymentLogs(deploymentId: $deploymentId, limit: 100) {
                message
                severity
                timestamp
            }
        }
    """, {"deploymentId": deployment_id})

    runtime_logs = result.get("data", {}).get("deploymentLogs", [])
    if runtime_logs:
        for log in runtime_logs:
            ts = log.get("timestamp", "")[:19]
            sev = log.get("severity", "INFO")
            msg = log.get("message", "")
            print(f"[{ts}] [{sev}] {msg}")
    else:
        print("Aucun log runtime.")
        if result.get("errors"):
            print("Erreur API:", result["errors"])

    # 4. Variables d'environnement (noms uniquement, pas les valeurs)
    print_section("VARIABLES D'ENVIRONNEMENT (noms)")
    result = gql(token, """
        query($projectId: String!, $serviceId: String!, $environmentId: String!) {
            variables(
                projectId: $projectId
                serviceId: $serviceId
                environmentId: $environmentId
            )
        }
    """, {
        "projectId": project_id,
        "serviceId": service_id,
        "environmentId": environment_id,
    })

    variables = result.get("data", {}).get("variables", {})
    if isinstance(variables, dict):
        for key in sorted(variables.keys()):
            val = variables[key]
            # Masquer les valeurs sensibles
            masked = val[:4] + "****" if len(val) > 4 else "****"
            print(f"  {key} = {masked}")
    elif result.get("errors"):
        print("Erreur API:", result["errors"])
    else:
        print("Aucune variable trouvée.")


if __name__ == "__main__":
    main()
