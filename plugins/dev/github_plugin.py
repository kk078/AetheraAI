"""
GitHub Plugin for Aethera
Manages repositories, issues, PRs, and file operations.
"""
import asyncio
from typing import Any, Dict, List, Optional
import aiohttp
from ..plugin_base import AetheraPlugin, PluginConfig, PluginParameter, PluginResult


class GitHubPlugin(AetheraPlugin):
    """GitHub integration plugin."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.token = config.get('token', '')
        self._session: Optional[aiohttp.ClientSession] = None

    def get_config(self) -> PluginConfig:
        return PluginConfig(
            name='github',
            version='1.0.0',
            description='GitHub repository, issue, and PR management',
            author='Aethera AI',
            parameters=[
                PluginParameter(
                    name='action',
                    type='action',
                    description='Action to perform',
                    required=True,
                    choices=[
                        'get_repo', 'list_repos',
                        'get_issue', 'create_issue', 'update_issue', 'close_issue',
                        'get_pr', 'create_pr', 'merge_pr', 'list_prs',
                        'get_file', 'create_file', 'update_file', 'delete_file',
                        'create_branch', 'delete_branch',
                        'list_commits', 'get_commit',
                    ]
                ),
                PluginParameter(name='repo', type='str', description='Repository (owner/name)', required=False),
                PluginParameter(name='owner', type='str', description='Repository owner', required=False),
                PluginParameter(name='name', type='str', description='Repository/file name', required=False),
                PluginParameter(name='path', type='str', description='File path in repo', required=False),
                PluginParameter(name='content', type='str', description='File content', required=False),
                PluginParameter(name='message', type='str', description='Commit message', required=False),
                PluginParameter(name='branch', type='str', description='Branch name', required=False),
                PluginParameter(name='base', type='str', description='Base branch for PR', required=False),
                PluginParameter(name='title', type='str', description='Issue/PR title', required=False),
                PluginParameter(name='body', type='str', description='Issue/PR body', required=False),
                PluginParameter(name='issue_number', type='int', description='Issue/PR number', required=False),
                PluginParameter(name='labels', type='list', description='Labels to add', required=False),
                PluginParameter(name='assignees', type='list', description='Assignees', required=False),
            ],
            permissions=['repo', 'read:user', 'user:email'],
            dependencies=['aiohttp'],
        )

    async def _do_initialize(self) -> None:
        """Initialize HTTP session."""
        if not self.token:
            raise ValueError("GitHub token is required")

        self._session = aiohttp.ClientSession(
            headers={
                'Authorization': f'token {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/vnd.github.v3+json',
            }
        )

    async def cleanup(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        await super().cleanup()

    async def execute(self, action: str, parameters: Dict[str, Any]) -> PluginResult:
        """Execute GitHub action."""
        action_map = {
            'get_repo': self._get_repo,
            'list_repos': self._list_repos,
            'get_issue': self._get_issue,
            'create_issue': self._create_issue,
            'update_issue': self._update_issue,
            'close_issue': self._close_issue,
            'get_pr': self._get_pr,
            'create_pr': self._create_pr,
            'merge_pr': self._merge_pr,
            'list_prs': self._list_prs,
            'get_file': self._get_file,
            'create_file': self._create_file,
            'update_file': self._update_file,
            'delete_file': self._delete_file,
            'create_branch': self._create_branch,
            'delete_branch': self._delete_branch,
            'list_commits': self._list_commits,
            'get_commit': self._get_commit,
        }

        if action not in action_map:
            return PluginResult(success=False, error=f"Unknown action: {action}")

        try:
            result = await action_map[action](parameters)
            return PluginResult(success=True, data=result)
        except Exception as e:
            return PluginResult(success=False, error=str(e))

    def _parse_repo(self, params: Dict) -> tuple:
        """Parse repo string or owner/name params."""
        repo = params.get('repo', '')
        if '/' in repo:
            owner, name = repo.split('/', 1)
        else:
            owner = params.get('owner', '')
            name = params.get('name', '')
        return owner, name

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make GitHub API request."""
        url = f"https://api.github.com/{endpoint}"
        async with self._session.request(method, url, json=data) as resp:
            if resp.status >= 400:
                error = await resp.json()
                raise Exception(f"GitHub API error: {error.get('message', 'Unknown error')}")
            return await resp.json()

    async def _get_repo(self, params: Dict) -> Dict:
        """Get repository info."""
        owner, name = self._parse_repo(params)
        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")

        result = await self._request('GET', f'repos/{owner}/{name}')
        return {
            'name': result['name'],
            'full_name': result['full_name'],
            'description': result.get('description', ''),
            'private': result.get('private', False),
            'stars': result.get('stargazers_count', 0),
            'forks': result.get('forks_count', 0),
            'default_branch': result.get('default_branch', 'main'),
        }

    async def _list_repos(self, params: Dict) -> List[Dict]:
        """List user repositories."""
        result = await self._request('GET', 'user/repos?sort=updated&per_page=100')
        return [
            {
                'name': r['name'],
                'full_name': r['full_name'],
                'description': r.get('description', ''),
                'private': r.get('private', False),
                'updated': r.get('updated_at', ''),
            }
            for r in result
        ]

    async def _get_issue(self, params: Dict) -> Dict:
        """Get issue details."""
        owner, name = self._parse_repo(params)
        issue_number = params.get('issue_number')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not issue_number:
            raise ValueError("Issue number is required")

        result = await self._request('GET', f'repos/{owner}/{name}/issues/{issue_number}')
        return {
            'number': result['number'],
            'title': result['title'],
            'body': result.get('body', ''),
            'state': result.get('state', 'open'),
            'labels': [l['name'] for l in result.get('labels', [])],
            'assignees': [a['login'] for a in result.get('assignees', [])],
        }

    async def _create_issue(self, params: Dict) -> Dict:
        """Create new issue."""
        owner, name = self._parse_repo(params)

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not params.get('title'):
            raise ValueError("Issue title is required")

        data = {
            'title': params['title'],
            'body': params.get('body', ''),
        }
        if params.get('labels'):
            data['labels'] = params['labels']
        if params.get('assignees'):
            data['assignees'] = params['assignees']

        result = await self._request('POST', f'repos/{owner}/{name}/issues', data)
        return {'number': result['number'], 'url': result['html_url']}

    async def _update_issue(self, params: Dict) -> Dict:
        """Update issue."""
        owner, name = self._parse_repo(params)
        issue_number = params.get('issue_number')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not issue_number:
            raise ValueError("Issue number is required")

        data = {}
        if params.get('title'):
            data['title'] = params['title']
        if params.get('body'):
            data['body'] = params['body']
        if params.get('labels'):
            data['labels'] = params['labels']
        if params.get('assignees'):
            data['assignees'] = params['assignees']

        result = await self._request('PATCH', f'repos/{owner}/{name}/issues/{issue_number}', data)
        return {'number': result['number'], 'url': result['html_url']}

    async def _close_issue(self, params: Dict) -> bool:
        """Close issue."""
        owner, name = self._parse_repo(params)
        issue_number = params.get('issue_number')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not issue_number:
            raise ValueError("Issue number is required")

        await self._request('PATCH', f'repos/{owner}/{name}/issues/{issue_number}', {'state': 'closed'})
        return True

    async def _get_pr(self, params: Dict) -> Dict:
        """Get PR details."""
        owner, name = self._parse_repo(params)
        pr_number = params.get('pr_number') or params.get('issue_number')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not pr_number:
            raise ValueError("PR number is required")

        result = await self._request('GET', f'repos/{owner}/{name}/pulls/{pr_number}')
        return {
            'number': result['number'],
            'title': result['title'],
            'state': result.get('state', 'open'),
            'head': result['head']['ref'],
            'base': result['base']['ref'],
            'merged': result.get('merged', False),
            'url': result['html_url'],
        }

    async def _create_pr(self, params: Dict) -> Dict:
        """Create pull request."""
        owner, name = self._parse_repo(params)

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not params.get('title'):
            raise ValueError("PR title is required")
        if not params.get('head'):
            raise ValueError("Head branch is required")

        data = {
            'title': params['title'],
            'head': params['head'],
            'base': params.get('base', 'main'),
            'body': params.get('body', ''),
        }

        result = await self._request('POST', f'repos/{owner}/{name}/pulls', data)
        return {'number': result['number'], 'url': result['html_url']}

    async def _merge_pr(self, params: Dict) -> Dict:
        """Merge pull request."""
        owner, name = self._parse_repo(params)
        pr_number = params.get('pr_number') or params.get('issue_number')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not pr_number:
            raise ValueError("PR number is required")

        result = await self._request(
            'PUT',
            f'repos/{owner}/{name}/pulls/{pr_number}/merge',
            {'commit_message': params.get('commit_message', '')}
        )
        return {'merged': result.get('merged', False), 'sha': result.get('sha', '')}

    async def _list_prs(self, params: Dict) -> List[Dict]:
        """List pull requests."""
        owner, name = self._parse_repo(params)

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")

        state = params.get('state', 'open')
        result = await self._request('GET', f'repos/{owner}/{name}/pulls?state={state}&per_page=50')
        return [
            {
                'number': pr['number'],
                'title': pr['title'],
                'head': pr['head']['ref'],
                'base': pr['base']['ref'],
                'user': pr['user']['login'],
            }
            for pr in result
        ]

    async def _get_file(self, params: Dict) -> Dict:
        """Get file content."""
        owner, name = self._parse_repo(params)
        path = params.get('path', '')
        branch = params.get('branch', 'main')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not path:
            raise ValueError("File path is required")

        result = await self._request('GET', f'repos/{owner}/{name}/contents/{path}?ref={branch}')

        # Decode content
        import base64
        content = base64.b64decode(result['content']).decode('utf-8')

        return {
            'path': result['path'],
            'content': content,
            'sha': result['sha'],
            'size': result['size'],
        }

    async def _create_file(self, params: Dict) -> Dict:
        """Create new file."""
        owner, name = self._parse_repo(params)
        path = params.get('path', '')
        content = params.get('content', '')
        message = params.get('message', f'Create {path}')
        branch = params.get('branch', 'main')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not path:
            raise ValueError("File path is required")

        import base64
        data = {
            'message': message,
            'content': base64.b64encode(content.encode()).decode(),
            'branch': branch,
        }

        result = await self._request('PUT', f'repos/{owner}/{name}/contents/{path}', data)
        return {'path': result['content']['path'], 'sha': result['content']['sha']}

    async def _update_file(self, params: Dict) -> Dict:
        """Update existing file."""
        owner, name = self._parse_repo(params)
        path = params.get('path', '')
        content = params.get('content', '')
        message = params.get('message', f'Update {path}')
        branch = params.get('branch', 'main')
        sha = params.get('sha')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not path:
            raise ValueError("File path is required")

        import base64
        data = {
            'message': message,
            'content': base64.b64encode(content.encode()).decode(),
            'branch': branch,
        }

        # Get current SHA if not provided
        if not sha:
            current = await self._get_file(params)
            data['sha'] = current['sha']
        else:
            data['sha'] = sha

        result = await self._request('PUT', f'repos/{owner}/{name}/contents/{path}', data)
        return {'path': result['content']['path'], 'sha': result['content']['sha']}

    async def _delete_file(self, params: Dict) -> bool:
        """Delete file."""
        owner, name = self._parse_repo(params)
        path = params.get('path', '')
        message = params.get('message', f'Delete {path}')
        branch = params.get('branch', 'main')
        sha = params.get('sha')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not path:
            raise ValueError("File path is required")

        # Get SHA if not provided
        if not sha:
            current = await self._get_file({**params, 'branch': branch})
            sha = current['sha']

        data = {
            'message': message,
            'sha': sha,
            'branch': branch,
        }

        await self._request('DELETE', f'repos/{owner}/{name}/contents/{path}', data)
        return True

    async def _create_branch(self, params: Dict) -> Dict:
        """Create branch from another branch."""
        owner, name = self._parse_repo(params)
        branch = params.get('branch')
        base = params.get('base', 'main')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not branch:
            raise ValueError("Branch name is required")

        # Get base branch SHA
        ref_result = await self._request('GET', f'repos/{owner}/{name}/git/refs/heads/{base}')
        sha = ref_result['object']['sha']

        # Create new branch
        result = await self._request('POST', f'repos/{owner}/{name}/git/refs', {
            'ref': f'refs/heads/{branch}',
            'sha': sha,
        })
        return {'ref': result['ref'], 'sha': result['object']['sha']}

    async def _delete_branch(self, params: Dict) -> bool:
        """Delete branch."""
        owner, name = self._parse_repo(params)
        branch = params.get('branch')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not branch:
            raise ValueError("Branch name is required")

        await self._request('DELETE', f'repos/{owner}/{name}/git/refs/heads/{branch}')
        return True

    async def _list_commits(self, params: Dict) -> List[Dict]:
        """List commits."""
        owner, name = self._parse_repo(params)
        branch = params.get('branch', 'main')
        path = params.get('path', '')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")

        endpoint = f'repos/{owner}/{name}/commits?sha={branch}&per_page=50'
        if path:
            endpoint += f'&path={path}'

        result = await self._request('GET', endpoint)
        return [
            {
                'sha': c['sha'][:7],
                'message': c['commit']['message'].split('\n')[0],
                'author': c['commit']['author']['name'],
                'date': c['commit']['author']['date'],
            }
            for c in result
        ]

    async def _get_commit(self, params: Dict) -> Dict:
        """Get commit details."""
        owner, name = self._parse_repo(params)
        sha = params.get('sha')

        if not owner or not name:
            raise ValueError("Repository (owner/name) is required")
        if not sha:
            raise ValueError("Commit SHA is required")

        result = await self._request('GET', f'repos/{owner}/{name}/commits/{sha}')
        return {
            'sha': result['sha'],
            'message': result['commit']['message'],
            'author': result['commit']['author']['name'],
            'date': result['commit']['author']['date'],
            'files_changed': len(result.get('files', [])),
        }


def register_plugin():
    """Register the GitHub plugin."""
    import os
    return GitHubPlugin, {
        'token': os.getenv('GITHUB_TOKEN', ''),
        'enabled': True,
    }
