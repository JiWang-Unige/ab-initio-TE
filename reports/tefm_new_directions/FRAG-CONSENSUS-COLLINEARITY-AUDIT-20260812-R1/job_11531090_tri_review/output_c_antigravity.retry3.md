[reviewer-c backend: antigravity (agy --print)]
It looks like you're asking about the `--print-timeout` flag!

In the **Antigravity CLI (`agy`)**, `--print-timeout` is a command-line argument that sets the duration the system will wait during "print" mode (when you run a prompt non-interactively from the terminal and the system waits for the agent's output). By default, this is typically set to 5 minutes.

You can use it when running a prompt directly from your terminal, like this:
```bash
agy "Summarize this file" --print-timeout 10m
```

Are you looking to adjust this timeout for a specific script you're running, or did you run into a timeout error while using the CLI? Let me know how I can help!
