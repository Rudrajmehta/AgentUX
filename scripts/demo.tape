# AgentUX demo recording
# Run with: vhs scripts/demo.tape
# Output: scripts/agentux-demo.mp4

Output scripts/agentux-demo.mp4
Output scripts/agentux-demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1280
Set Height 780
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 40ms
Set PlaybackSpeed 1.0

# Custom prompt — hide the real username, show "agentux-demo"
Hide
Type "export PS1='\[\033[1;36m\]agentux-demo\[\033[0m\] $ '"
Enter
Type "clear"
Enter
Show

# ── Scene 1: help (6s) ──────────────────────────────────
Type "agentux --help"
Sleep 500ms
Enter
Sleep 4s

Hide
Type "clear"
Enter
Show
Sleep 300ms

# ── Scene 2: run against a real website (demo mode, fast) (12s) ──
Type "agentux run https://vercel.com --task 'find pricing and free tier limits' --demo"
Sleep 500ms
Enter
Sleep 10s

Hide
Type "clear"
Enter
Show
Sleep 300ms

# ── Scene 3: CLI surface on git (12s) ──────────────────
Type "agentux cli git --task 'find how to create a new branch' --demo"
Sleep 500ms
Enter
Sleep 10s

Hide
Type "clear"
Enter
Show
Sleep 300ms

# ── Scene 4: list all runs (5s) ──────────────────────────
Type "agentux runs"
Sleep 500ms
Enter
Sleep 4s

Hide
Type "clear"
Enter
Show
Sleep 300ms

# ── Scene 5: inspect a run — show scorecard (10s) ─────
Type "agentux inspect 42528ff67087"
Sleep 500ms
Enter
Sleep 8s

Hide
Type "clear"
Enter
Show
Sleep 300ms

# ── Scene 6: replay the run (14s) ───────────────────────
Type "agentux replay 42528ff67087 --speed 4"
Sleep 500ms
Enter
Sleep 12s

Hide
Type "clear"
Enter
Show
Sleep 300ms

# ── Scene 7: trends view (6s) ────────────────────────────
Type "agentux trends"
Sleep 500ms
Enter
Sleep 5s

Hide
Type "clear"
Enter
Show
Sleep 300ms

# ── Scene 8: TUI (12s) ──────────────────────────────────
Type "agentux tui"
Sleep 500ms
Enter
Sleep 4s
# Switch to trends tab
Type "2"
Sleep 2s
# Switch to alerts tab
Type "3"
Sleep 2s
# Back to home
Type "1"
Sleep 2s
# Quit TUI
Type "q"
Sleep 500ms

Sleep 1s
