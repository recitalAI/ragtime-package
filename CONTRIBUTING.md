Thanks for being here! Glad you wish to contribute!

This repo contains the main Ragtime🎹 package. You can contribute by proposing new features, ideas, optimizations and documentation :)

# Backlog
Here are the projects we currently have in mind:
- `Async [AS]`: moving the answer generation step to `async` so as to speed it up. At the moment, the main loop in `TextGenerator.generate` runs questions iteratively and, for each question, each LLM. Running in async would allow to run all this more quickly. We have to make sure not too many parallel calls to LLMs are made so as not to have calls blocked. Hence a limit per LLM has to be included.
- `User interface [UI]`: add a user interface on top of the JSON files...big stuff!

# Testing the PR
Before releasing you can test your PR with `full_test.py` in `tests`.

You can then test the package with Linux and Windows if you're running with Windows computer with the `run_tests.py` script.
Just set the variable `script_dir` to the local `tests` folder on your computer and tun the script. Is will run `full_test.py` in your Windows environment and then run it on your Linux environment (assuming you already have installed WSL2 on your Windows).