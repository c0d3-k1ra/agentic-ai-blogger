#!/bin/bash

# Check if any tracked files have unstaged changes (auto-fixed by hooks)
if ! git diff --quiet; then
    echo ""
    echo "✨ Files were automatically fixed by pre-commit hooks!"
    echo ""
    echo "📝 Next steps:"
    echo "   git add -u          # Stage the auto-fixed changes"
    echo "   git commit          # Commit again"
    echo ""
fi
