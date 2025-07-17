# Git Quick Reference

## Setup & Configuration

  • Set your identity:
      git config --global user.name "Your Name"
      git config --global user.email "you@example.com"

## Cloning Repositories

  • Clone a remote repo:
      git clone <repository-url>

## Checking Status

  • Show modified files:
      git status

## Staging Changes

  • Stage a file:
      git add <file>
  • Stage all changes:
      git add .

## Committing Changes

  • Commit staged changes with message:
      git commit -m "Your commit message"
  • Amend last commit (without changing message):
      git commit --amend --no-edit

## Pushing & Pulling

  • Push to remote:
      git push [<remote>] [<branch>]
  • Pull updates:
      git pull [<remote>] [<branch>]

## Branching & Merging

  • List branches:
      git branch
  • Create new branch:
      git branch <branch-name>
  • Switch to branch:
      git checkout <branch-name>
  • Create & switch in one step:
      git checkout -b <new-branch>
  • Merge branch into current:
      git merge <branch-name>

## Remote Repositories

  • List remotes:
      git remote -v
  • Add new remote:
      git remote add <name> <url>

## Viewing History

  • Show commit history:
      git log
  • Condensed history:
      git log --oneline --graph --decorate
  • Show changes:
      git diff

## Stashing Changes

  • Save uncommitted changes:
      git stash
  • List stashes:
      git stash list
  • Apply & remove latest stash:
      git stash pop

## Undoing Changes

  • Unstage a file:
      git restore --staged <file>
  • Discard working-dir changes:
      git restore <file>
  • Reset last commit (keep changes):
      git reset --soft HEAD~1
  • Reset last commit (discard changes):
      git reset --hard HEAD~1
  • Revert a commit by creating a new one:
      git revert <commit-hash>

## Tagging

  • Create annotated tag:
      git tag -a <tag-name> -m "Tag message"
  • Push tags:
      git push --tags

## Help

  • Get help on any command:
      git help <command>  or  git <command> --help

---
*Keep this cheat-sheet handy for a quick refresher!* 
