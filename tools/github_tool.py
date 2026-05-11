import logging
from github import Github, GithubException

import config

logger = logging.getLogger(__name__)

# Clientes separados para token pessoal e da empresa
_personal = Github(config.GITHUB_TOKEN_PERSONAL) if config.GITHUB_TOKEN_PERSONAL else None
_company = Github(config.GITHUB_TOKEN_COMPANY) if config.GITHUB_TOKEN_COMPANY else None


def _client_for(repo_name: str) -> Github | None:
    """Retorna o cliente correto baseado em qual lista o repo pertence."""
    if repo_name in config.GITHUB_REPOS_PERSONAL:
        return _personal
    if repo_name in config.GITHUB_REPOS_COMPANY:
        return _company
    return None


def list_repos() -> str:
    """Lista todos os repositórios configurados com descrição."""
    lines = []
    for label, client, repos in [
        ("Pessoal", _personal, config.GITHUB_REPOS_PERSONAL),
        ("Empresa", _company, config.GITHUB_REPOS_COMPANY),
    ]:
        if not client or not repos:
            continue
        lines.append(f"**{label}:**")
        for repo_name in repos:
            try:
                repo = client.get_repo(repo_name)
                desc = repo.description or "sem descrição"
                lines.append(f"  • {repo.full_name} — {desc}")
            except GithubException:
                logger.exception("Erro ao acessar repo %s", repo_name)
                lines.append(f"  • {repo_name} — erro ao acessar")

    return "\n".join(lines) if lines else "Nenhum repositório configurado."


def get_recent_commits(repo_name: str, limit: int = 5) -> str:
    """Retorna os últimos commits de um repositório."""
    client = _client_for(repo_name)
    if not client:
        return f"Repositório '{repo_name}' não encontrado na configuração."
    try:
        repo = client.get_repo(repo_name)
        commits = list(repo.get_commits()[:limit])
        if not commits:
            return f"Nenhum commit encontrado em {repo_name}."
        lines = [f"**Últimos commits — {repo_name}:**"]
        for c in commits:
            date_str = c.commit.author.date.strftime("%d/%m %H:%M")
            msg = c.commit.message.split("\n")[0][:80]
            author = c.commit.author.name
            lines.append(f"  • [{date_str}] {author}: {msg}")
        return "\n".join(lines)
    except GithubException:
        logger.exception("Erro ao buscar commits de %s", repo_name)
        return f"Erro ao acessar commits de {repo_name}."


def list_open_prs(repo_name: str) -> str:
    """Lista os pull requests abertos de um repositório."""
    client = _client_for(repo_name)
    if not client:
        return f"Repositório '{repo_name}' não encontrado na configuração."
    try:
        repo = client.get_repo(repo_name)
        prs = list(repo.get_pulls(state="open"))
        if not prs:
            return f"Nenhum PR aberto em {repo_name}."
        lines = [f"**PRs abertos — {repo_name}:**"]
        for pr in prs:
            lines.append(f"  • #{pr.number} {pr.title} (@{pr.user.login})")
        return "\n".join(lines)
    except GithubException:
        logger.exception("Erro ao buscar PRs de %s", repo_name)
        return f"Erro ao acessar PRs de {repo_name}."


def list_open_issues(repo_name: str, limit: int = 10) -> str:
    """Lista as issues abertas de um repositório."""
    client = _client_for(repo_name)
    if not client:
        return f"Repositório '{repo_name}' não encontrado na configuração."
    try:
        repo = client.get_repo(repo_name)
        issues = [i for i in repo.get_issues(state="open") if not i.pull_request][:limit]
        if not issues:
            return f"Nenhuma issue aberta em {repo_name}."
        lines = [f"**Issues abertas — {repo_name}:**"]
        for issue in issues:
            lines.append(f"  • #{issue.number} {issue.title}")
        return "\n".join(lines)
    except GithubException:
        logger.exception("Erro ao buscar issues de %s", repo_name)
        return f"Erro ao acessar issues de {repo_name}."


def get_file(repo_name: str, file_path: str, branch: str = "main") -> str:
    """Retorna o conteúdo de um arquivo de um repositório."""
    client = _client_for(repo_name)
    if not client:
        return f"Repositório '{repo_name}' não encontrado na configuração."
    try:
        repo = client.get_repo(repo_name)
        file_content = repo.get_contents(file_path, ref=branch)
        content = file_content.decoded_content.decode("utf-8")
        # Limita para não explodir o contexto do LLM
        if len(content) > 8000:
            content = content[:8000] + "\n\n[... arquivo truncado após 8000 chars ...]"
        return f"**{repo_name}/{file_path}** (branch: {branch})\n\n```\n{content}\n```"
    except GithubException:
        logger.exception("Erro ao acessar %s/%s", repo_name, file_path)
        return f"Erro ao acessar {file_path} em {repo_name}."


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print(list_repos())
