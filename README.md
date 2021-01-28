https://tbat.ch

A personal home page and small blog built with Jekyll.

## Quickstart for Arch Linux
```bash
git clone https://github.com/tristanbatchler/tbat.ch
sudo pacman -S make gcc ruby rubygems
echo "# Add ruby gem apps to path \nexport PATH=\"\$PATH:\$HOME/.gem/ruby/2.7.0/bin"\" >> ~/.profile
source ~/.profile
gem install jekyll bundler
cd tbat.ch
bundle install
bundle exec jekyll serve &
xdg-open http://localhost:4000 &
```

[![Netlify Status](https://api.netlify.com/api/v1/badges/0b21337d-5f89-4321-bd90-27c7ef709574/deploy-status)](https://app.netlify.com/sites/tbatch/deploys)
