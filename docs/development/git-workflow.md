# Git Workflow - LOs Generation System

## Branching Strategy

We use a **Gitflow-inspired** workflow optimized for AI-driven development with Claude Code integration.

### Branch Structure

```
main           # Production-ready code
├── develop    # Integration branch for features
├── feature/   # Feature development branches  
├── bugfix/    # Bug fix branches
├── hotfix/    # Production hotfixes
└── release/   # Release preparation branches
```

### Branch Naming Conventions

#### Feature Branches
```
feature/epic-{number}-{short-description}
feature/story-{number}-{short-description}
feature/task-{short-description}
```

**Examples:**
- `feature/epic-2-rag-pipeline`
- `feature/story-3-1-lo-generation-engine`
- `feature/task-add-bloom-taxonomy-validation`

#### Bug Fix Branches
```
bugfix/issue-{number}-{short-description}
bugfix/{short-description}
```

**Examples:**
- `bugfix/issue-45-vector-search-timeout`
- `bugfix/gemini-api-rate-limiting`

#### Hotfix Branches
```
hotfix/v{version}-{short-description}
```

**Examples:**
- `hotfix/v1.0.1-database-connection-leak`
- `hotfix/v1.0.2-security-patch`

#### Release Branches
```
release/v{major.minor}
```

**Examples:**
- `release/v1.0`
- `release/v1.1`

## Development Workflow

### 1. Starting New Work

```bash
# Ensure you're on develop with latest changes
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/story-3-2-api-endpoints-integration

# Push branch to remote
git push -u origin feature/story-3-2-api-endpoints-integration
```

### 2. Development Process

```bash
# Make commits frequently with clear messages
git add .
git commit -m "feat(api): add learning objectives CRUD endpoints

- Implement GET /learning-objectives with pagination
- Add POST /learning-objectives with validation
- Include proper error handling and responses
- Add comprehensive tests for new endpoints

Closes #42"

# Push changes regularly
git push origin feature/story-3-2-api-endpoints-integration
```

### 3. Code Review and Merging

```bash
# Create pull request (via GitHub/GitLab UI)
# After approval, merge with --no-ff to preserve branch history
git checkout develop
git pull origin develop
git merge --no-ff feature/story-3-2-api-endpoints-integration
git push origin develop

# Clean up feature branch
git branch -d feature/story-3-2-api-endpoints-integration
git push origin --delete feature/story-3-2-api-endpoints-integration
```

### 4. Release Process

```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v1.0

# Bump version numbers, update changelogs
# Test thoroughly in staging environment

# Merge to main and tag
git checkout main
git pull origin main
git merge --no-ff release/v1.0
git tag -a v1.0.0 -m "Release v1.0.0: Initial MVP release"
git push origin main --tags

# Merge back to develop
git checkout develop
git merge --no-ff release/v1.0
git push origin develop

# Clean up release branch
git branch -d release/v1.0
```

### 5. Hotfix Process

```bash
# Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/v1.0.1-critical-security-fix

# Make necessary changes and test
git commit -m "fix(security): patch SQL injection vulnerability

- Sanitize user input in learning objectives endpoint
- Add parameterized queries throughout API layer
- Update security tests

Fixes #78"

# Merge to main
git checkout main
git merge --no-ff hotfix/v1.0.1-critical-security-fix
git tag -a v1.0.1 -m "Hotfix v1.0.1: Security patch"
git push origin main --tags

# Merge to develop
git checkout develop
git merge --no-ff hotfix/v1.0.1-critical-security-fix
git push origin develop

# Clean up hotfix branch
git branch -d hotfix/v1.0.1-critical-security-fix
```

## Commit Message Standards

### Conventional Commits Format

```
<type>(<scope>): <description>

<body>

<footer>
```

### Commit Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Build process or auxiliary tool changes
- **ci**: CI/CD pipeline changes

### Scope Examples

- **api**: API endpoints and routing
- **services**: Business logic services
- **models**: Database models and schemas
- **tasks**: Celery background tasks
- **config**: Configuration changes
- **docker**: Docker and deployment
- **tests**: Test-related changes

### Commit Message Examples

```bash
# Feature addition
git commit -m "feat(services): implement LO generation with Gemini API

- Add LLMService for Gemini API integration
- Implement structured output validation with Pydantic AI
- Add retry logic for API rate limiting
- Include quality scoring for generated objectives

Implements story #31"

# Bug fix
git commit -m "fix(vector): resolve Qdrant connection timeout issues

- Increase connection timeout from 5s to 30s
- Add connection retry logic with exponential backoff
- Improve error messages for debugging
- Add health check for Qdrant connectivity

Fixes #67"

# Documentation
git commit -m "docs(api): add OpenAPI schema examples

- Include request/response examples for all endpoints
- Add authentication documentation
- Document error response formats
- Update README with API usage guide"

# Refactoring
git commit -m "refactor(database): optimize query performance

- Add database indexes for common query patterns
- Optimize repository methods with eager loading
- Reduce N+1 query problems in API endpoints
- Add query performance tests"
```

