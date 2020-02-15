# Manage contexts

Project to manage repositories, libraries, and packages, with a single command, it could be able to manage different contexts for developer environments.

Imagine the situation, when you clone o create a repository, you need to install different packages, set up the profiles
for interactive console or some other stuff.

1. environments, conda environments in format yml
2. profiles, profiles and config file to ipython and ipdb
3. repositories, repositories with each folder with own context
4. containers, there container a lot of boxes

A container has a single environment, profile and repository folder, all those it call context.

## Environments, profiles and repositories

1. Set up context manager
   1. Install dependencies (Anaconda, Git, Docker), (pre-requisities, setup script)
   2. Config path to .ipython folder (profiles) ipython --profile=name --ipython-dir=path
   3. Config path to conda folder (environments)
   4. Config path to repository (repositories)

2. Create a new context
   1. Create a folder in repositories/repository
   2. Create a ipython profile
   3. Create a box.json file with a template
   4. Create a new file environment in conda and export it
   5. Create a repositoy with template

3. Clone a new context
   1. Clone repository
   2. Import dependencies from requirements to conda
   3. Generate point 1 if not exists

4. Delete a context
   1. Delete context from ipython profiles
   2. Delete context from conda environment
   3. Delete context from github
   4. Delete all config files

### Task 1 . Wrapper to the follow commands

1. Wrapper to manage commands from **conda** and **virtualwrapper**
   1. `conda env export > <envname>.yml`
   2. `conda env create -f <envname>.yml`
   3. `conda activate <envname>`
   4. `conda create --name <envname>`
   5. `conda info --envs`
   6. `conda remove --name <envname> --all`
   7. `conda create --name <envname_clone> --clone <envname>`

2. Wrapper to manage commands from **git**
   1. `git clone <repository>`
   2. `git checkout -b <branch>`
   3. `git fetch`
   4. `git init`

3. Wrapper to manage commands from **bash** terminal
   1. `mkdir repositories/<repository>`
   2. `touch boxes/<box>.json`

4. Wrapper to manage commands from **ipython**
   1. `ipython profile create <profile>`
   2. `ipython locate profile <profile>`
   3. `ipython --profile=foo`
   4. `ipython locate`
   5. `ipython --profile=<profile> --ipython-dir=<dir>`
