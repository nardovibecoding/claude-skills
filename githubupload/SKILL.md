---
name: githubupload
description: |
  Upload a local project to GitHub as a new public repo. Handles git init, README generation, .gitignore, and repo creation via gh CLI.

  USE FOR:
  - Uploading a new project to GitHub for the first time
  - Creating a GitHub repo from a local folder
  - Building out the user's GitHub profile with their projects

allowed-tools:
  - Bash(gh *)
  - Bash(git *)
  - Read
  - Write
  - Glob
---

# GitHub Upload Skill

Uploads a local project folder to GitHub as a new repo. Follows this workflow:

## Steps

1. **Read the project** — explore the folder to understand what it is (language, purpose, structure)
2. **Show a summary** — list all files that will be uploaded and the proposed repo name/description. STOP and wait for user confirmation before proceeding.
3. **Prepare the repo locally:**
   - Create a `.gitignore` appropriate for the project type
   - Generate a clean `README.md` based on the actual code
   - Run `git init && git add . && git commit -m "Initial commit"`
4. **Create and push to GitHub:**
   - Use `gh repo create <name> --public --description "..." --push --source .`
5. **Confirm success** — output the repo URL

## Auth check

Before starting, verify gh is authenticated:
```bash
gh auth status
```

If not logged in, ask the user to run:
```bash
echo "TOKEN" | gh auth login --with-token
```

## README template

Generate a README with:
- Project name + one-liner description
- What it does (2-3 bullet points)
- How to install/use it
- Tech stack / built with

## Notes
- Always show summary and wait for confirmation before pushing
- Never push API keys, `.env` files, or credentials
- Default to `--public` unless user specifies private
- Strip `.DS_Store` and OS junk from `.gitignore`