## Claude Code Integration

### Working with AI Assistance

When working with Claude Code, include context in commit messages:

```bash
git commit -m "feat(api): implement job status endpoint with Claude Code

- Generated comprehensive REST API implementation
- Added async job tracking with UUID identifiers
- Included proper error handling and validation
- Added unit and integration tests

Co-authored-by: Claude <noreply@anthropic.com>
Generated with Claude Code"
```

### AI-Generated Code Review

Before committing AI-generated code:

1. **Review thoroughly**: Understand what the code does
2. **Test comprehensively**: Run full test suite
3. **Validate business logic**: Ensure it meets requirements
4. **Check security**: Review for potential vulnerabilities
5. **Optimize performance**: Profile for bottlenecks

## Pull Request Guidelines

### PR Title Format

```
<type>(<scope>): <description> [#issue-number]
```

**Examples:**
- `feat(api): add learning objectives CRUD endpoints [#42]`
- `fix(vector): resolve Qdrant connection issues [#67]`
- `docs(deployment): add production setup guide [#89]`

### PR Description Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance impact assessed

## Security Considerations
- [ ] No sensitive data exposed
- [ ] Input validation implemented
- [ ] Authentication/authorization checked
- [ ] SQL injection prevention verified

## Deployment Notes
- [ ] Database migrations included
- [ ] Environment variables documented
- [ ] Configuration changes noted
- [ ] Rollback procedure documented

## Related Issues
Closes #issue-number
Relates to #other-issue

## AI Assistance
- [ ] Code generated with Claude Code
- [ ] AI-generated code reviewed and validated
- [ ] Business logic verified manually
- [ ] Security implications assessed

## Screenshots/Demos
(Include if applicable)
```

### Code Review Checklist

#### For Reviewers
- **Functionality**: Does it work as intended?
- **Code Quality**: Is it readable and maintainable?
- **Performance**: Are there performance implications?
- **Security**: Any security vulnerabilities?
- **Tests**: Are there adequate tests?
- **Documentation**: Is documentation updated?

#### For Authors
- **Self-review**: Review your own PR first
- **Test coverage**: Ensure adequate test coverage
- **Documentation**: Update relevant documentation
- **Breaking changes**: Clearly communicate any breaking changes
- **Dependencies**: Document new dependencies

## Branch Protection Rules

### Main Branch
- **Require pull request reviews**: At least 1 reviewer
- **Require status checks**: All CI tests must pass
- **Require branches to be up to date**: Must be current with main
- **Restrict pushes**: No direct pushes allowed
- **Require signed commits**: For security

### Develop Branch
- **Require pull request reviews**: At least 1 reviewer
- **Require status checks**: All CI tests must pass
- **Allow force pushes**: For maintainers only
- **Restrict pushes**: No direct pushes from contributors

## Git Configuration

### Required Git Config

```bash
# User identification
git config --global user.name "Your Name"
git config --global user.email "your.email@company.com"

# Commit signing (recommended)
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_GPG_KEY_ID

# Editor and merge tool
git config --global core.editor "code --wait"
git config --global merge.tool vscode

# Line ending handling
git config --global core.autocrlf input    # Linux/Mac
git config --global core.autocrlf true     # Windows

# Default branch name
git config --global init.defaultBranch main
```

### Useful Git Aliases

```bash
# Add to ~/.gitconfig or run as git config commands
[alias]
    co = checkout
    br = branch
    ci = commit
    st = status
    unstage = reset HEAD --
    last = log -1 HEAD
    visual = !gitk
    
    # Enhanced logging
    lg = log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit
    
    # Clean up merged branches
    cleanup = "!git branch --merged | grep -v '\\*\\|main\\|develop' | xargs -n 1 git branch -d"
    
    # Quick amend
    amend = commit --amend --no-edit
    
    # Interactive rebase
    rebase-interactive = rebase -i
```

## Workflow Automation

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        args: [--line-length=100]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
```

### Git Hooks Setup

```bash
# Install pre-commit hooks
make hooks-install

# Run hooks on all files
make hooks-update

# Manual hook execution
poetry run pre-commit run --all-files
```

This Git workflow ensures code quality, traceability, and smooth collaboration while supporting AI-assisted development patterns.