// Pinokio owns the terminal and its Stop control. Talos owns all tool permissions.
module.exports = (action, interactive = false) => ({
  run: [{method: 'shell.run', params: {
    venv: '.bootstrap', venv_python: '3.11', path: '.',
      message: `python launcher.py ${action}`, interactive, input: interactive,
      ...(interactive ? {onprompt: shell => shell.kill()} : {})
  }}]
});
