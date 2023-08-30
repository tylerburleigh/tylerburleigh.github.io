source ~/.zshrc
git push https://tylerburleigh:$GITHUB_KEY@github.com/tylerburleigh/tylerburleigh.github.io `git subtree split --prefix _site main`:gh-pages --force
