Thanks for being here! Glad you wish to contribute!

This repo contains the main Ragtime🎹 package. You can contribute by proposing new features, ideas, optimizations and documentation :)

Here are the projects we currently have in mind:
- `Async [AS]`: moving the answer generation step to `async` so as to speed it up. At the moment, the main loop in `TextGenerator.generate` runs questions iteratively and, for each question, each LLM. Running in async would allow to run all this more quickly. We have to make sure not too many parallel calls to LLMs are made so as not to have calls blocked. Hence a limit per LLM has to be included.
- `User interface [UI]`: add a user interface on top of the JSON files...big stuff!